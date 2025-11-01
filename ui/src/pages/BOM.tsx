import { Button, Card, Input, Modal, ModalClose, ModalDialog, Stack, Table, Typography } from "@mui/joy";
import { useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import SearchIcon from '@mui/icons-material/Search';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import VisibilityIcon from '@mui/icons-material/Visibility';

import Header from "../Header";
import { ExistingBomOutput } from "../openapi/inventory";
import CLIENT from "./../client";
import { ErrorReporting } from "..";
import BomEntryTable from "./bom_components/BomEntryTable";
import BomUpload from "./bom_components/BomUpload";

function useAllBoms(): [ExistingBomOutput[], () => void] {
  const [data, setData] = useState([] as ExistingBomOutput[]);
  const setErr = useContext(ErrorReporting);

  const refresh = useCallback(() => {
    CLIENT.getAllBomsApiBomGet().then(setData).catch(setErr);
  }, [setErr]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return [data, refresh];
}

function BOM() {
  const [boms, refreshBoms] = useAllBoms();
  const [searchTerm, setSearchTerm] = useState('');
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedBom, setSelectedBom] = useState<ExistingBomOutput | null>(null);
  const setErr = useContext(ErrorReporting);

  const filteredBoms = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (term === '') {
      return boms;
    }
    return boms.filter(bom => {
      return (bom.name || '').toLowerCase().includes(term) ||
        (bom.project?.name || '').toLowerCase().includes(term) ||
        (bom.infoLine || '').toLowerCase().includes(term);
    });
  }, [boms, searchTerm]);

  const handleDelete = useCallback((bomId: string) => {
    if (window.confirm('Are you sure you want to delete this BOM?')) {
      CLIENT.deleteBomApiBomBomIdDelete({ bomId })
        .then(() => {
          refreshBoms();
        })
        .catch(setErr);
    }
  }, [setErr, refreshBoms]);

  const handleView = useCallback((bom: ExistingBomOutput) => {
    setSelectedBom(bom);
    setViewModalOpen(true);
  }, []);

  const handleUploadSuccess = useCallback(() => {
    setUploadModalOpen(false);
    refreshBoms();
  }, [refreshBoms]);

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
        <Card sx={{ width: "100%", maxWidth: "1400px" }}>
          <Stack direction='row' sx={{
            justifyContent: "space-between",
            alignItems: "center",
            gap: '1rem',
          }}>
            <Typography level='title-lg'>BOMs</Typography>
            <Stack direction='row' gap='1em' alignItems="center">
              <Button
                startDecorator={<UploadFileIcon />}
                onClick={() => setUploadModalOpen(true)}
                variant="outlined"
              >
                Upload
              </Button>
              <Button
                component={Link}
                to="/bom/new"
                startDecorator={<AddIcon />}
              >
                New BOM
              </Button>
              <Input
                sx={{
                  maxWidth: '25em',
                  flexGrow: 1,
                }}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                endDecorator={<SearchIcon />}
                placeholder="Search BOMs" />
            </Stack>
          </Stack>

          <Table>
            <thead>
              <tr>
                <th style={{ width: '20%' }}>Name</th>
                <th style={{ width: '20%' }}>Project</th>
                <th style={{ width: '15%' }}>Info Line</th>
                <th style={{ width: '10%' }}>Entries</th>
                <th style={{ width: '35%' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredBoms.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                    <Typography level="body-md" color="neutral">
                      {boms.length === 0 ? 'No BOMs found. Create one to get started!' : 'No BOMs match your search.'}
                    </Typography>
                  </td>
                </tr>
              ) : (
                filteredBoms.map(bom => (
                  <tr key={bom.id}>
                    <td>{bom.name || <Typography level="body-sm" color="neutral">(Unnamed)</Typography>}</td>
                    <td>{bom.project?.name || <Typography level="body-sm" color="neutral">-</Typography>}</td>
                    <td>{bom.infoLine || <Typography level="body-sm" color="neutral">-</Typography>}</td>
                    <td>{bom.rows?.length || 0}</td>
                    <td>
                      <Stack direction="row" gap="0.5rem">
                        <Button
                          size="sm"
                          variant="soft"
                          startDecorator={<VisibilityIcon />}
                          onClick={() => handleView(bom)}
                        >
                          View
                        </Button>
                        <Button
                          component={Link}
                          to={`/bom/${bom.id}/edit`}
                          size="sm"
                          variant="soft"
                          color="primary"
                          startDecorator={<EditIcon />}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="soft"
                          color="danger"
                          startDecorator={<DeleteIcon />}
                          onClick={() => bom.id && handleDelete(bom.id)}
                        >
                          Delete
                        </Button>
                      </Stack>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </Table>
        </Card>

        {/* View Modal */}
        <Modal open={viewModalOpen} onClose={() => {
          setViewModalOpen(false);
          setSelectedBom(null);
        }}>
          <ModalDialog sx={{ maxWidth: '1000px', width: '100%', maxHeight: '90vh', overflow: 'auto' }}>
            <ModalClose />
            <Typography level="h2">
              {selectedBom?.name || 'BOM Details'}
            </Typography>
            {selectedBom && (
              <Stack gap="1rem" sx={{ mt: 2 }}>
                <Stack direction="row" gap="2rem">
                  <Typography><strong>Name:</strong> {selectedBom.name || '(Unnamed)'}</Typography>
                  <Typography><strong>Project:</strong> {selectedBom.project?.name}</Typography>
                </Stack>
                <Typography><strong>Info Line:</strong> {selectedBom.infoLine}</Typography>
                {selectedBom.project && (
                  <Stack>
                    <Typography><strong>Author:</strong> {selectedBom.project.authorNames}</Typography>
                    <Typography><strong>Comments:</strong> {selectedBom.project.comments}</Typography>
                  </Stack>
                )}
                <Typography level="title-md">Entries ({selectedBom.rows?.length || 0})</Typography>
                <BomEntryTable entries={selectedBom.rows || []} />
              </Stack>
            )}
          </ModalDialog>
        </Modal>

        {/* Upload Modal */}
        <Modal open={uploadModalOpen} onClose={() => setUploadModalOpen(false)}>
          <ModalDialog sx={{ maxWidth: '600px', width: '100%' }}>
            <ModalClose />
            <Typography level="h2">Upload BOM</Typography>
            <BomUpload
              onSuccess={handleUploadSuccess}
              onCancel={() => setUploadModalOpen(false)}
            />
          </ModalDialog>
        </Modal>
      </div>
    </div>
  );
}

export default BOM;

