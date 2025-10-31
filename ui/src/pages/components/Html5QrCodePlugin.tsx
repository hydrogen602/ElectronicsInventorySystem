// file = Html5QrcodePlugin.tsx
import { Html5QrcodeResult, Html5QrcodeScanner, Html5QrcodeScanType, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import { Html5QrcodeScannerConfig } from 'html5-qrcode/esm/html5-qrcode-scanner';
import { useEffect, useId, useRef } from 'react';


let useEffectCount = 0;

// Props interface for the Html5QrcodePlugin component
interface Html5QrcodePluginProps {
  fps?: number;
  qrbox?: number | { width: number; height: number };
  aspectRatio?: number;
  verbose?: boolean;
  qrCodeSuccessCallback: (decodedText: string, decodedResult: Html5QrcodeResult) => void;
  qrCodeErrorCallback?: (error: string) => void;
  formatsToSupport?: Html5QrcodeSupportedFormats[];
}


function Html5QrcodePlugin(props: Html5QrcodePluginProps) {
  const nodeId = useId();
  const div = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const call = useEffectCount++;

    if (!div.current) {
      throw new Error(`Html5QrcodePlugin - useEffect - div not found. call=${call} nodeId=${nodeId}`);
    }

    // when component mounts
    const config: Html5QrcodeScannerConfig = {
      fps: props.fps,
      qrbox: props.qrbox,
      aspectRatio: props.aspectRatio,
      disableFlip: false,
      formatsToSupport: props.formatsToSupport,
      useBarCodeDetectorIfSupported: true,
    };


    const verbose = props.verbose === true;

    const elem = document.createElement('div');
    elem.id = `html5qr-code-full-region-${nodeId}-${call}`;
    div.current.appendChild(elem);

    const thisScanner = new Html5QrcodeScanner(elem.id, config, verbose);

    async function clear() {
      try {
        await thisScanner.clear();
        console.log(`Html5QrcodePlugin - clear done. call=${call}, nodeId=${nodeId}, state=${thisScanner.getState()}`);
      } catch (error) {
        console.error(`Failed to clear html5QrcodeScanner. call=${call}, error=${error}`);
      }
      div.current?.removeChild(elem);
    }

    console.log(`Html5QrcodePlugin - render. call=${call}, nodeId=${nodeId}`);
    thisScanner.render((text, result) => {
      props.qrCodeSuccessCallback(text, result);
      clear();
    }, props.qrCodeErrorCallback);

    // cleanup function when component will unmount
    return () => {
      console.log(`Html5QrcodePlugin - useEffect - cleanup. call=${call}, nodeId=${nodeId}`);
      clear();
    };
  }, [props, nodeId]);

  return (
    <div ref={div} />
  );
};

export default Html5QrcodePlugin;