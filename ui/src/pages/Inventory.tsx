import { Button, Card, Input, Modal, ModalClose, ModalDialog, Stack, Table, Typography } from "@mui/joy";
import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import SearchIcon from '@mui/icons-material/Search';

import Header from "../Header";
import { ExistingInventoryItem } from "../openapi/inventory";
import CLIENT from "../client";
import OneRow from "./inventory_components/OneRow";
import { MapSelf, useEnvironment } from "./inventory_components/utils";
import { ErrorReporting } from "..";

function useAllItems(): [ExistingInventoryItem[], () => void, (id: string, f: MapSelf<ExistingInventoryItem>) => void] {
  const [data, setData] = useState([] as ExistingInventoryItem[]);

  const setErr = useContext(ErrorReporting);

  function smallestOfSet(s: Set<number>) {
    let min = Infinity;
    s.forEach(v => {
      if (v < min) {
        min = v;
      }
    })
    return min;
  }

  data.sort((a, b) => smallestOfSet(a.slotIds) - smallestOfSet(b.slotIds));

  const refresh = useCallback(() => {
    CLIENT.getAllItemsApiItemsGet().then(setData).catch(setErr);
  }, [setErr]);
  useEffect(() => {
    CLIENT.getAllItemsApiItemsGet().then(setData).catch(setErr);
  }, [setErr]);

  const updateItem = useCallback((id: string, f: MapSelf<ExistingInventoryItem>) => {
    setData(data => {
      const idx = data.findIndex(item => item.id === id);
      if (idx === -1) {
        setErr(new Error(`Item with id ${id} not found`));
        throw new Error(`Item with id ${id} not found`);
      }
      const updated = f(data[idx]);
      const newData = data.filter(item => item.id !== id);
      newData.push(updated);
      return newData;
    });
  }, [setData, setErr]);

  return [data, refresh, updateItem];
}

function Inventory() {
  const [items, refreshItems, updateItem] = useAllItems();

  const [searchTerm, setSearchTerm] = useState('');

  const filteredItems = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (term === '') {
      return items;
    }
    return items.filter(item => {
      return (item.itemDescription || '').toLowerCase().includes(term) ||
        (item.comments || '').toLowerCase().includes(term) ||
        (item.manufacturerName || '').toLowerCase().includes(term) ||
        (item.digikeyPartNumber || '').toLowerCase().includes(term) ||
        (item.digikeyPartNumber || '').toLowerCase().includes(term);
    });
  }, [items, searchTerm]);

  const env = useEnvironment();

  return (
    <div>
      <Header />

      <div style={{
        margin: "3rem",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "2rem",
      }}>
        {env !== 'prod' && <Typography level='h2' color='warning'>Environment: {env}</Typography>}
        <Card>
          <Stack direction='row' sx={{
            justifyContent: "space-between",
            alignItems: "center",
            gap: '1rem',
          }}>
            <Typography level='title-lg'>Inventory</Typography>
            <Stack direction='row' gap='1em'>
              <Button onClick={() => CLIENT.updateAllItemsDetailsApiItemsUpdateDetailsPost()}>Resync Details</Button>
              <Input
                sx={{
                  maxWidth: '25em',
                  flexGrow: 1,
                }}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                endDecorator={<SearchIcon />}
                placeholder="Search" />
            </Stack>
          </Stack>

          <Table>
            <thead>
              <tr>
                <th style={{
                  width: '3em'
                }}></th>
                {/* <th style={{
                  width: '16em'
                }}>Id</th> */}
                <th style={{
                  width: '4em'
                }}>SlotID</th>
                <th>Item Description</th>
                <th style={{
                  width: '8em'
                }}>Available</th>
                <th>Comments</th>
                <th style={{
                  width: '2em'
                }}></th>
                <th style={{
                  width: '2em'
                }}></th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => <OneRow item={item} key={item.id} refresh={refreshItems} updateItem={(f: MapSelf<ExistingInventoryItem>) => updateItem(item.id || '', f)} />)}
            </tbody>
          </Table>
        </Card>
      </div>
    </div>
  );
}

export default Inventory;
