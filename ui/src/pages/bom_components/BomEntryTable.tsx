import { Table, Typography, Stack } from "@mui/joy";
import { BomEntry, ExistingInventoryItem } from "../../openapi/inventory";
import { useContext, useEffect, useState } from "react";
import CLIENT from "../../client";
import { ErrorReporting } from "../..";

interface BomEntryTableProps {
  entries: BomEntry[];
}

function formatSlotIds(slotIds: Set<number>): string {
  return Array.from(slotIds)
    .sort((a, b) => a - b)
    .map(id => id.toString(16).toUpperCase().padStart(2, '0'))
    .join(', ');
}

function calculateMaxPCBs(entry: BomEntry, matchedItems: ExistingInventoryItem[]): number | null {
  if (matchedItems.length === 0 || entry.qty <= 0) {
    return null;
  }

  const maxItemsAvailable = matchedItems.reduce((sum, item) => sum + item.availableQuantity, 0);
  return Math.floor(maxItemsAvailable / entry.qty);
}

export default function BomEntryTable({ entries }: BomEntryTableProps) {
  const [matchedItemsMap, setMatchedItemsMap] = useState<Map<string, ExistingInventoryItem>>(new Map());
  const [loadingItems, setLoadingItems] = useState<Set<string>>(new Set());
  const [imageErrors, setImageErrors] = useState<Set<string>>(new Set());
  const setErr = useContext(ErrorReporting);

  useEffect(() => {
    const allItemIds = new Set<string>();
    entries.forEach(entry => {
      entry.inventoryItemMappingIds?.forEach(id => {
        if (id && !matchedItemsMap.has(id) && !loadingItems.has(id)) {
          allItemIds.add(id);
        }
      });
    });

    if (allItemIds.size === 0) {
      return;
    }

    setLoadingItems(prev => {
      const next = new Set(prev);
      allItemIds.forEach(id => next.add(id));
      return next;
    });

    const fetchPromises = Array.from(allItemIds).map(async (itemId) => {
      try {
        const item = await CLIENT.getItemApiItemItemIdGet({ itemId });
        return { itemId, item };
      } catch (error) {
        setErr(error as Error);
        return null;
      }
    });

    Promise.all(fetchPromises).then(results => {
      setMatchedItemsMap(prev => {
        const newMap = new Map(prev);
        results.forEach(result => {
          if (result) {
            newMap.set(result.itemId, result.item);
          }
        });
        return newMap;
      });

      setLoadingItems(prev => {
        const next = new Set(prev);
        allItemIds.forEach(id => next.delete(id));
        return next;
      });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries]);

  if (entries.length === 0) {
    return <div>No entries</div>;
  }

  // Calculate max PCBs per entry and overall
  const entryMaxPCBs = entries.map(entry => {
    const matchedItems = Array.from(entry.inventoryItemMappingIds || [])
      .map(id => matchedItemsMap.get(id))
      .filter((item): item is ExistingInventoryItem => item !== undefined);
    return calculateMaxPCBs(entry, matchedItems);
  });

  const overallMaxPCBs = Math.min(...entryMaxPCBs.filter((pcb): pcb is number => pcb !== null));

  return (
    <Stack gap="1rem">
      {overallMaxPCBs !== null && (
        <Typography level="title-md" color="primary">
          Maximum PCBs that can be assembled: {overallMaxPCBs}
        </Typography>
      )}
      <Table>
        <thead>
          <tr>
            <th style={{ width: '4%' }}>Qty</th>
            <th>Device</th>
            <th>Value</th>
            <th>Description</th>
            <th>Parts</th>
            <th>Comments</th>
            <th style={{ width: '10%' }}>Max PCBs</th>
            <th style={{ width: '30%' }}>Matched Items</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry, idx) => {
            const matchedItems = Array.from(entry.inventoryItemMappingIds || [])
              .map(id => matchedItemsMap.get(id))
              .filter((item): item is ExistingInventoryItem => item !== undefined);

            const maxPCBs = calculateMaxPCBs(entry, matchedItems);

            return (
              <tr
                key={idx}
                style={{
                  opacity: entry.doNotPlace ? 0.5 : 1,
                  color: entry.doNotPlace ? '#999' : undefined,
                }}
              >
                <td style={{ wordWrap: 'break-word' }}>{entry.qty}</td>
                <td style={{ wordWrap: 'break-word' }}>{entry.device}</td>
                <td style={{ wordWrap: 'break-word' }}>{entry.value}</td>
                <td style={{ wordWrap: 'break-word' }}>{entry.description}</td>
                <td style={{ wordWrap: 'break-word' }}>{entry.parts?.join(', ')}</td>
                <td style={{ wordWrap: 'break-word' }}>{entry.comments}</td>
                <td style={{ wordWrap: 'break-word' }}>
                  {maxPCBs !== null ? (
                    <Typography level="body-sm" fontWeight={maxPCBs === overallMaxPCBs ? "lg" : "md"}>
                      {maxPCBs}
                    </Typography>
                  ) : (
                    <Typography level="body-sm" color="neutral">
                      -
                    </Typography>
                  )}
                </td>
                <td style={{ wordWrap: 'break-word' }}>
                  {matchedItems.length > 0 ? (
                    <Stack gap="0.5rem">
                      {matchedItems.map((item) => {
                        const imageUrl = item.productDetails?.imageUrl;
                        const imageFailed = imageErrors.has(item.id);
                        const showPlaceholder = !imageUrl || imageFailed;

                        return (
                          <Stack key={item.id} direction="row" gap="0.5rem" alignItems="flex-start">
                            {showPlaceholder ? (
                              <div style={{
                                width: '3em',
                                height: '3em',
                                backgroundColor: '#f0f0f0',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '4px',
                                flexShrink: 0,
                              }}>
                                <Typography level="body-xs" color="neutral">No image</Typography>
                              </div>
                            ) : (
                              <img
                                src={imageUrl}
                                alt={item.itemDescription || ''}
                                style={{
                                  width: '3em',
                                  height: '3em',
                                  objectFit: 'contain',
                                  borderRadius: '4px',
                                  flexShrink: 0,
                                }}
                                onError={() => {
                                  setImageErrors(prev => new Set(prev).add(item.id));
                                }}
                              />
                            )}
                            <Stack gap="0.25rem" flexGrow={1} sx={{ minWidth: 0 }}>
                              <Typography level="body-sm" sx={{ wordWrap: 'break-word' }}>
                                {item.itemDescription}
                              </Typography>
                              <Typography level="body-xs" color="neutral">
                                Available: {item.availableQuantity}
                              </Typography>
                              <Typography level="body-xs" component="code" sx={{ wordWrap: 'break-word' }}>
                                Slots: {formatSlotIds(item.slotIds)}
                              </Typography>
                            </Stack>
                          </Stack>
                        );
                      })}
                    </Stack>
                  ) : (
                    <Typography level="body-sm" color="neutral">
                      No matched items
                    </Typography>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </Stack>
  );
}

