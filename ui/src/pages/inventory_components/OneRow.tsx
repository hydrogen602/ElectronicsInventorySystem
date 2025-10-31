import { Button, Chip, ChipDelete, Divider, IconButton, Input, Link, Sheet, Stack, Tab, TabList, TabPanel, Tabs, Tooltip, Typography } from "@mui/joy";
import { Fragment, useContext, useEffect, useState } from "react";
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import LaunchIcon from '@mui/icons-material/Launch';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';


import { ExistingInventoryItem } from "../../openapi/inventory";
import { ErrorReporting } from "../..";
import CLIENT from "./client";
import { MapSelf } from "./utils";
import SlotIdSelect from "../components/SlotIdSelect";



function OneRow({ item, refresh, updateItem }: { item: ExistingInventoryItem, refresh: () => void, updateItem: (f: MapSelf<ExistingInventoryItem>) => void }) {
  const [open, setOpen] = useState(false);

  const setErr = useContext(ErrorReporting);

  const setQuantity = async (quantity: number) => {
    try {
      if (typeof item.id !== 'string') {
        throw new Error('Item id is not a string, cannot set quantity');
      }
      await CLIENT.setQuantityApiItemItemIdQuantityPost({
        itemId: item.id,
        quantity: quantity
      });
      refresh();
    } catch (e) {
      setErr(e);
    };
  };

  const setComment = async (comment: string) => {
    try {
      if (typeof item.id !== 'string') {
        throw new Error('Item id is not a string, cannot set comment');
      }
      await CLIENT.setCommentsApiItemItemIdCommentsPost({
        itemId: item.id,
        comments: comment
      });
      refresh();
    } catch (e) {
      setErr(e);
    };
  };

  const [tempComment, setTempComment] = useState(item.comments || '');

  useEffect(() => {
    setTempComment(item.comments || '');
  }, [item.comments]);

  const warnings: number | null = item.productDetails?.productWarnings === undefined ? null : (item.productDetails.productWarnings?.length || null);

  const image_url = item.productDetails?.imageUrl || null;

  function renderSlotId(slotId: number): string {
    return slotId.toString(16)?.toUpperCase().padStart(2, '0');
  }

  const [newSlotId, setNewSlotId] = useState('');

  function getNewSlot(): number | null {
    const newSlotIdTrimmed = newSlotId.toLowerCase().trim();
    const newSlot = parseInt(newSlotIdTrimmed, 16);
    if (newSlot.toString(16) !== newSlotIdTrimmed || Number.isNaN(newSlot)) {
      return null;
    }
    return newSlot;
  }

  return (<>
    <tr >
      {/* <td>
      <code>{doc.id}</code>
    </td> */}
      <td>
        <IconButton
          aria-label="expand row"
          variant="plain"
          color="neutral"
          size="sm"
          onClick={() => setOpen(!open)}
        >
          {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
        </IconButton>
      </td>
      <td>
        <code>{Array.from(item.slotIds).map(renderSlotId).join(', ')}</code>
      </td>
      <td>
        <Stack direction='row' alignItems='center' gap='0.5em'>
          {image_url && <img src={image_url} alt={item.itemDescription || ''} style={{
            width: '3em',
            height: '3em',
          }}></img>}
          {item.itemDescription}
        </Stack>
      </td>
      <td>
        {item.availableQuantity}
      </td>
      <td>
        {item.comments}
      </td>
      <td>
        {item.productDetails?.datasheetUrl &&
          <Link
            underline="none"
            variant="plain"
            href={item.productDetails?.datasheetUrl}
            sx={{
              borderRadius: '50%',
              padding: '8px',
            }}
            level="h4"><LaunchIcon /></Link>}
      </td>
      <td>
        {warnings !== null && warnings > 0 &&
          <Stack direction='column' justifyContent='center' alignItems='center'>
            <Tooltip
              title={
                (item.productDetails?.productWarnings || []).map(warn => <Typography sx={{
                  fontWeight: 'bold',
                  margin: '0.5rem',
                }} color='warning' key={warn}>{warn}</Typography>)
              }
              arrow
              color="warning"
              placement="left"
              size="md"
              variant="soft">
              <WarningAmberIcon sx={{
                padding: '8px',
              }} color='warning' />
            </Tooltip>
          </Stack>
        }
      </td>
    </tr>
    <tr>
      <td style={{ height: 0, padding: 0 }} colSpan={7}>
        {open && (
          <Sheet>
            <Stack direction='row'>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', margin: '1rem' }}>
                <Typography>Available Quantity</Typography>
                <Button onClick={() => {
                  const newQuantity = Math.max(0, item.availableQuantity - 1);
                  updateItem(item => ({ ...item, availableQuantity: newQuantity }));
                  setQuantity(newQuantity);
                }}>-</Button>
                <Typography>{item.availableQuantity}</Typography>
                <Button onClick={() => {
                  const newQuantity = item.availableQuantity + 1;
                  updateItem(item => ({ ...item, availableQuantity: newQuantity }));
                  setQuantity(newQuantity);
                }}>+</Button>
              </div>
              <Divider orientation="vertical" />
              <SlotIdSelect slotIds={item.slotIds} deleteSlotId={slotId => {
                CLIENT.removeItemFromSlotApiItemItemIdSlotSlotIdDelete({
                  itemId: item.id,
                  slotId: slotId
                }).then(() => refresh()).catch(setErr);
              }} addSlotId={slotId => {
                CLIENT.addItemToSlotApiItemItemIdSlotSlotIdPut({
                  itemId: item.id,
                  slotId: slotId
                }).then(() => refresh()).catch(setErr);
              }} />
              <Divider orientation="vertical" />
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', margin: '1rem', flexGrow: 1 }}>
                <Typography>Comments</Typography>
                <Input
                  sx={{
                    flexGrow: 1,
                    width: '100%',
                  }}
                  value={tempComment}
                  onChange={e => setTempComment(e.target.value)}
                  onKeyDown={async e => {
                    if (e.key === 'Enter') {
                      updateItem(item => ({ ...item, comments: tempComment }));
                      await setComment(tempComment);
                      (e.target as HTMLElement).blur();
                    }
                  }}
                  endDecorator={<Button onClick={() => {
                    updateItem(item => ({ ...item, comments: tempComment }));
                    setComment(tempComment);
                  }}>Save</Button>}
                />
              </div>
              <Divider orientation="vertical" />

            </Stack>

            <Divider />
            {(item.productDetails?.productWarnings || []).map(warn => <Typography sx={{
              fontWeight: 'bold',
              margin: '0.5rem',
            }} color='warning' key={warn}>{warn}</Typography>)}
            <Divider />
            <Tabs
              orientation="horizontal"
              size="md"
              defaultValue={0}
            >
              <TabList>
                <Tab
                  variant="plain"
                  color="neutral">Details</Tab>
                <Tab
                  variant="plain"
                  color="neutral">Raw JSON</Tab>
              </TabList>
              <TabPanel value={0}>
                <Stack gap={'1ex'}>
                  {item.productDetails?.productUrl && <Link href={item.productDetails?.productUrl} endDecorator={<LaunchIcon />}>Product Page</Link>}

                  {item.productDetails?.datasheetUrl && <Link href={item.productDetails?.datasheetUrl} endDecorator={<LaunchIcon />}>Datasheet</Link>}

                  <Typography>Digikey Part Number: {item.digikeyPartNumber}</Typography>
                  <Typography>Manufacturer: {item.manufacturerName}</Typography>
                  <Typography>Manufacturer Part Number: {item.manufacturerPartNumber}</Typography>

                  {item.digikeyOrders?.map(order => (
                    <Fragment key={`${order.invoiceId}-${order.salesOrderId}`}>
                      <Divider />
                      <Typography>Invoice ID: {order.invoiceId}, Sales Order ID: {order.salesOrderId}</Typography>
                      <ul>
                        <li>
                          Quantity: {order.quantity}
                        </li>
                        {order.lotCode && <li>
                          Lot Code: {order.lotCode}
                        </li>}
                        {order.countryOfOrigin && <li>
                          Country of Origin: {order.countryOfOrigin}
                        </li>}
                      </ul>
                    </Fragment>
                  ))}
                </Stack>

              </TabPanel>
              <TabPanel value={1}>
                <pre style={{
                  whiteSpace: 'pre-wrap',
                  padding: '1rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #ccc',
                  wordBreak: 'break-all',
                  boxShadow: 'inset 0 0 1rem rgba(0,0,0,0.1)',
                }}>
                  {JSON.stringify(item, null, 2)}
                </pre>
              </TabPanel>
            </Tabs>

          </Sheet>
        )} </td>
    </tr >
  </>
  );

}

export default OneRow;