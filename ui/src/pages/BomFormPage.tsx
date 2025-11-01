import { Box, Button, Card, Stack, Typography } from "@mui/joy";
import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import Header from "../Header";
import { ExistingBomOutput, NewBomInput } from "../openapi/inventory";
import CLIENT from "../client";
import { ErrorReporting } from "..";
import BomForm from "./bom_components/BomForm";

function BomFormPage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const setErr = useContext(ErrorReporting);
  const [bom, setBom] = useState<ExistingBomOutput | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const isEdit = !!id;

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      CLIENT.getBomApiBomBomIdGet({ bomId: id })
        .then(setBom)
        .catch((error) => {
          setErr(error);
          navigate('/bom');
        })
        .finally(() => setLoading(false));
    }
  }, [id, isEdit, setErr, navigate]);

  const handleSubmit = useCallback(async (bomData: ExistingBomOutput | NewBomInput) => {
    try {
      if (isEdit && id) {
        await CLIENT.updateBomApiBomBomIdPut({
          bomId: id,
          existingBomInput: bomData as ExistingBomOutput,
        });
      } else {
        await CLIENT.createBomApiBomPost({
          newBomInput: bomData as NewBomInput,
        });
      }
      navigate('/bom');
    } catch (error) {
      setErr(error);
    }
  }, [isEdit, id, navigate, setErr]);

  const handleCancel = useCallback(() => {
    navigate('/bom');
  }, [navigate]);

  const menuRef = useRef<HTMLDivElement>(null);

  if (isEdit && loading) {
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
          <Stack direction="row" alignItems="center" gap="1rem" sx={{ mb: 2 }} ref={menuRef}>
            <Button
              component={Link}
              to="/bom"
              variant="outlined"
              startDecorator={<ArrowBackIcon />}
            >
              Back
            </Button>
            <Typography level="h2">
              {isEdit ? 'Edit BOM' : 'Create New BOM'}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
          </Stack>

          <BomForm
            bom={bom}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            menuRef={menuRef}
          />
        </Card>
      </div>
    </div>
  );
}

export default BomFormPage;

