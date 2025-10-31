import { useContext, useEffect, useState } from "react";
import { ErrorReporting } from "../..";
import CLIENT from "./client";

export type MapSelf<T> = (a: T) => T;

export function useEnvironment(): 'prod' | 'dev' | 'test' {
  const [env, setEnv] = useState<'prod' | 'dev' | 'test'>('prod');
  const setErr = useContext(ErrorReporting);

  useEffect(() => {
    CLIENT.getEnvApiEnvGet().then(setEnv).catch(setErr);
  }, [setErr]);

  return env;
}
