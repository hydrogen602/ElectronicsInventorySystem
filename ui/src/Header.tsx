import { Box, Button, Divider, Stack, Typography, useColorScheme } from '@mui/joy';
import { Link as RouterLink, useLocation, useSearchParams } from 'react-router-dom';
import Link from '@mui/joy/Link';
import { useLayoutEffect } from 'react';
import { useColorMode } from './utils';

function LinkTo({ to, title, location }: { to: string, title: string, location: string }) {
  return (
    <Link component={RouterLink} to={to} level="title-lg" underline="none" disabled={location === to}
      variant={location === to ? "solid" : "plain"}
    >
      <Typography level='title-lg' >
        {title}
      </Typography>
    </Link>
  );
}

function Header(props: { tools?: JSX.Element }) {
  let location = useLocation().pathname;
  const [searchParams] = useSearchParams();

  const mode = useColorMode();
  const { setMode } = useColorScheme();

  // Check for mode query parameter and set color mode if valid
  const modeParam = searchParams.get('mode');

  useLayoutEffect(() => {
    // Set mode from query parameter if valid
    if (modeParam === 'light' || modeParam === 'dark') {
      setMode(modeParam);
    }

    // Set background color
    document.body.style.backgroundColor = mode === "light" ? "whitesmoke" : "#222";
  }, [modeParam, setMode, mode]);

  if (mode !== "light" && mode !== "dark" && mode !== undefined) {
    throw new Error("Invalid color scheme detected!!! " + mode);
  }

  // Don't render header if standalone=false query param is present
  if (searchParams.get('standalone') === 'false') {
    return null;
  }

  return <div style={{
    position: "sticky",
    top: 0,
    left: 0,
    right: 0,
    marginLeft: 0,
    marginRight: 0,
    zIndex: 1000,
  }}>
    <Box sx={{
      backgroundColor: mode === "light" ? "white" : "#333",
      padding: "1rem",
      display: "flex",
      flexDirection: {
        xs: "column",
        md: "row"
      },
      justifyContent: {
        xs: "center",
        md: "space-between",
      },
      alignItems: "center",
      gap: "2rem",

      // width: "calc(100vw - 2rem)", // 2rem padding -> left and right already does this
    }} component="header">
      <Stack direction="row" gap="2rem">
        <LinkTo to="/" title="Inventory" location={location} />
      </Stack>
      <Stack direction="row" gap="2rem" alignItems="center">
        {props.tools}
        <Button variant="soft" onClick={() => setMode(mode === "light" ? "dark" : "light")}>
          {mode === "light" ? "Dark" : "Light"}
        </Button>
      </Stack>

    </Box>
    <Divider />
  </div >;
}

export default Header;
