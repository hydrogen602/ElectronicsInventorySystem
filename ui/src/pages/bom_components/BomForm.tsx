import { Button, FormControl, FormLabel, Input, Stack, Textarea, Typography } from "@mui/joy";
import { useState, useEffect } from "react";
import { ExistingBomOutput, NewBomInput, BomEntry, ProjectInfo } from "../../openapi/inventory";
import BomEntryEditor from "./BomEntryEditor";
import { createPortal } from "react-dom";

interface BomFormProps {
  bom?: ExistingBomOutput;
  onSubmit: (bom: ExistingBomOutput | NewBomInput) => void;
  onCancel: () => void;
  menuRef: React.RefObject<HTMLDivElement>;
}

export default function BomForm({ bom, onSubmit, onCancel, menuRef }: BomFormProps) {
  const [name, setName] = useState(bom?.name || '');
  const [infoLine, setInfoLine] = useState(bom?.infoLine || '');
  const [projectName, setProjectName] = useState(bom?.project?.name || '');
  const [authorNames, setAuthorNames] = useState(bom?.project?.authorNames || '');
  const [projectComments, setProjectComments] = useState(bom?.project?.comments || '');
  const [rows, setRows] = useState<BomEntry[]>(bom?.rows || []);

  useEffect(() => {
    if (bom) {
      setName(bom.name || '');
      setInfoLine(bom.infoLine || '');
      setProjectName(bom.project?.name || '');
      setAuthorNames(bom.project?.authorNames || '');
      setProjectComments(bom.project?.comments || '');
      setRows(bom.rows || []);
    }
  }, [bom]);

  const handleSubmit = () => {
    const project: ProjectInfo = {
      name: projectName || null,
      authorNames: authorNames || null,
      comments: projectComments || '',
    };

    if (bom) {
      const updatedBom: ExistingBomOutput = {
        id: bom.id,
        name: name || null,
        infoLine: infoLine || null,
        project,
        rows,
      };
      onSubmit(updatedBom);
    } else {
      const newBom: NewBomInput = {
        name: name || null,
        infoLine: infoLine || null,
        project,
        rows,
      };
      onSubmit(newBom);
    }
  };

  const addEntry = () => {
    const newEntry: BomEntry = {
      qty: 1,
      device: '',
      value: null,
      description: null,
      manufacturer: null,
      comments: '',
      parts: [],
      inventoryItemMappingIds: new Set(),
      fusion360Ext: null,
    };
    setRows([...rows, newEntry]);
  };

  const updateEntry = (index: number, entry: BomEntry) => {
    const newRows = [...rows];
    newRows[index] = entry;
    setRows(newRows);
  };

  const removeEntry = (index: number) => {
    setRows(rows.filter((_, i) => i !== index));
  };

  return (
    <Stack gap="1.5rem" sx={{ mt: 2 }}>
      {
        menuRef.current && createPortal(
          <Stack direction="row" gap="1rem" justifyContent="flex-end">
            <Button variant="outlined" onClick={onCancel}>Cancel</Button>
            <Button onClick={handleSubmit}>
              {bom ? 'Update' : 'Create'} BOM
            </Button>
          </Stack>,
          menuRef.current
        )
      }

      <Stack gap="1rem">
        <FormControl>
          <FormLabel>Name</FormLabel>
          <Input
            placeholder="BOM Name (optional)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </FormControl>
        <FormControl>
          <FormLabel>Info Line</FormLabel>
          <Input
            placeholder="Info Line (optional)"
            value={infoLine}
            onChange={(e) => setInfoLine(e.target.value)}
          />
        </FormControl>
      </Stack>

      <Stack gap="1rem">
        <Typography level="title-sm">Project Information</Typography>
        <FormControl>
          <FormLabel>Project Name</FormLabel>
          <Input
            placeholder="Project Name (optional)"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
          />
        </FormControl>
        <FormControl>
          <FormLabel>Author Names</FormLabel>
          <Input
            placeholder="Author Names (optional)"
            value={authorNames}
            onChange={(e) => setAuthorNames(e.target.value)}
          />
        </FormControl>
        <FormControl>
          <FormLabel>Project Comments</FormLabel>
          <Textarea
            placeholder="Project Comments"
            value={projectComments}
            onChange={(e) => setProjectComments(e.target.value)}
            minRows={2}
          />
        </FormControl>
      </Stack>



      <Stack gap="1rem">
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography level="title-sm">BOM Entries ({rows.length})</Typography>
          <Button size="sm" onClick={addEntry}>Add Entry</Button>
        </Stack>
        <Stack gap="1rem">
          {rows.map((entry, index) => (
            <BomEntryEditor
              key={index}
              entry={entry}
              index={index}
              onUpdate={(updatedEntry) => updateEntry(index, updatedEntry)}
              onRemove={() => removeEntry(index)}
            />
          ))}
          {rows.length === 0 && (
            <Typography level="body-sm" color="neutral">
              No entries. Click "Add Entry" to add one.
            </Typography>
          )}
        </Stack>
      </Stack>

      <Stack direction="row" gap="1rem" justifyContent="flex-end">
        <Button variant="outlined" onClick={onCancel}>Cancel</Button>
        <Button onClick={handleSubmit}>
          {bom ? 'Update' : 'Create'} BOM
        </Button>
      </Stack>
    </Stack>
  );
}

