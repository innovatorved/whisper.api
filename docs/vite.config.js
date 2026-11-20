import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import {
  loadAllDocs,
  renderDocPage,
  renderRootRedirectHtml,
  renderSitemapXml
} from "./src/lib/docs-builder.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONTENT_DIR = path.resolve(__dirname, "src/content");
const SITE_URL = process.env.SITE_URL ?? "https://whisper.vedgupta.in";

function whisperDocsPlugin() {
  return {
    name: "whisper-docs",

    configureServer(server) {
      server.watcher.add(CONTENT_DIR);
      server.watcher.on("change", (file) => {
        if (file.startsWith(CONTENT_DIR)) {
          server.ws.send({ type: "full-reload" });
        }
      });

      server.middlewares.use(async (req, res, next) => {
        const rawUrl = (req.url || "/").split("?")[0];
        if (rawUrl === "/") {
          res.statusCode = 302;
          res.setHeader("Location", "/docs");
          res.end();
          return;
        }

        const normalized = rawUrl.replace(/\/+$/, "");
        if (normalized === "/docs" || normalized.startsWith("/docs/")) {
          const allDocs = loadAllDocs(CONTENT_DIR);
          const slug = normalized === "/docs" ? "" : normalized.slice("/docs/".length);
          const entry = allDocs.find((d) => d.slug === slug);
          if (!entry) return next();

          const rawHtml = renderDocPage(entry, allDocs, {
            css: [],
            js: ["/src/main.js"]
          });
          const html = await server.transformIndexHtml(rawUrl, rawHtml);
          res.statusCode = 200;
          res.setHeader("Content-Type", "text/html; charset=utf-8");
          res.end(html);
          return;
        }

        next();
      });
    },

    generateBundle(_, bundle) {
      const css = [];
      const js = [];

      for (const item of Object.values(bundle)) {
        if (item.type === "asset" && item.fileName.endsWith(".css")) {
          css.push(`/${item.fileName}`);
        } else if (item.type === "chunk" && item.isEntry) {
          js.push(`/${item.fileName}`);
        }
      }

      const allDocs = loadAllDocs(CONTENT_DIR);
      for (const entry of allDocs) {
        const fileName = entry.slug === "" ? "docs/index.html" : `docs/${entry.slug}/index.html`;
        this.emitFile({
          type: "asset",
          fileName,
          source: renderDocPage(entry, allDocs, { css, js })
        });
      }

      this.emitFile({
        type: "asset",
        fileName: "index.html",
        source: renderRootRedirectHtml()
      });

      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source: renderSitemapXml(allDocs, SITE_URL)
      });
    }
  };
}

export default defineConfig({
  plugins: [tailwindcss(), whisperDocsPlugin()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, "src/main.js")
      }
    }
  }
});
