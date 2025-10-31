import React, { createContext, useCallback, useReducer, useState } from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource/inter';
import { CssVarsProvider } from '@mui/joy/styles';
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";

import './index.css';
import Inventory from './pages/Inventory';
import { Snackbar } from '@mui/joy';
import ErrorIcon from '@mui/icons-material/Error';


const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

const basePath = process.env.REACT_APP_BASE_PATH || "/";

const router = createBrowserRouter([
  {
    path: basePath,
    children: [
      {
        path: "",
        element: <Inventory />,
      }
    ]
  }
]);

export const GlobalVars = createContext({} as GlobalVarsObj);

export const ErrorReporting = createContext(console.error as (err: any) => void);

interface GlobalVarsObj {
  getStored: (key: string) => string | null;
  setStored: (key: string, value: string | null) => void;
}

interface IAction {
  key: string;
  value: string | null;
}
type IState = Record<string, string | null>;

const LOCAL_STORAGE_KEY = 'electronic-inv-sys-ui-state';

function reducer(state: IState, action: IAction) {
  const newState = { ...state, [action.key]: action.value };
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(newState));
  return newState;
}

function TopLevel({ children }: { children?: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {}, (_) => {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
    else {
      return {} as IState;
    }
  });

  const getStored = useCallback((key: string) => {
    return state[key];
  }, [state]);

  const setStored = useCallback((key: string, value: string | null) => {
    dispatch({ key, value });
  }, [dispatch]);

  const [error, setErrorStr] = useState<string | null>(null);

  const setError = useCallback((err: any) => {
    if (err) {
      console.error(err);
    }
    setErrorStr(err + []);
  }, [setErrorStr]);



  return (
    <GlobalVars.Provider value={{
      getStored,
      setStored,
    }}>
      <ErrorReporting.Provider value={setError}>
        {children}
      </ErrorReporting.Provider>
      <Snackbar
        color='danger'
        autoHideDuration={20000}
        open={error !== null}
        variant='soft'
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        onClose={() => setErrorStr(null)}
        endDecorator={<ErrorIcon />}>
        {error}
      </Snackbar>
    </GlobalVars.Provider>
  );
}

root.render(
  <React.StrictMode>
    <CssVarsProvider defaultMode="system">
      <TopLevel>
        <RouterProvider router={router} />
      </TopLevel>
    </CssVarsProvider>
  </React.StrictMode>
);

