import { Button, Card, Chip, ChipDelete, FormControl, FormLabel, Input, Stack, Textarea, Typography } from "@mui/joy";
import DeleteIcon from '@mui/icons-material/Delete';
import LinkIcon from '@mui/icons-material/Link';
import { useState, useEffect, useCallback, useContext } from "react";
import { BomEntry, ExistingInventoryItem } from "../../openapi/inventory";
import InventoryItemSelector from "./InventoryItemSelector";
import CLIENT from "../../client";
import { ErrorReporting } from "../..";

interface BomEntryEditorProps {
  entry: BomEntry;
  index: number;
  onUpdate: (entry: BomEntry) => void;
  onRemove: () => void;
}

export default function BomEntryEditor({ entry, index, onUpdate, onRemove }: BomEntryEditorProps) {
  const [partsInput, setPartsInput] = useState(entry.parts?.join(', ') || '');
  const [assignedItems, setAssignedItems] = useState<ExistingInventoryItem[]>([]);
  const [selectorOpen, setSelectorOpen] = useState(false);
  const setErr = useContext(ErrorReporting);

  useEffect(() => {
    setPartsInput(entry.parts?.join(', ') || '');
  }, [entry.parts]);

  // Fetch assigned inventory items
  useEffect(() => {
    const fetchAssignedItems = async () => {
      if (!entry.inventoryItemMappingIds || entry.inventoryItemMappingIds.size === 0) {
        setAssignedItems([]);
        return;
      }

      try {
        const itemPromises = Array.from(entry.inventoryItemMappingIds).map(id =>
          CLIENT.getItemApiItemItemIdGet({ itemId: id })
        );
        setAssignedItems(await Promise.all(itemPromises));
      } catch (error) {
        setErr(error);
      }
    };

    fetchAssignedItems();
  }, [entry.inventoryItemMappingIds, setErr]);

  const updateField = <K extends keyof BomEntry>(field: K, value: BomEntry[K]) => {
    onUpdate({ ...entry, [field]: value });
  };

  const handlePartsChange = (partsStr: string) => {
    setPartsInput(partsStr);
  };

  const handlePartsBlur = () => {
    const parts = partsInput.split(',').map(p => p.trim()).filter(p => p.length > 0);
    updateField('parts', parts);
  };

  const handleAddInventoryItem = useCallback((itemId: string) => {
    const newIds = new Set(entry.inventoryItemMappingIds);
    newIds.add(itemId);
    updateField('inventoryItemMappingIds', newIds);
    setSelectorOpen(false);
  }, [entry.inventoryItemMappingIds, updateField]);

  const handleRemoveInventoryItem = useCallback((itemId: string) => {
    const newIds = new Set(entry.inventoryItemMappingIds);
    newIds.delete(itemId);
    updateField('inventoryItemMappingIds', newIds);
  }, [entry.inventoryItemMappingIds, updateField]);

  return (
    <Card variant="outlined">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography level="title-sm">Entry #{index + 1}</Typography>
        <Button
          size="sm"
          variant="soft"
          color="danger"
          startDecorator={<DeleteIcon />}
          onClick={onRemove}
        >
          Remove
        </Button>
      </Stack>
      <Stack gap="0.75rem">
        <Stack direction="row" gap="0.75rem">
          <FormControl required sx={{ width: '100px' }}>
            <FormLabel>Qty</FormLabel>
            <Input
              type="number"
              placeholder="Quantity"
              value={entry.qty}
              onChange={(e) => updateField('qty', parseInt(e.target.value) || 0)}
            />
          </FormControl>
          <FormControl required sx={{ flexGrow: 1 }}>
            <FormLabel>Device</FormLabel>
            <Input
              placeholder="Device"
              value={entry.device}
              onChange={(e) => updateField('device', e.target.value)}
            />
          </FormControl>
          <FormControl sx={{ flexGrow: 1 }}>
            <FormLabel>Value</FormLabel>
            <Input
              placeholder="Value (optional)"
              value={entry.value || ''}
              onChange={(e) => updateField('value', e.target.value || null)}
            />
          </FormControl>
        </Stack>
        <Stack direction="row" gap="0.75rem">
          <FormControl sx={{ flexGrow: 1 }}>
            <FormLabel>Description</FormLabel>
            <Input
              placeholder="Description (optional)"
              value={entry.description || ''}
              onChange={(e) => updateField('description', e.target.value || null)}
            />
          </FormControl>
          <FormControl sx={{ flexGrow: 1 }}>
            <FormLabel>Manufacturer</FormLabel>
            <Input
              placeholder="Manufacturer (optional)"
              value={entry.manufacturer || ''}
              onChange={(e) => updateField('manufacturer', e.target.value || null)}
            />
          </FormControl>
        </Stack>
        <FormControl>
          <FormLabel>Parts</FormLabel>
          <Input
            placeholder="Parts (comma-separated)"
            value={partsInput}
            onChange={(e) => handlePartsChange(e.target.value)}
            onBlur={handlePartsBlur}
          />
        </FormControl>
        <FormControl>
          <FormLabel>Comments</FormLabel>
          <Textarea
            placeholder="Comments"
            value={entry.comments || ''}
            onChange={(e) => updateField('comments', e.target.value)}
            minRows={2}
          />
        </FormControl>

        <Stack gap="0.5rem">
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <FormLabel>Assigned Inventory Items</FormLabel>
            <Button
              size="sm"
              variant="soft"
              startDecorator={<LinkIcon />}
              onClick={() => setSelectorOpen(true)}
            >
              Match/Add Item
            </Button>
          </Stack>
          {assignedItems.length > 0 ? (
            <Stack direction="row" gap="0.5rem" flexWrap="wrap">
              {assignedItems.map((item) => (
                <Chip
                  key={item.id}
                  variant="soft"
                  color="primary"
                  endDecorator={
                    <ChipDelete
                      onDelete={() => handleRemoveInventoryItem(item.id)}
                    />
                  }
                >
                  {item.itemDescription} ({item.availableQuantity})
                </Chip>
              ))}
            </Stack>
          ) : (
            <Typography level="body-sm" color="neutral">
              No inventory items assigned. Click "Match/Add Item" to search and assign.
            </Typography>
          )}
        </Stack>
      </Stack>

      <InventoryItemSelector
        bomEntry={entry}
        open={selectorOpen}
        onClose={() => setSelectorOpen(false)}
        onSelect={handleAddInventoryItem}
      />
    </Card>
  );
}

