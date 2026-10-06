/** Validation and de-duplication helpers for (client-side encrypted) file and folder names. */

export function validateItemName(raw: string, siblings: { id?: string; name: string }[], excludeId?: string): string | null {
  const name = raw.trim();
  if (!name) return "Please enter a name.";
  if (name.length > 255) return "Names can be at most 255 characters.";
  if (name === "." || name === "..") return "That name isn't allowed.";
  if (/[\\/]/.test(name)) return "Names can't contain / or \\.";
  const lower = name.toLowerCase();
  if (siblings.some((n) => n.id !== excludeId && (n.name || "").toLowerCase() === lower)) {
    return `An item named "${name}" already exists in this folder.`;
  }
  return null;
}

/** "report.pdf" -> "report (1).pdf" if taken (case-insensitive), and so on. */
export function uniqueName(name: string, taken: Iterable<string>): string {
  const lowerTaken = new Set(Array.from(taken, (t) => (t || "").toLowerCase()));
  if (!lowerTaken.has(name.toLowerCase())) return name;
  const dot = name.lastIndexOf(".");
  const hasExt = dot > 0 && dot < name.length - 1;
  const base = hasExt ? name.slice(0, dot) : name;
  const ext = hasExt ? name.slice(dot) : "";
  for (let i = 1; i < 10000; i++) {
    const candidate = `${base} (${i})${ext}`;
    if (!lowerTaken.has(candidate.toLowerCase())) return candidate;
  }
  return `${base} (${Date.now()})${ext}`;
}
