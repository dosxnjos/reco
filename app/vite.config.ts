import { defineConfig, searchForWorkspaceRoot } from "vite";

// A interface mora em app/ui; o Tauri carrega app/ui/dist no release e http://localhost:1430 em dev
// (src-tauri/tauri.conf.json). A porta 1430 não colide com a 1420 do Lacre (F3-D10).
// fs.allow: sem o primeiro item o Vite deixa de servir a própria pasta; o segundo (relativo a app/ui)
// libera design/tokens.css do design system do Reco.
export default defineConfig({
  root: "ui",
  clearScreen: false,
  base: "./",
  server: {
    port: 1430,
    strictPort: true,
    host: "localhost",
    watch: { ignored: ["**/src-tauri/**"] },
    fs: { allow: [searchForWorkspaceRoot(process.cwd()), "../../design"] },
  },
  envPrefix: ["VITE_", "TAURI_ENV_"],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2021",
    sourcemap: false,
    // O app nunca carrega nada da rede.
    assetsInlineLimit: 100000,
  },
});
