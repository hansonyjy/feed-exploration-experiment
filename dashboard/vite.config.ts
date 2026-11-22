import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

// The site reads only committed exports (D61): ../exports is served as static files, so the page
// data lives at <base>/dashboard/*.json and the source CSVs can be linked for download.
export default defineConfig({
  base: "/feed-exploration-experiment/",
  publicDir: fileURLToPath(new URL("../exports", import.meta.url)),
  build: { outDir: "dist", emptyOutDir: true },
});
