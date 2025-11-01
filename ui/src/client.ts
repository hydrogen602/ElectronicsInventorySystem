import { Configuration, DefaultApi } from "./openapi/inventory";

export const BASE_URL = process.env.REACT_APP_INV_API as string;
console.log(`Connecting to ${BASE_URL}`);

export const CONFIG = new Configuration({
  basePath: BASE_URL,
});

export const CLIENT = new DefaultApi(CONFIG);

export default CLIENT;
