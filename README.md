# Electronic Inventory System

Software to track your electronic inventory.

Features:

- API endpoints to add DigiKey products by barcode
- API queries DigiKey API to get product details
- UI to list and search inventory
  - Quick-access link to documentation
  - Track part availability
  - Warnings for low stock at the supplier, moisture sensitivity, end of life product status, etc.
  - Fetch product image from DigiKey
- Assign hex IDs to represent the physical location of the part in the inventory
- Create bill of materials or import them from Fusion360-produced gerber zip file
  - Match BOM entries to inventory items
  - Shows how many PCBs can be assembled given the available stock in the inventory.
  - Printable list of BOM entries, including number available, physical location id, part number in the PCB design, etc.

![Screenshot of UI](https://github.com/hydrogen602/ElectronicsInventorySystem/blob/main/screenshots/image.png?raw=true)

# Running

```bash
make run-docker
```

# TODO:

- [ ] DB collection to log every import?
- [ ] portability
  - [x] isolate UI from other stuff
  - [x] bring UI and backend into one repo
  - [x] add docker-compose that runs it all together (UI, backend, db)
- [ ] features
  - [ ] mobile-friendly UI
  - [x] given a BOM, list in which slot each part is found
  - [ ] Store non-digikey parts
  - [ ] UI for OAuth login
