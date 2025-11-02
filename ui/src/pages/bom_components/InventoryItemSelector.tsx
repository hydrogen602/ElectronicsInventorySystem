import { Button, Card, Input, Modal, ModalClose, ModalDialog, Stack, Table, Typography } from "@mui/joy";
import { useCallback, useContext, useEffect, useState } from "react";
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
  const [matchedItems, setMatchedItems] = useState<ExistingInventoryItem[] | null>(null);
  const [browsedItems, setBrowsedItems] = useState<ExistingInventoryItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showBrowseResults, setShowBrowseResults] = useState(false);
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());
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

  useEffect(() => {
    if (open && bomEntry) {
      handleMatchEntry();
    }
  }, [open, bomEntry, handleMatchEntry]);

  const displayedItems = showBrowseResults ? browsedItems : matchedItems;

  return (
    <Modal open={open} onClose={onClose}>
      <ModalDialog sx={{ maxWidth: '800px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
        <ModalClose />
        <Typography level="h3">Match Inventory Items</Typography>

        <Card variant="outlined" sx={{ mt: 2, mb: 1 }}>
          <Stack gap={0.5}>
            <Typography level="body-md">
              <strong>Device:</strong> {bomEntry.device}
            </Typography>
            {bomEntry.value && (
              <Typography level="body-md">
                <strong>Value:</strong> {bomEntry.value}
              </Typography>
            )}
            {bomEntry.description && (
              <Typography level="body-md">
                <strong>Description:</strong> {bomEntry.description}
              </Typography>
            )}
          </Stack>
        </Card>

        <Stack gap="1rem" sx={{ mt: 2 }}>
          <Input
            placeholder="Search all inventory..."
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
          />

          {displayedItems && displayedItems.length > 0 && (
            <Card variant="outlined">
              <Typography level="title-sm" sx={{ mb: 1 }}>
                {showBrowseResults ? 'Browse Results' : 'Matched Items'} ({displayedItems.length})
              </Typography>
              <Table>
                <thead>
                  <tr>
                    <th style={{ width: '80px' }}>Image</th>
                    <th>Description</th>
                    <th>Manufacturer</th>
                    <th>Part Number</th>
                    <th>Quantity</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedItems.map((item) => {
                    const isMatched = bomEntry.inventoryItemMappingIds.has(item.id);
                    const imageUrl = item.productDetails?.imageUrl;
                    const imageFailed = imageErrors.has(item.id);
                    const showPlaceholder = !imageUrl || imageFailed;
                    return (
                      <tr key={item.id}>
                        <td>
                          {showPlaceholder ? (
                            <div
                              style={{
                                width: '64px',
                                height: '64px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backgroundColor: '#f0f0f0',
                                borderRadius: '4px',
                                color: '#999',
                                fontSize: '12px',
                              }}
                            >
                              No image
                            </div>
                          ) : (
                            <img
                              src={imageUrl}
                              alt={item.itemDescription}
                              style={{
                                width: '64px',
                                height: '64px',
                                objectFit: 'contain',
                                borderRadius: '4px',
                                backgroundColor: '#f0f0f0',
                              }}
                              onError={() => {
                                setImageErrors((prev) => new Set(prev).add(item.id));
                              }}
                            />
                          )}
                        </td>
                        <td>{item.itemDescription}</td>
                        <td>{item.manufacturerName}</td>
                        <td>{item.digikeyPartNumber || item.manufacturerPartNumber}</td>
                        <td>{item.availableQuantity}</td>
                        <td>
                          {isMatched ? (
                            <Typography level="body-sm" color="success">
                              Matched
                            </Typography>
                          ) : (
                            <Button
                              size="sm"
                              variant="soft"
                              color="primary"
                              startDecorator={<AddIcon />}
                              onClick={() => handleSelect(item.id)}
                            >
                              Select
                            </Button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </Card>
          )}

          {!isSearching && (displayedItems === null || displayedItems.length === 0) && (
            <Typography level="body-md" color="neutral">
              {showBrowseResults
                ? 'No items found. Try a different search term.'
                : (
                  displayedItems === null ? 'No similar items found. Search above to browse all inventory.' : 'Search above to browse all inventory.'
                )}
            </Typography>
          )}
        </Stack>
      </ModalDialog>
    </Modal>
  );
}

