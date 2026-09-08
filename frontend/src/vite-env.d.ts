/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_ENTRA_TENANT_ID?: string;
  readonly VITE_ENTRA_WEB_CLIENT_ID?: string;
  readonly VITE_ENTRA_API_CLIENT_ID?: string;
  readonly VITE_AI_D3_SYNTHETIC_PROJECT_IDS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
