# BOM parsing

- BOM management
  - [x] Store BOM in database
  - [x] UI + API to CRUD BOMs
    - [x] Parse BOM file from Fusion360
    - [x] Manually creation of BOMs
- BOM-Inventory matching
  - [x] search inventory for matching parts
  - [x] assign inventory items to BOM entries
- Part sourcing
  - [x] Given the BOM & inventory, check if a given number of PCBs can be assembled
  - [ ] Determine which parts are missing from the inventory for a given number of PCBs
  - [ ] Auto-generate DigiKey-compatible shopping list
  - [ ] Ability to assign placeholders when an inventory item is not available - like a digikey product number or adafruit product number.
  - [ ] Warning if a BOM entry only maps to one inv item which is low in stock or an obsolete part.
- Assembly planning
  - [x] UI display of which PCB parts map to which inventory items & slot ids. (e.g. R1 is product resister 10k and is in slot 01)
    - [x] Make the UI display print-friendly.
