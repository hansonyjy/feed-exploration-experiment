import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

// The site reads only committed exports (D61): ../exports is served as static files, so the page
// data lives at <base>/dashboard/*.json and the source CSVs can be linked for download.
// Repo links point at the exact commit the site was built from, so they never 404 and always match
// the data on the page. CI sets GITHUB_SHA; local builds use the checked-out commit.
const commit = process.env.GITHUB_SHA ?? execSync("git rev-parse HEAD").toString().trim();

export default defineConfig({
  define: { __COMMIT__: JSON.stringify(commit) },
  base: "/feed-exploration-experiment/",
  publicDir: fileURLToPath(new URL("../exports", import.meta.url)),
  build: { outDir: "dist", emptyOutDir: true },
});
