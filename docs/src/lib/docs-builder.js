import fs from "node:fs";
import path from "node:path";
import { Marked } from "marked";
import { parse as parseYaml } from "yaml";

const ORDER = [
  "index",
  "getting-started",
  "authentication",
  "api-reference",
  "streaming",
  "models",
  "docker",
  "code-examples",
  "contributing"
];

function escapeHtml(str = "") {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function dedent(text) {
  const lines = text.replace(/^\n+|\n+$/g, "").split("\n");
  const indents = lines
    .filter((l) => l.trim().length > 0)
    .map((l) => l.match(/^[ \t]*/)[0].length);
  const minIndent = indents.length ? Math.min(...indents) : 0;
  return lines.map((l) => l.slice(minIndent)).join("\n");
}

function parseFrontmatter(raw) {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!match) return { data: {}, body: raw };
  return {
    data: parseYaml(match[1]) || {},
    body: match[2]
  };
}

function parseAttrs(attrString) {
  const attrs = {};
  const re = /([a-zA-Z0-9_-]+)="([^"]*)"/g;
  let m;
  while ((m = re.exec(attrString))) {
    attrs[m[1]] = m[2];
  }
  return attrs;
}

function createMarkdownRenderer(collectHeadings = false) {
  const headings = [];
  const slugCounts = new Map();
  const marked = new Marked({ gfm: true, breaks: false });

  marked.use({
    renderer: {
      heading({ tokens, depth }) {
        const html = this.parser.parseInline(tokens);
        const plain = html
          .replace(/<[^>]+>/g, "")
          .replace(/&amp;/g, "&")
          .replace(/&lt;/g, "<")
          .replace(/&gt;/g, ">")
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
          .trim();

        const baseSlug = plain
          .toLowerCase()
          .replace(/[^\w\s-]/g, "")
          .trim()
          .replace(/\s+/g, "-");

        const count = slugCounts.get(baseSlug) ?? 0;
        slugCounts.set(baseSlug, count + 1);
        const slug = count === 0 ? baseSlug : `${baseSlug}-${count}`;

        if (collectHeadings) {
          headings.push({ depth, slug, text: plain });
        }
        return `<h${depth} id="${slug}">${html}</h${depth}>\n`;
      }
    }
  });

  return { marked, headings };
}

function renderAside(type, innerHtml) {
  const t = type === "tip" || type === "caution" ? type : "note";
  const config = {
    tip: {
      box: "border-[var(--ds-success-border)] bg-[var(--ds-success-bg)]",
      iconColor: "text-[var(--ds-success)]",
      label: "Tip",
      icon: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" class="h-4 w-4 shrink-0" aria-hidden="true"><path d="M8 2a4 4 0 0 1 2.2 7.34c-.45.3-.7.78-.7 1.32V11h-3v-.34c0-.54-.25-1.02-.7-1.32A4 4 0 0 1 8 2Z" /><path d="M6.5 13h3" /></svg>`
    },
    note: {
      box: "border-[var(--ds-info-border)] bg-[var(--ds-info-bg)]",
      iconColor: "text-[var(--ds-info)]",
      label: "Note",
      icon: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" class="h-4 w-4 shrink-0" aria-hidden="true"><circle cx="8" cy="8" r="6" /><path d="M8 7v4m0-6h.01" /></svg>`
    },
    caution: {
      box: "border-[var(--ds-warning-border)] bg-[var(--ds-warning-bg)]",
      iconColor: "text-[var(--ds-warning)]",
      label: "Caution",
      icon: `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" class="h-4 w-4 shrink-0" aria-hidden="true"><path d="M8 2.2 14 13H2L8 2.2Z" /><path d="M8 6.5v3m0 2h.01" /></svg>`
    }
  }[t];

  return `<aside class="my-5 rounded-lg border px-4 py-3.5 text-[14px] leading-[1.6] text-[var(--ds-ink-prose)] ${config.box}">
  <div class="mb-1 flex items-center gap-1.5 text-[12px] font-semibold ${config.iconColor}">
    ${config.icon}
    <span>${config.label}</span>
  </div>
  <div class="[&>p:first-child]:mt-0 [&>p:last-child]:mb-0">
    ${innerHtml}
  </div>
</aside>`;
}

function renderMarkdownWithComponents(source) {
  const { marked: inlineMarked } = createMarkdownRenderer(false);
  const { marked: pageMarked, headings } = createMarkdownRenderer(true);
  const blocks = [];

  const stash = (html) => {
    const token = `@@DOC_BLOCK_${blocks.length}@@`;
    blocks.push(html);
    return token;
  };

  const transformComponents = (input) => {
    let out = input;

    // 1. Self-closing <LinkCard ... />
    out = out.replace(/<LinkCard\s+([^>]*?)\/>/g, (_, attrStr) => {
      const { title = "", href = "#", description = "" } = parseAttrs(attrStr);
      const html = `<a href="${escapeHtml(href)}" class="group block rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] p-4 no-underline transition-colors hover:border-[var(--ds-border-strong)] hover:bg-[var(--ds-surface-hover)]">
  <p class="m-0 flex items-center justify-between text-[14px] font-semibold text-[var(--ds-ink)]">
    <span>${escapeHtml(title)}</span>
    <span class="text-[var(--ds-ink-faint)] transition-transform group-hover:translate-x-0.5 group-hover:text-[var(--ds-ink)]" aria-hidden="true">→</span>
  </p>
  ${description ? `<p class="m-0 mt-1 text-[13px] leading-[1.55] text-[var(--ds-ink-muted)]">${escapeHtml(description)}</p>` : ""}
</a>`;
      return stash(html);
    });

    // 2. <Card title="...">...</Card>
    out = out.replace(/<Card\s+([^>]*?)>([\s\S]*?)<\/Card>/g, (_, attrStr, inner) => {
      const { title = "" } = parseAttrs(attrStr);
      const innerHtml = inlineMarked.parse(dedent(inner));
      const html = `<section class="rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] p-4">
  <h3 class="m-0 text-[15px] font-semibold tracking-[-0.015em] text-[var(--ds-ink)]">${escapeHtml(title)}</h3>
  <div class="mt-1.5 text-[13.5px] leading-[1.55] text-[var(--ds-ink-muted)] [&>p]:m-0">
    ${innerHtml}
  </div>
</section>`;
      return stash(html);
    });

    // 3. <CardGrid>...</CardGrid>
    out = out.replace(/<CardGrid>([\s\S]*?)<\/CardGrid>/g, (_, inner) => {
      const html = `<div class="not-prose grid gap-3 sm:grid-cols-2">${inner.trim()}</div>`;
      return stash(html);
    });

    // 4. <Aside type="...">...</Aside>
    out = out.replace(/<Aside(?:\s+([^>]*?))?>([\s\S]*?)<\/Aside>/g, (_, attrStr = "", inner) => {
      const { type = "note" } = parseAttrs(attrStr);
      const innerHtml = inlineMarked.parse(dedent(inner));
      return stash(renderAside(type, innerHtml));
    });

    // 5. <TabItem label="...">...</TabItem>
    out = out.replace(/<TabItem\s+([^>]*?)>([\s\S]*?)<\/TabItem>/g, (_, attrStr, inner) => {
      const { label = "" } = parseAttrs(attrStr);
      const innerHtml = inlineMarked.parse(dedent(inner));
      const html = `<section class="mb-4 last:mb-0">
  <p class="m-0 mb-2 inline-block rounded border border-[var(--ds-border)] bg-[var(--ds-canvas-subtle)] px-2 py-0.5 font-mono text-[11px] font-medium text-[var(--ds-ink-muted)]">${escapeHtml(label)}</p>
  <div class="[&_.ds-code-wrap]:my-0">${innerHtml}</div>
</section>`;
      return stash(html);
    });

    // 6. <Tabs>...</Tabs>
    out = out.replace(/<Tabs>([\s\S]*?)<\/Tabs>/g, (_, inner) => {
      const html = `<div class="my-5 rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] p-4">${inner.trim()}</div>`;
      return stash(html);
    });

    // 7. <Steps>...</Steps>
    out = out.replace(/<Steps>([\s\S]*?)<\/Steps>/g, (_, inner) => {
      const innerHtml = pageMarked.parse(dedent(inner));
      const html = `<div class="my-5 rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] px-5 py-4 [&>ol]:m-0 [&>ol]:space-y-4">${innerHtml}</div>`;
      return stash(html);
    });

    return out;
  };

  const preprocessed = transformComponents(source);
  let html = pageMarked.parse(preprocessed);

  // Restore stashed HTML blocks (loop for nested blocks like CardGrid -> Card or Steps -> Tabs -> TabItem)
  let prev;
  do {
    prev = html;
    html = html.replace(/<p>\s*(@@DOC_BLOCK_(\d+)@@)\s*<\/p>|@@DOC_BLOCK_(\d+)@@/g, (_, __, idxA, idxB) => {
      const idx = Number(idxA ?? idxB);
      return blocks[idx] ?? "";
    });
  } while (html !== prev);

  return { html, headings };
}

export function loadAllDocs(contentDir) {
  const files = fs.readdirSync(contentDir).filter((f) => f.endsWith(".md"));
  const entries = files.map((file) => {
    const id = path.basename(file, ".md");
    const raw = fs.readFileSync(path.join(contentDir, file), "utf-8");
    const { data, body } = parseFrontmatter(raw);
    const { html, headings } = renderMarkdownWithComponents(body);
    return {
      id,
      slug: id === "index" ? "" : id,
      href: id === "index" ? "/docs" : `/docs/${id}`,
      data,
      html,
      headings
    };
  });

  const rank = new Map(ORDER.map((slug, idx) => [slug, idx]));
  entries.sort((a, b) => {
    const ra = rank.get(a.id) ?? 999;
    const rb = rank.get(b.id) ?? 999;
    if (ra === rb) return String(a.data.title || a.id).localeCompare(String(b.data.title || b.id));
    return ra - rb;
  });

  return entries;
}

export function renderDocPage(entry, allDocs, assets) {
  const { title = entry.id, description, hero } = entry.data;
  const active = entry.href;
  const tocHeadings = entry.headings.filter((h) => h.depth >= 2 && h.depth <= 3);

  const currentIndex = allDocs.findIndex((d) => d.id === entry.id);
  const prevItem = currentIndex > 0 ? allDocs[currentIndex - 1] : undefined;
  const nextItem = currentIndex >= 0 && currentIndex < allDocs.length - 1 ? allDocs[currentIndex + 1] : undefined;

  const searchItems = allDocs.map((item) => ({
    title: item.data.title,
    description: item.data.description,
    slug: item.id,
    href: item.href
  }));

  const navLinksHtml = (isMobile = false) =>
    allDocs
      .map((item) => {
        const isActive = item.href === active;
        const base = isMobile
          ? "block rounded-md px-2.5 py-1.5 text-[13px]"
          : "block rounded-md px-2.5 py-1.5 text-[13px] leading-snug transition-colors";
        const state = isActive
          ? "bg-[var(--brand-accent-soft)] font-medium text-[var(--ds-ink)]"
          : "text-[var(--ds-ink-muted)] hover:bg-[var(--ds-surface-hover)] hover:text-[var(--ds-ink)]";
        return `<a href="${escapeHtml(item.href)}"${isActive ? ' aria-current="page"' : ""} class="${base} ${state}">${escapeHtml(item.data.title)}</a>`;
      })
      .join("\n");

  const heroOrHeaderHtml = hero
    ? `<section class="mb-8 flex flex-col items-start gap-6 rounded-xl border border-[var(--ds-border)] bg-[var(--ds-surface)] p-6 sm:flex-row sm:items-center">
        <img src="/logo.png" alt="Whisper API" class="h-24 w-24 shrink-0 rounded-xl border border-[var(--ds-border)] bg-white object-contain p-1.5 sm:h-28 sm:w-28" />
        <div class="min-w-0 flex-1">
          <h1 class="m-0 text-[28px] font-semibold leading-[1.18] tracking-[-0.032em] text-[var(--ds-ink)]">${escapeHtml(title)}</h1>
          ${hero.tagline ? `<p class="mt-2 text-[15px] leading-[1.6] text-[var(--ds-ink-muted)]">${escapeHtml(hero.tagline)}</p>` : ""}
          ${
            hero.actions && hero.actions.length > 0
              ? `<div class="mt-4 flex flex-wrap items-center gap-2.5">
                  ${hero.actions
                    .map((action) => {
                      const cls =
                        action.variant === "primary"
                          ? "inline-flex h-9 items-center gap-1.5 rounded-md bg-[var(--brand-accent)] px-4 text-[13px] font-medium text-[var(--brand-accent-ink)] transition-colors hover:bg-[var(--brand-accent-hover)]"
                          : "inline-flex h-9 items-center gap-1.5 rounded-md border border-[var(--ds-border)] bg-[var(--ds-surface)] px-4 text-[13px] font-medium text-[var(--ds-ink)] transition-colors hover:bg-[var(--ds-surface-hover)]";
                      return `<a href="${escapeHtml(action.link)}" class="${cls}">${escapeHtml(action.text)}${action.variant === "primary" ? ' <span aria-hidden="true">→</span>' : ""}</a>`;
                    })
                    .join("\n")}
                </div>`
              : ""
          }
        </div>
      </section>`
    : `<header class="mb-8 rounded-xl border border-[var(--ds-border)] bg-[var(--ds-surface)] p-6">
        <h1 class="m-0 text-[28px] font-semibold leading-[1.18] tracking-[-0.032em] text-[var(--ds-ink)]">${escapeHtml(title)}</h1>
        ${description ? `<p class="mt-2 mb-0 text-[15px] leading-[1.6] text-[var(--ds-ink-muted)]">${escapeHtml(description)}</p>` : ""}
      </header>`;

  const paginationHtml =
    prevItem || nextItem
      ? `<nav aria-label="Pagination" class="mt-12 grid gap-3 border-t border-[var(--ds-divider)] pt-6 sm:grid-cols-2">
          ${
            prevItem
              ? `<a href="${escapeHtml(prevItem.href)}" class="group rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] px-4 py-3 transition-colors hover:border-[var(--ds-border-strong)] hover:bg-[var(--ds-surface-hover)]">
                  <p class="m-0 text-[11px] font-medium text-[var(--ds-ink-faint)]">← Previous</p>
                  <p class="mt-1 mb-0 text-[14px] font-medium text-[var(--ds-ink)]">${escapeHtml(prevItem.data.title)}</p>
                </a>`
              : "<div></div>"
          }
          ${
            nextItem
              ? `<a href="${escapeHtml(nextItem.href)}" class="group rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] px-4 py-3 text-right transition-colors hover:border-[var(--ds-border-strong)] hover:bg-[var(--ds-surface-hover)]">
                  <p class="m-0 text-[11px] font-medium text-[var(--ds-ink-faint)]">Next →</p>
                  <p class="mt-1 mb-0 text-[14px] font-medium text-[var(--ds-ink)]">${escapeHtml(nextItem.data.title)}</p>
                </a>`
              : ""
          }
        </nav>`
      : "";

  const tocHtml =
    tocHeadings.length > 0
      ? `<div class="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto border-l border-[var(--ds-border)] pl-4">
          <p class="mb-2.5 text-[12px] font-semibold text-[var(--ds-ink)]">On this page</p>
          <nav class="space-y-0.5" id="toc-nav" aria-label="On this page">
            ${tocHeadings
              .map(
                (h) =>
                  `<a href="#${escapeHtml(h.slug)}" data-heading="${escapeHtml(h.slug)}" class="ds-toc-link ${h.depth === 3 ? "pl-5" : ""}">${escapeHtml(h.text)}</a>`
              )
              .join("\n")}
          </nav>
        </div>`
      : "";

  const cssTags = (assets.css || [])
    .map((href) => `<link rel="stylesheet" href="${escapeHtml(href)}" />`)
    .join("\n    ");
  const jsTags = (assets.js || [])
    .map((src) => `<script type="module" src="${escapeHtml(src)}"></script>`)
    .join("\n    ");

  return `<!doctype html>
<html lang="en" data-theme="light">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script>
      (() => {
        const stored = localStorage.getItem("whisper-docs-theme");
        const theme = stored === "dark" || stored === "light"
          ? stored
          : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", theme);
      })();
    </script>
    <title>${escapeHtml(title)} | Whisper API Docs</title>
    ${description ? `<meta name="description" content="${escapeHtml(description)}" />` : ""}
    <meta property="og:title" content="${escapeHtml(title)} | Whisper API Docs" />
    ${description ? `<meta property="og:description" content="${escapeHtml(description)}" />` : ""}
    <meta property="og:image" content="/logo.png" />
    <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
    <link rel="shortcut icon" href="/favicon.svg" />
    <link rel="apple-touch-icon" href="/logo.png" />
    ${cssTags}
  </head>

  <body class="min-h-screen bg-[var(--ds-canvas)] text-[var(--ds-ink)]">
    <a
      href="#main-content"
      class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-[var(--brand-accent)] focus:px-3 focus:py-1.5 focus:text-xs focus:font-medium focus:text-[var(--brand-accent-ink)]"
    >
      Skip to content
    </a>

    <header class="sticky top-0 z-40 h-14 border-b border-[var(--ds-border)] bg-[var(--ds-topbar-bg)] backdrop-blur-md">
      <div class="mx-auto flex h-full w-full max-w-[1320px] items-center justify-between gap-4 px-4 sm:px-6">
        <a href="/docs" class="flex items-center gap-2.5 transition-opacity hover:opacity-85">
          <svg viewBox="0 0 40 40" class="h-7 w-7 shrink-0" aria-hidden="true">
            <rect x="4" y="15" width="4" height="10" rx="2" fill="#F97316" />
            <rect x="11" y="10" width="4" height="20" rx="2" fill="#F97316" />
            <rect x="18" y="4" width="4" height="32" rx="2" fill="#F97316" />
            <rect x="25" y="10" width="4" height="20" rx="2" fill="#F97316" />
            <rect x="32" y="15" width="4" height="10" rx="2" fill="#F97316" />
          </svg>
          <span class="flex items-center gap-1.5">
            <span class="text-[17px] font-bold tracking-[-0.03em] text-[var(--ds-ink)]">whisper</span>
            <span class="rounded bg-[#F97316] px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-wider text-white">API</span>
          </span>
        </a>

        <div class="flex items-center gap-2">
          <div class="relative hidden w-[260px] md:block">
            <input
              id="docs-search-input"
              type="search"
              placeholder="Search docs..."
              aria-label="Search documentation"
              autocomplete="off"
              data-search-items="${escapeHtml(JSON.stringify(searchItems))}"
              class="h-8 w-full rounded-md border border-[var(--ds-border)] bg-[var(--ds-surface)] pl-3 pr-12 text-[13px] text-[var(--ds-ink)] placeholder-[var(--ds-ink-faint)] transition-colors focus:border-[var(--ds-border-strong)] focus:outline-none"
            />
            <kbd class="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-[var(--ds-border)] bg-[var(--ds-canvas-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--ds-ink-faint)]">
              ⌘K
            </kbd>
            <div
              id="docs-search-results"
              class="hidden absolute right-0 top-[calc(100%+6px)] z-50 max-h-80 w-[340px] overflow-y-auto rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] p-1 shadow-[var(--ds-shadow-overlay)]"
            ></div>
          </div>

          <span class="hidden h-8 items-center rounded-md border border-[var(--ds-border)] bg-[var(--ds-surface)] px-2 font-mono text-[11px] font-medium text-[var(--ds-ink-muted)] sm:inline-flex">
            v2.1.0
          </span>

          <button
            id="theme-toggle-btn"
            type="button"
            aria-label="Toggle dark mode"
            class="inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--ds-border)] bg-[var(--ds-surface)] text-[var(--ds-ink-muted)] transition-colors hover:bg-[var(--ds-surface-hover)] hover:text-[var(--ds-ink)]"
          >
            <svg id="theme-icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="hidden h-4 w-4">
              <circle cx="12" cy="12" r="4"></circle>
              <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32 1.41-1.41"></path>
            </svg>
            <svg id="theme-icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="h-4 w-4">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          </button>

          <a
            href="https://github.com/innovatorved/whisper.api"
            aria-label="GitHub repository"
            target="_blank"
            rel="noreferrer"
            class="inline-flex h-8 w-8 items-center justify-center rounded-md border border-[var(--ds-border)] bg-[var(--ds-surface)] text-[var(--ds-ink-muted)] transition-colors hover:bg-[var(--ds-surface-hover)] hover:text-[var(--ds-ink)]"
          >
            <svg viewBox="0 0 24 24" class="h-4 w-4 fill-current">
              <path d="M12 2C6.48 2 2 6.58 2 12.23c0 4.52 2.87 8.35 6.84 9.7.5.1.66-.22.66-.49 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.2-3.37-1.2-.45-1.18-1.11-1.5-1.11-1.5-.91-.64.07-.63.07-.63 1 .08 1.53 1.06 1.53 1.06.9 1.57 2.36 1.12 2.94.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05A9.27 9.27 0 0 1 12 6.9c.85 0 1.71.12 2.51.35 1.9-1.33 2.74-1.05 2.74-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.95-2.34 4.82-4.57 5.07.36.32.68.95.68 1.92 0 1.39-.01 2.5-.01 2.84 0 .27.17.59.67.49A10.28 10.28 0 0 0 22 12.23C22 6.58 17.52 2 12 2Z" />
            </svg>
          </a>
        </div>
      </div>
    </header>

    <div class="mx-auto w-full max-w-[1320px] px-4 py-8 sm:px-6">
      <div class="grid grid-cols-1 items-start gap-10 lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,760px)_224px] xl:justify-between">
        <aside class="hidden lg:block">
          <nav aria-label="Documentation navigation" class="sticky top-20 space-y-0.5">
            <p class="mb-2.5 px-2.5 text-[11px] font-medium text-[var(--ds-ink-faint)]">Documentation</p>
            ${navLinksHtml(false)}
          </nav>
        </aside>

        <main id="main-content" class="min-w-0 w-full max-w-[760px]">
          <details class="mb-6 rounded-lg border border-[var(--ds-border)] bg-[var(--ds-surface)] p-3 lg:hidden">
            <summary class="flex cursor-pointer items-center gap-2 text-[13px] font-medium text-[var(--ds-ink)]">
              <svg class="h-4 w-4 text-[var(--ds-ink-muted)]" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
                  clip-rule="evenodd"
                ></path>
              </svg>
              Navigation
            </summary>
            <nav class="mt-2.5 space-y-0.5 border-t border-[var(--ds-divider)] pt-2.5">
              ${navLinksHtml(true)}
            </nav>
          </details>

          ${heroOrHeaderHtml}

          <article class="ds-prose">
            ${entry.html}
          </article>

          ${paginationHtml}

          <footer class="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-[var(--ds-divider)] pt-6 text-[12px] text-[var(--ds-ink-faint)]">
            <span>Whisper API · MIT License</span>
            <div class="flex items-center gap-4">
              <a href="https://github.com/innovatorved/whisper.api" target="_blank" rel="noreferrer" class="hover:text-[var(--ds-ink)]">
                GitHub
              </a>
              <a href="https://github.com/innovatorved/whisper.cpp" target="_blank" rel="noreferrer" class="hover:text-[var(--ds-ink)]">
                whisper.cpp Fork
              </a>
            </div>
          </footer>
        </main>

        <aside class="hidden xl:block">
          ${tocHtml}
        </aside>
      </div>
    </div>

    ${jsTags}
  </body>
</html>
`;
}

export function renderRootRedirectHtml() {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="refresh" content="0; url=/docs" />
    <link rel="canonical" href="/docs" />
    <title>Whisper API Docs</title>
  </head>
  <body>
    <p>Redirecting to <a href="/docs">/docs</a>…</p>
  </body>
</html>
`;
}

export function renderSitemapXml(allDocs, siteUrl) {
  const base = siteUrl.replace(/\/+$/, "");
  const urls = allDocs
    .map((doc) => `  <url><loc>${escapeHtml(`${base}${doc.href}`)}</loc></url>`)
    .join("\n");
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`;
}
