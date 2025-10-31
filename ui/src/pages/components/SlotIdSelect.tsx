import { Box, Chip, ChipDelete, Input, Stack, Typography } from "@mui/joy";
import { useContext, useState } from "react";

import { ErrorReporting } from "../..";

export interface SlotIdSelectProps {
  slotIds: Set<number>;
  deleteSlotId: (slotId: number) => void;
  addSlotId: (slotId: number) => void;
}

export default function SlotIdSelect({ slotIds, deleteSlotId, addSlotId }: SlotIdSelectProps) {
  const setErr = useContext(ErrorReporting);

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

  return (
    <Stack direction='column' alignContent='center' alignItems='center' justifyContent='center' justifyItems='center' sx={{ margin: '1rem' }}>
      <Typography>Slot IDs</Typography>
      <Box style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
        {Array.from(slotIds).map(slotId => (
          <Chip
            key={slotId}
            variant="soft"
            color="primary"
            size="md"
            endDecorator={<ChipDelete onDelete={() => deleteSlotId(slotId)} />}
          >
            {renderSlotId(slotId)}
          </Chip>
        ))}
        <form onSubmit={(event) => {
          event.preventDefault();
          const newSlot = getNewSlot();
          if (newSlot === null) {
            setErr('Invalid slot ID');
            return;
          }

          addSlotId(newSlot);
          setNewSlotId('');
        }}>
          <Input placeholder="new" sx={{ width: '4rem' }} value={newSlotId} onChange={e => {
            // filter out non-hex characters
            setNewSlotId(e.target.value.replace(/[^0-9A-Fa-f]/g, ''));
          }} error={getNewSlot() === null && newSlotId !== ''} />
        </form>
      </Box>
    </Stack >
  );
}