from __future__ import annotations
import itertools

from loguru import logger

from electronic_inv_sys.contracts.models import BomEntry, ExistingInventoryItem
from electronic_inv_sys.contracts.repos import InventoryRepository


def match_bom_entry_to_inventory(
    bom_entry: BomEntry,
    inventory: InventoryRepository,
    max_results: int = 10,
) -> list[ExistingInventoryItem]:
    """
    Match a BOM entry to inventory items with intelligent ranking.

    Prioritizes exact matches on manufacturer part number, then uses text search
    for fuzzy matching on other fields.

    Args:
        bom_entry: The BOM entry to match
        inventory: The inventory repository to search
        max_results: Maximum number of results to return (default 10)

    Returns:
        List of inventory items ranked by relevance (exact matches first)
    """

    manufacturer_part_numbers: list[str] = []
    if bom_entry.fusion360_ext:
        if bom_entry.fusion360_ext.manufacturer_part_number:
            manufacturer_part_numbers.append(
                bom_entry.fusion360_ext.manufacturer_part_number
            )
        if bom_entry.fusion360_ext.mpn:
            manufacturer_part_numbers.append(bom_entry.fusion360_ext.mpn)

    exact_matches: list[ExistingInventoryItem] = []
    if manufacturer_part_numbers:
        exact_matches = inventory.get_items_by_manufacturer_part_numbers(
            manufacturer_part_numbers
        )
    else:
        exact_matches = []

    search_terms: list[str] = []
    if bom_entry.device:
        search_terms.append(bom_entry.device)
    if bom_entry.value:
        search_terms.append(bom_entry.value)
    if bom_entry.description:
        search_terms.append(bom_entry.description)
    if bom_entry.manufacturer:
        search_terms.append(bom_entry.manufacturer)
    if manufacturer_part_numbers:
        search_terms.extend(manufacturer_part_numbers)

    # Perform text search if we have search terms
    text_matches: list[ExistingInventoryItem] = []
    if search_terms:
        try:
            query = " ".join(search_terms)
            text_matches = inventory.text_search(query, max_results=max_results)
        except NotImplementedError:
            # Some repositories may not implement text search
            logger.warning("Text search not implemented for this repository")

    # deduplicate
    # CPython dicts keep insertion order
    # this is in inverse priority so exact matches override text matches
    # on key collision
    all_matches = {
        item.id: item
        for item in itertools.chain(reversed(text_matches), reversed(exact_matches))
    }

    # Return up to max_results & put the highest priority items first again
    return list(reversed(all_matches.values()))[:max_results]
