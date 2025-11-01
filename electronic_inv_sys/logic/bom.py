from __future__ import annotations

from abc import ABC, abstractmethod
import io
from logging import info
import re
from typing import Annotated
import zipfile

from bson import ObjectId
from pydantic import BaseModel

from electronic_inv_sys.contracts.models import ObjectIdPydanticAnnotation

# from electronic_inv_sys.contracts.repos import InventoryRepository


class BomSource(ABC):
    @abstractmethod
    def gerber_bom_analysis(self, gerber_data_zip: bytes) -> Bom: ...


class Fusion360BomSource(BomSource):

    def gerber_bom_analysis(self, gerber_data_zip: bytes) -> Bom:
        try:
            with zipfile.ZipFile(io.BytesIO(gerber_data_zip)) as zip_file:
                assembly_files = [
                    f
                    for f in zip_file.namelist()
                    if "CAMOutputs/Assembly/" in f and not f.endswith("/")
                ]

                found_contents: list[str] = []
                for filename in assembly_files:
                    content = zip_file.read(filename).decode("utf-8", errors="ignore")
                    if content.startswith("Partlist exported from Fusion Hub"):
                        found_contents.append(content)

                match found_contents:
                    case []:
                        raise ValueError(
                            "Partlist file not found in ZIP archive.",
                        )
                    case [c]:
                        content = c
                    case _:
                        raise ValueError(
                            "Multiple partlist files found in ZIP archive.",
                        )

                bom = self._parse_fusion360_bom(content)
                info(f"Parsed BOM with {len(bom.rows)} entries.")

                return bom
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file.")

    def _parse_fusion360_bom(self, bom_text: str) -> Bom:
        lines = bom_text.strip().split("\n")
        if len(lines) < 3:
            raise ValueError("BOM text is too short to parse.")

        info_line = lines[0]
        header_line = lines[2]
        data_lines = lines[3:]

        header_re = re.compile(r"(\w+)\s+")

        headers = [
            ParseInfo(column_name=m.group(1), start_index=m.start(), end_index=m.end())
            for m in header_re.finditer(header_line)
        ]

        def find_header(name: str) -> ParseInfo:
            for header in headers:
                if header.column_name == name:
                    return header
            raise ValueError(f"Header '{name}' not found in BOM.")

        qty_header = find_header("Qty")
        value_header = find_header("Value")
        device_header = find_header("Device")
        package_header = find_header("Package")
        parts_header = find_header("Parts")
        description_header = find_header("Description")
        category_header = find_header("CATEGORY")
        manufacturer_header = find_header("MANUFACTURER")
        manufacturer_part_number_header = find_header("MANUFACTURER_PART_NUMBER")
        mpn_header = find_header("MPN")

        rows: list[BomEntry] = []
        for data_line in data_lines:
            qty_str = qty_header.extract_from_line(data_line)
            if not qty_str:
                raise ValueError(f"Missing Qty in BOM line: {data_line}")
            try:
                qty = int(qty_str)
            except ValueError:
                raise ValueError(f"Invalid Qty '{qty_str}' in BOM line: {data_line}")

            value = value_header.extract_from_line(data_line)
            device = device_header.extract_from_line(data_line)
            if not device:
                raise ValueError(f"Missing Device in BOM line: {data_line}")
            package = package_header.extract_from_line(data_line)
            if not package:
                raise ValueError(f"Missing Package in BOM line: {data_line}")
            parts_str = parts_header.extract_from_line(data_line)
            if not parts_str:
                raise ValueError(f"Missing Parts in BOM line: {data_line}")
            parts = [p.strip() for p in parts_str.split(",") if p.strip()]
            description = description_header.extract_from_line(data_line)
            category = category_header.extract_from_line(data_line)
            manufacturer = manufacturer_header.extract_from_line(data_line)
            manufacturer_part_number = (
                manufacturer_part_number_header.extract_from_line(data_line)
            )
            mpn = mpn_header.extract_from_line(data_line)

            row = BomEntry(
                qty=qty,
                value=value,
                device=device,
                parts=parts,
                description=description,
                manufacturer=manufacturer,
                comments="",
                inventory_item_mapping_ids=[],
                fusion360_ext=FusionBomEntry(
                    package=package,
                    category=category,
                    manufacturer_part_number=manufacturer_part_number,
                    mpn=mpn,
                ),
            )
            rows.append(row)

        return Bom(
            info_line=info_line,
            rows=rows,
            project=ProjectInfo.empty(),
        )


class ParseInfo(BaseModel):
    """
    The table is neatly formatted, so every column starts and ends at the same place in every line.
    """

    column_name: str
    start_index: int
    end_index: int

    def extract_from_line(self, line: str) -> str | None:
        text = line[self.start_index : self.end_index].strip()
        return text or None


class ProjectInfo(BaseModel):
    name: str | None
    """The name of the project."""
    author_names: str | None
    """The names of the authors of the project."""
    comments: str
    """Comments about the project."""

    @classmethod
    def empty(cls) -> ProjectInfo:
        return cls(name=None, author_names=None, comments="")


class Bom(BaseModel):
    info_line: str
    """Info parsed from the BOM file."""
    project: ProjectInfo
    rows: list[BomEntry]
    """The list of BOM entries."""


class BomEntry(BaseModel):
    """
    Represents a single entry in a BOM.
    """

    qty: int
    """The quantity of the part in the BOM."""
    value: str | None
    """e.g. 10R or 0.1uF"""
    device: str
    """e.g. the part number or name of the part. Required for identifying the part"""
    parts: list[str]
    """e.g. by which names it is referred to in the gerber file, e.g. ["R1", "R2"]."""
    description: str | None
    """The description of the part."""
    manufacturer: str | None
    """The manufacturer of the part."""

    comments: str

    inventory_item_mapping_ids: list[Annotated[ObjectId, ObjectIdPydanticAnnotation]]
    """
    List of which inventory items can be used where this part is used.
    """

    fusion360_ext: FusionBomEntry | None
    """
    Fusion360-specific extension data.
    """


class FusionBomEntry(BaseModel):
    package: str
    category: str | None
    manufacturer_part_number: str | None
    mpn: str | None
