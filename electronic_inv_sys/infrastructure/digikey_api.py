from json import JSONDecodeError
import time
from typing import TYPE_CHECKING, Any, Type, cast
from urllib.parse import quote
from httpx import AsyncClient, HTTPStatusError, Response
from loguru import logger
from pydantic import BaseModel, NonNegativeInt, ValidationError


from electronic_inv_sys.contracts.digikey_api import DigiKeyAPI, DigiKeyAPIException
from electronic_inv_sys.contracts.digikey_models import OAuthTokenRefresh
from electronic_inv_sys.contracts.digikey_models.barcoding import (
    PackListBarcodeResponse,
    Product2DBarcodeResponse,
    ProductBarcodeResponse,
)
from electronic_inv_sys.contracts.digikey_models.packlist import (
    InvoicePackingList,
    SalesOrderPackList,
)
from electronic_inv_sys.contracts.digikey_models.product_search import ProductDetails
from electronic_inv_sys.contracts.repos import ConfigRepository, MetadataRepository
from electronic_inv_sys.util import Environment


class DigiKeyOAuth(BaseModel):
    access_token: str
    token_type: str
    expires_at: NonNegativeInt
    refresh_token: str
    refresh_token_expires_at: NonNegativeInt


class AuthException(DigiKeyAPIException):
    """
    OAuth went wrong
    """

    pass


class DigiKeyAPIImpl(DigiKeyAPI):
    DIGIKEY_OAUTH_KEY = "DIGIKEY_OAUTH"

    __unfixable_msg = "Manual OAuth reset is required."

    def __init__(
        self,
        session: AsyncClient,
        metadata: MetadataRepository,
        config: ConfigRepository,
    ) -> None:
        super().__init__()
        self.__session = session
        self.__metadata = metadata
        self.__digikey_key = config["DIGIKEY_KEY"]
        self.__digikey_id = config["DIGIKEY_ID"]

        self.__sandbox = config.environment == Environment.TEST

    @property
    def __url_base(self) -> str:
        if self.__sandbox:
            return "https://sandbox-api.digikey.com"
        return "https://api.digikey.com"

    async def get_item_by_1d_barcode(self, barcode1d: str) -> ProductBarcodeResponse:
        barcode1d = barcode1d.strip()
        if not barcode1d.isdigit():
            raise ValueError(f"Barcode must be all digits, but got {barcode1d}")

        path = f"Barcoding/v3/ProductBarcodes/{quote(barcode1d)}"
        return await self.__generic_getter(path, ProductBarcodeResponse)

    async def get_item_by_2d_barcode(self, barcode2d: str) -> Product2DBarcodeResponse:
        barcode2d = barcode2d.replace("\u001e", "\u241e").replace("\u001d", "\u241d")
        path = f"Barcoding/v3/Product2DBarcodes/{quote(barcode2d)}"
        return await self.__generic_getter(path, Product2DBarcodeResponse)

    async def get_pack_list_by_1d_barcode(
        self, barcode1d: str
    ) -> PackListBarcodeResponse:
        barcode1d = barcode1d.strip()
        if not barcode1d.isdigit():
            raise ValueError(f"Barcode must be all digits, but got {barcode1d}")
        path = f"Barcoding/v3/PackListBarcodes/{quote(barcode1d)}"
        return await self.__generic_getter(path, PackListBarcodeResponse)

    async def get_pack_list_by_2d_barcode(
        self, barcode2d: str
    ) -> PackListBarcodeResponse:
        barcode2d = barcode2d.replace("\u001e", "\u241e").replace("\u001d", "\u241d")
        path = f"Barcoding/v3/PackList2DBarcodes/{quote(barcode2d)}"
        return await self.__generic_getter(path, PackListBarcodeResponse)

    async def get_product_details(self, digikey_part_id: str) -> ProductDetails:
        path = f"products/v4/search/{quote(digikey_part_id)}/productdetails"
        return await self.__generic_getter(path, ProductDetails)

    async def get_pack_list_by_sales_order_id(
        self, sales_order_id: NonNegativeInt
    ) -> SalesOrderPackList:
        # the packinglist api seems broken, it returns "errorcode":"messaging.adaptors.http.flow.ApplicationNotFound"
        raise Exception("This is not working on the DigiKey side for some reason")
        # path = f"packinglist/v1/salesorderid/{sales_order_id}?includePdf=false"
        # return self.__generic_getter(path, SalesOrderPackList)

    async def get_pack_list_by_invoice_id(
        self, invoice_id: NonNegativeInt
    ) -> InvoicePackingList:
        # the packinglist api seems broken, it returns "errorcode":"messaging.adaptors.http.flow.ApplicationNotFound"
        raise Exception("This is not working on the DigiKey side for some reason")
        # path = f"packinglist/v1/invoice/{invoice_id}?includePdf=false"
        # return self.__generic_getter(path, InvoicePackingList)

    async def __generic_getter[T](self, path: str, type_: Type[T]) -> T:
        """
        Args:
            path (str): The path to the API endpoint, without the base URL / hostname / port stuff.
            type_ (Type[T]): The type to parse the response into.
        """
        headers = await self.__get_headers()
        path = path.lstrip("/")
        resp: Response | None = None
        try:
            # this should be async, but aiohttp is not working with digikey
            resp = await self.__session.get(
                f"{self.__url_base}/{path}",
                headers=headers,
            )
            resp.raise_for_status()
            return type_(**resp.json())
        except HTTPStatusError as e:
            text = resp.text if resp is not None else "No response text"
            logger.error(
                "HTTP error ({status}) from digikey: {error}: {method} '{url}', response: {text}",
                status=e.response.status_code,
                error=e,
                method=e.request.method,
                url=e.request.url,
                text=text,
            )
            if e.response.status_code == 404:
                raise KeyError("Item not found")
            raise DigiKeyAPIException(
                f"DigiKey API returned an error: status {e.response.status_code}"
            ) from e
        except JSONDecodeError as e:
            text = resp.text if resp is not None else "No response text"
            logger.error(
                "Failed to parse response as json from DigiKey API: {error}: {text}",
                error=e,
                text=text,
            )
            raise DigiKeyAPIException(
                "Failed to parse response as json from DigiKey API."
            ) from e
        except ValidationError as e:
            text = resp.text if resp is not None else "No response text"

            logger.error(
                "Failed to parse response from DigiKey API: {error}. Tried to parse into {type_name}, data: {text}",
                error=e,
                type_name=type_.__name__,
                text=text,
            )
            raise DigiKeyAPIException(
                "Failed to parse response from DigiKey API."
            ) from e

    async def __get_headers(self) -> dict[str, str]:
        access_token, token_type = await self.__oauth_access_token()

        return {
            "X-DIGIKEY-Client-Id": self.__digikey_id,
            "X-DIGIKEY-Locale-Site": "US",
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Currency": "USD",
            "Authorization": f"{token_type} {access_token}",
        }

    async def __oauth_access_token(self) -> tuple[str, str]:
        """
        Retrieves the OAuth access token for authentication.
        May refresh the token if it is expired or about to expire.

        Returns:
            (str, str): The OAuth access token, and the token type.
        Raises:
            AuthException: If the `digikey_oauth_key` is not found in the config repo or if the value for the key is invalid or if the refresh fails.
        """
        current_auth_raw = self.__metadata.get(self.DIGIKEY_OAUTH_KEY)
        if current_auth_raw is None:
            logger.error(f"No OAuth token found in metadata. {self.__unfixable_msg}")
            raise AuthException(
                f"No OAuth token found in metadata. {self.__unfixable_msg}"
            )
        if not isinstance(current_auth_raw, dict):
            logger.error(f"Invalid OAuth data in metadata. {self.__unfixable_msg}")
            raise AuthException(
                f"Invalid OAuth data in metadata. {self.__unfixable_msg}"
            )

        try:
            current_auth = DigiKeyOAuth(**cast(Any, current_auth_raw))
        except ValidationError as e:
            logger.error(f"Invalid OAuth data in metadata: {e}. {self.__unfixable_msg}")
            raise AuthException(
                f"Invalid OAuth data in metadata. {self.__unfixable_msg}"
            ) from e

        soon = time.time() + 60

        if current_auth.expires_at < soon:
            current_auth = await self.__oauth_refresh(current_auth, soon)

        return current_auth.access_token, current_auth.token_type

    async def __oauth_refresh(
        self, current_auth: DigiKeyOAuth, soon: float
    ) -> DigiKeyOAuth:
        logger.info("Refreshing OAuth token")

        if current_auth.refresh_token_expires_at < soon:
            logger.error(f"Refresh token has expired. {self.__unfixable_msg}")
            raise AuthException(f"Refresh token has expired. {self.__unfixable_msg}")

        body = {
            "client_id": self.__digikey_id,
            "client_secret": self.__digikey_key,
            "refresh_token": current_auth.refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            # this should be async, but aiohttp somehow causes DigiKey to reset the connection
            resp = await self.__session.post(
                f"{self.__url_base}/v1/oauth2/token", data=body
            )
            try:
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to refresh token: {e} - {resp.text}")
                raise e
            new_auth_response = OAuthTokenRefresh(**resp.json())

            now = int(time.time())
            new_auth = DigiKeyOAuth(
                access_token=new_auth_response.access_token,
                token_type=new_auth_response.token_type,
                expires_at=now + new_auth_response.expires_in,
                refresh_token=new_auth_response.refresh_token,
                refresh_token_expires_at=now
                + new_auth_response.refresh_token_expires_in,
            )

            assert (
                new_auth.expires_at > now
            ), f"Got new token that expires in the past or soon: Expires at {time.ctime(new_auth.expires_at)}"
            assert (
                new_auth.refresh_token_expires_at > now
            ), f"Got new refresh token that expires in the past or soon: Expires at {time.ctime(new_auth.refresh_token_expires_at)}"

            # update both tokens - the refresh token we just used is now invalid so we need the store the new one too
            self.__metadata[self.DIGIKEY_OAUTH_KEY] = new_auth.model_dump()
            return new_auth

        except ValidationError as e:
            raise AuthException(
                "Failed to parse response from DigiKey API. This is a bug"
            ) from e
        except HTTPStatusError as e:
            status = e.response.status_code
            logger.error(f"Failed to refresh token: {e}, status {status}")

            if status == 401:
                raise AuthException(
                    f"Failed to authenticate with DigiKey API. Check your credentials or other potential fix: {self.__unfixable_msg}"
                ) from e
            raise AuthException(f"Failed to refresh token: {e}") from e
        except Exception as e:
            logger.opt(exception=e).error("Unknown error refreshing token: {}", str(e))
            raise AuthException(
                f"Unexpected error: Failed to refresh token: {e}"
            ) from e


if TYPE_CHECKING:
    DigiKeyAPIImpl(cast(Any, None), cast(Any, None), cast(Any, None))
