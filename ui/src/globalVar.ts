import { useCallback, useContext } from "react";
import { GlobalVars } from ".";

export function useGlobalVars(key: string) {
  const { getStored, setStored } = useContext(GlobalVars);

  const value = getStored(key);

  const setValue = useCallback((col: string | null) => {
    setStored(key, col);
  }, [setStored, key]);

  return { value, setValue };
}
