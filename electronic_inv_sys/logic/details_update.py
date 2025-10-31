from electronic_inv_sys.contracts.digikey_models.product_search import (
    ProductT,
)
from electronic_inv_sys.contracts.models import DigiKeyProductDetails


def refine_product_details(product: ProductT) -> DigiKeyProductDetails:
    """
    Refine raw product details from the DigiKey API into what we care about.

    Warnings are computed here based on the product details.

    Args:
        digikey_part_number (str): The DigiKey part number to get details for.
        digikey_api (DigiKeyAPI): The DigiKey API to use.
    Returns:
        DigiKeyProductDetails: The product details.
    """

    descr = product.Description

    warnings: list[str] = []
    quantity_available = product.QuantityAvailable
    if quantity_available is not None:
        if quantity_available < 1000:
            warnings.append("Low stock")
        elif quantity_available == 0:
            warnings.append("Sold out")

    if (status := product.ProductStatus) is not None:
        if status.Status != "Active":
            warnings.append(f"Product status: {status.Status}")
    if product.NormallyStocking is False:
        warnings.append("Not normally stocked")
    if product.Discontinued is True:
        warnings.append("Discontinued")
    if product.EndOfLife is True:
        warnings.append("End of life")

    classifications = product.Classifications
    if classifications:
        match classifications.RohsStatus:
            case None:
                warnings.append("No RoHS status")
            case "RoHS Compliant":
                pass
            case "RoHS non-compliant":
                warnings.append("Not RoHS compliant")
            case "RoHS Compliant By Exemption":
                warnings.append("RoHS compliant by exemption")
            case "Not Applicable":
                pass
            case "ROHS3 Compliant":
                pass
            case other:
                warnings.append(f"RoHS status: {other}")

        moisture = classifications.MoistureSensitivityLevel
        if moisture is not None:
            if moisture.lower() == "not applicable":
                pass
            else:
                try:
                    level, note = moisture.split(sep=None, maxsplit=1)
                    level = int(level)
                    if level == 0 or level == 1:
                        pass
                    else:
                        note = note.strip("()")
                        warnings.append(f"Moisture sensitivity level: {level} - {note}")
                except ValueError:
                    warnings.append(f"Moisture sensitivity level: {moisture}")

    return DigiKeyProductDetails(
        product_url=product.ProductUrl,
        datasheet_url=product.DatasheetUrl,
        image_url=product.PhotoUrl,
        detailed_description=descr.DetailedDescription if descr is not None else None,
        product_warnings=warnings,
    )
