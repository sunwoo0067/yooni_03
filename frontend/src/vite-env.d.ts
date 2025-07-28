/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  // 더 많은 env 변수들...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}