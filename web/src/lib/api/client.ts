import createClient from "openapi-fetch";

import type { paths } from "./generated/schema";
import { getPublicApiBaseUrl } from "./config";

export const apiClient = createClient<paths>({
  baseUrl: getPublicApiBaseUrl(),
  credentials: "include",
});
