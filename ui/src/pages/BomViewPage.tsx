import { Button, Card, Stack, Typography } from "@mui/joy";
import { useContext, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import Header from "../Header";
import { ExistingBomOutput } from "../openapi/inventory";
import CLIENT from "../client";
import { ErrorReporting } from "..";
import BomEntryTable from "./bom_components/BomEntryTable";

function BomViewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const setErr = useContext(ErrorReporting);
  const [bom, setBom] = useState<ExistingBomOutput | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) {
      navigate('/bom');
      return;
    }

    setLoading(true);
    CLIENT.getBomApiBomBomIdGet({ bomId: id })
      .then(setBom)
      .catch((error) => {
        setErr(error);
        navigate('/bom');
      })
      .finally(() => setLoading(false));
  }, [id, navigate, setErr]);

  if (loading) {
    return (
      <div>
        <Header />
        <div style={{
          margin: "3rem",
          display: "flex",
          justifyContent: "center",
        }}>
          <Typography>Loading...</Typography>
        </div>
      </div>
    );
  }

  if (!bom) {
    return null;
  }

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
        <Card sx={{
          width: "100%", maxWidth: "1400px",
          '@media print': {
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            width: '100vw',
            zIndex: 1000,
            maxWidth: 'none',
            boxSizing: 'border-box',
            borderRadius: 0,
          }
        }}>
          <Stack direction="row" alignItems="center" gap="1rem" sx={{ mb: 2 }}>
            <Button
              component={Link}
              to="/bom"
              variant="outlined"
              sx={{
                '@media print': {
                  display: 'none',
                }
              }}
              startDecorator={<ArrowBackIcon />}
            >
              Back
            </Button>
            <Typography level="h2">
              {bom.name || 'BOM Details'}
            </Typography>
          </Stack>

          <Stack gap="1rem">
            <Stack direction="row" gap="2rem">
              <Typography><strong>Name:</strong> {bom.name || '(Unnamed)'}</Typography>
              <Typography><strong>Project:</strong> {bom.project?.name || '-'}</Typography>
            </Stack>
            {bom.infoLine && (
              <Typography><strong>Info Line:</strong> {bom.infoLine}</Typography>
            )}
            {bom.project && (
              <Stack gap="0.5rem">
                {bom.project.authorNames && (
                  <Typography><strong>Author:</strong> {bom.project.authorNames}</Typography>
                )}
                {bom.project.comments && (
                  <Typography><strong>Comments:</strong> {bom.project.comments}</Typography>
                )}
              </Stack>
            )}
            <Typography level="title-md">Entries ({bom.rows?.length || 0})</Typography>
            <BomEntryTable entries={bom.rows || []} />
          </Stack>
        </Card>
      </div>
    </div>
  );
}

export default BomViewPage;

