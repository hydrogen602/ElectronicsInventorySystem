import { Button, Card, Input, Modal, ModalClose, ModalDialog, Stack, Table, Typography } from "@mui/joy";
import { useCallback, useContext, useState } from "react";
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';

import { BomEntry, ExistingInventoryItem } from "../../openapi/inventory";
import CLIENT from "../../client";
import { ErrorReporting } from "../..";

interface InventoryItemSelectorProps {
  bomEntry: BomEntry;
  onSelect: (itemId: string) => void;
  onClose: () => void;
  open: boolean;
}

export default function InventoryItemSelector({
  bomEntry,
  onSelect,
  onClose,
  open
}: InventoryItemSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [matchedItems, setMatchedItems] = useState<ExistingInventoryItem[]>([]);
  const [browsedItems, setBrowsedItems] = useState<ExistingInventoryItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showBrowseResults, setShowBrowseResults] = useState(false);
  const setErr = useContext(ErrorReporting);

  const handleMatchEntry = useCallback(async () => {
    setIsSearching(true);
    try {
      const items = await CLIENT.matchBomEntryToInventoryApiBomMatchInventoryPost({
        bomEntry: bomEntry,
        maxResults: 10,
      });
      setMatchedItems(items);
      setShowBrowseResults(false);
    } catch (error) {
      setErr(error as Error);
    } finally {
      setIsSearching(false);
    }
  }, [bomEntry, setErr]);

  const handleBrowseSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setBrowsedItems([]);
      return;
    }

    setIsSearching(true);
    try {
      const items = await CLIENT.searchApiSearchGet({ query: searchQuery });
      setBrowsedItems(items);
      setShowBrowseResults(true);
    } catch (error) {
      setErr(error as Error);
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, setErr]);

  const handleSelect = (itemId: string) => {
    onSelect(itemId);
  };

  const displayedItems = showBrowseResults ? browsedItems : matchedItems;

  return (
    <Modal open={open} onClose={onClose}>
      <ModalDialog sx={{ maxWidth: '800px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
        <ModalClose />
        <Typography level="h3">Match Inventory Items</Typography>

        <Stack gap="1rem" sx={{ mt: 2 }}>
          <Stack direction="row" gap="1rem">
            <Button
              onClick={handleMatchEntry}
              loading={isSearching}
              startDecorator={<SearchIcon />}
            >
              Match by BOM Entry
            </Button>
            <Input
              placeholder="Or search all inventory..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleBrowseSearch();
                }
              }}
              endDecorator={
                <Button
                  size="sm"
                  variant="soft"
                  onClick={handleBrowseSearch}
                  loading={isSearching}
                >
                  <SearchIcon />
                </Button>
              }
              sx={{ flexGrow: 1 }}
            />
          </Stack>

          {displayedItems.length > 0 && (
            <Card variant="outlined">
              <Typography level="title-sm" sx={{ mb: 1 }}>
                {showBrowseResults ? 'Browse Results' : 'Matched Items'} ({displayedItems.length})
              </Typography>
              <Table>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Manufacturer</th>
                    <th>Part Number</th>
                    <th>Quantity</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedItems.map((item) => (
                    <tr key={item.id}>
                      <td>{item.itemDescription}</td>
                      <td>{item.manufacturerName}</td>
                      <td>{item.digikeyPartNumber || item.manufacturerPartNumber}</td>
                      <td>{item.availableQuantity}</td>
                      <td>
                        <Button
                          size="sm"
                          variant="soft"
                          color="primary"
                          startDecorator={<AddIcon />}
                          onClick={() => handleSelect(item.id)}
                        >
                          Select
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          )}

          {!isSearching && displayedItems.length === 0 && (
            <Typography level="body-md" color="neutral">
              {showBrowseResults
                ? 'No items found. Try a different search term.'
                : 'Click "Match by BOM Entry" to find matching inventory items, or search above to browse all inventory.'}
            </Typography>
          )}
        </Stack>
      </ModalDialog>
    </Modal>
  );
}

