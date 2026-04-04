export type NavItem = {
  slug: string;
  title: string;
};

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

export function sortDocs<T extends { id: string; data: { title: string } }>(entries: T[]) {
  const rank = new Map(ORDER.map((slug, idx) => [slug, idx]));
  return [...entries].sort((a, b) => {
    const ra = rank.get(a.id) ?? 999;
    const rb = rank.get(b.id) ?? 999;
    if (ra === rb) return a.data.title.localeCompare(b.data.title);
    return ra - rb;
  });
}

export function toNavItems<T extends { id: string; data: { title: string } }>(entries: T[]): NavItem[] {
  return entries.map((entry) => ({
    slug: entry.id === "index" ? "" : entry.id,
    title: entry.data.title
  }));
}