// Build separado, só pra gerar o bundle estático que o FastAPI serve.
// Não usa o app TanStack Start (src/router.tsx, __root.tsx, nitro) — só importa
// o componente Index de src/routes/index.tsx direto, sem SSR/roteador.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "static-entry",
  plugins: [react()],
  build: {
    outDir: "../../app/static/app",
    emptyOutDir: true,
  },
});
