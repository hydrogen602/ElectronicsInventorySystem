import { Button, FormControl, FormLabel, Input, Stack, Typography } from "@mui/joy";
import { useState, useContext, useRef } from "react";
import UploadFileIcon from '@mui/icons-material/UploadFile';

import { ErrorReporting } from "../..";
import CLIENT from "./../../client";
import { NewBomInput, NewBomOutput } from "../../openapi/inventory";

interface BomUploadProps {
  onSuccess: (bom?: NewBomOutput) => void;
  onCancel: () => void;
}

export default function BomUpload({ onSuccess, onCancel }: BomUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [src, setSrc] = useState('fusion360');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const setErr = useContext(ErrorReporting);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setErr(new Error('Please select a file to upload'));
      return;
    }

    setUploading(true);
    try {
      const bom = await CLIENT.uploadZipApiBomParseGerberExportPost({
        file: file,
        src: src,
      });

      // Create the BOM after parsing
      // NewBomOutput and NewBomInput have the same structure
      await CLIENT.createBomApiBomPost({
        newBomInput: bom
      });

      setUploading(false);
      onSuccess(bom);
    } catch (error) {
      setUploading(false);
      setErr(error);
    }
  };

  return (
    <Stack gap="1.5rem" sx={{ mt: 2 }}>
      <Typography level="body-md">
        Upload a ZIP file containing Gerber export files to parse and create a new BOM.
      </Typography>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".zip,application/zip,application/x-zip-compressed"
        style={{ display: 'none' }}
      />

      <Stack gap="1rem">
        <Button
          variant="outlined"
          startDecorator={<UploadFileIcon />}
          onClick={() => fileInputRef.current?.click()}
        >
          {file ? file.name : 'Select ZIP File'}
        </Button>

        {file && (
          <Typography level="body-sm" color="success">
            Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
          </Typography>
        )}

        <FormControl required>
          <FormLabel>BOM Source</FormLabel>
          <Input
            placeholder="Source (e.g., fusion360)"
            value={src}
            onChange={(e) => setSrc(e.target.value)}
          />
        </FormControl>
      </Stack>

      <Stack direction="row" gap="1rem" justifyContent="flex-end">
        <Button variant="outlined" onClick={onCancel} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          disabled={!file || !src || uploading}
          loading={uploading}
        >
          Upload & Create BOM
        </Button>
      </Stack>
    </Stack>
  );
}

