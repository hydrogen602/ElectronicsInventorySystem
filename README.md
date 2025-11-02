# Electronic Inventory System

Software to track your electronic inventory.

Features:

- API endpoints to add DigiKey products by barcode
- API queries DigiKey API to get product details
- UI to list and search inventory
  - Quick-access link to documentation
  - Track part availability
  - Warnings for low stock, moisture sensitivity, end of life product status, etc.
  - Fetch product image from DigiKey
- Assign hex IDs to represent the physical location of the part in the inventory

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
  - [ ] given a BOM, list in which slot each part is found
  - [ ] Store non-digikey parts
  - [ ] UI for OAuth login
