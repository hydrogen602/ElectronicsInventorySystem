import { useColorScheme } from "@mui/joy";

export function useColorMode(): 'light' | 'dark' | undefined {
  const { mode, systemMode } = useColorScheme();
  if (mode === "system") {
    return systemMode;
  }
  return mode;
}