import { useFilesStore } from "../../stores/files";

/** Returns human copy for an invalid file/folder name, or null when it's fine. */
export function validateName(
  raw: string,
  opts: { parentId: string | null; exceptId?: string; type: "file" | "folder" }
): string | null {
  const name = raw.trim();
  if (!name) return opts.type === "folder" ? "Enter a folder name." : "Enter a name.";
  if (/[\\/]/.test(name)) return "Names can't contain / or \\.";
  if (name === "." || name === "..") return "Choose a different name.";
  if (name.length > 255) return "Use 255 characters or fewer.";
  if (useFilesStore().nameExists(name, opts.parentId, opts.exceptId)) {
    return `A ${opts.type === "folder" ? "folder" : "file"} with this name already exists here.`;
  }
  return null;
}
