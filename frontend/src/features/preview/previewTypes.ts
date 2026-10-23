// What the in-app viewer can show for each file type, decided by extension (names
// are encrypted, so there's no server-side MIME type to go on).

export type PreviewKind = "image" | "video" | "audio" | "pdf" | "docx" | "sheet" | "text";

const MIME: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
  gif: "image/gif",
  svg: "image/svg+xml",
  bmp: "image/bmp",
  avif: "image/avif",
  ico: "image/x-icon",
  heic: "image/heic",
  heif: "image/heif",
  tif: "image/tiff",
  tiff: "image/tiff",
  mp4: "video/mp4",
  m4v: "video/mp4",
  mov: "video/quicktime",
  webm: "video/webm",
  mkv: "video/x-matroska",
  ogv: "video/ogg",
  "3gp": "video/3gpp",
  mp3: "audio/mpeg",
  wav: "audio/wav",
  ogg: "audio/ogg",
  oga: "audio/ogg",
  opus: "audio/ogg",
  m4a: "audio/mp4",
  aac: "audio/aac",
  flac: "audio/flac",
  weba: "audio/webm",
  pdf: "application/pdf",
};

const KIND: Record<string, PreviewKind> = {};
const register = (kind: PreviewKind, exts: string[]) => exts.forEach((e) => (KIND[e] = kind));
register("image", ["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp", "avif", "ico", "heic", "heif", "tif", "tiff"]);
register("video", ["mp4", "m4v", "mov", "webm", "mkv", "ogv", "3gp"]);
register("audio", ["mp3", "wav", "ogg", "oga", "opus", "m4a", "aac", "flac", "weba"]);
register("pdf", ["pdf"]);
register("docx", ["docx", "docm", "dotx"]);
register("sheet", ["xlsx", "xlsm", "xlsb", "xls", "ods", "csv", "tsv"]);
register("text", [
  "txt", "md", "markdown", "log", "json", "jsonl", "xml", "yaml", "yml", "toml", "ini", "cfg", "conf", "env", "srt", "vtt",
  "js", "mjs", "cjs", "ts", "tsx", "jsx", "vue", "svelte", "py", "rb", "php", "go", "rs", "java", "kt", "swift", "c", "h",
  "cpp", "hpp", "cs", "sql", "sh", "bash", "zsh", "ps1", "bat", "html", "htm", "css", "scss", "less", "gradle", "dockerfile",
]);

export const extensionOf = (name: string) => (name.includes(".") ? name.split(".").pop()!.toLowerCase() : "");

export function previewKindOf(node: { type: string; name: string }): PreviewKind | null {
  if (node.type !== "file") return null;
  return KIND[extensionOf(node.name)] ?? null;
}

export function mimeOf(name: string): string {
  return MIME[extensionOf(name)] ?? "application/octet-stream";
}

/** Formats a browser can't decode anyway; the viewer goes straight to its fallback. */
export function likelyUnsupported(kind: PreviewKind, name: string): boolean {
  const ext = extensionOf(name);
  const safari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
  if (kind === "image" && ["heic", "heif", "tif", "tiff"].includes(ext)) return !safari;
  return false;
}
