import {
  Folder,
  FileText,
  FileSpreadsheet,
  FileVideo,
  FileAudio,
  FileImage,
  FileCode,
  FileArchive,
  File,
  Presentation,
} from "lucide-vue-next";
import type { Component } from "vue";

export type FileKind = "folder" | "image" | "video" | "audio" | "pdf" | "doc" | "sheet" | "slides" | "archive" | "code" | "other";

interface KindInfo {
  label: string;
  icon: Component;
  tint: string; // icon colour + background
}

const KINDS: Record<FileKind, KindInfo> = {
  folder: { label: "Folder", icon: Folder, tint: "text-amber-500 bg-amber-500/10" },
  image: { label: "Image", icon: FileImage, tint: "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400" },
  video: { label: "Video", icon: FileVideo, tint: "text-violet-600 bg-violet-500/10 dark:text-violet-400" },
  audio: { label: "Audio", icon: FileAudio, tint: "text-pink-600 bg-pink-500/10 dark:text-pink-400" },
  pdf: { label: "PDF", icon: FileText, tint: "text-rose-600 bg-rose-500/10 dark:text-rose-400" },
  doc: { label: "Document", icon: FileText, tint: "text-primary bg-primary/10" },
  sheet: { label: "Spreadsheet", icon: FileSpreadsheet, tint: "text-green-700 bg-green-500/10 dark:text-green-400" },
  slides: { label: "Presentation", icon: Presentation, tint: "text-orange-600 bg-orange-500/10 dark:text-orange-400" },
  archive: { label: "Archive", icon: FileArchive, tint: "text-fg-muted bg-canvas-subtle" },
  code: { label: "Code", icon: FileCode, tint: "text-sky-600 bg-sky-500/10 dark:text-sky-400" },
  other: { label: "File", icon: File, tint: "text-fg-subtle bg-canvas-subtle" },
};

const EXTENSIONS: Record<string, FileKind> = {};
const register = (kind: FileKind, exts: string[]) => exts.forEach((e) => (EXTENSIONS[e] = kind));
register("image", ["png", "jpg", "jpeg", "webp", "gif", "svg", "bmp", "avif", "heic", "heif", "tif", "tiff", "raw", "arw", "cr2", "cr3", "nef", "dng", "orf", "rw2"]);
register("video", ["mp4", "mov", "mkv", "webm", "avi", "m4v", "mts", "m2ts", "3gp", "wmv"]);
register("audio", ["mp3", "wav", "ogg", "m4a", "flac", "aac", "opus", "aiff"]);
register("pdf", ["pdf"]);
register("doc", ["doc", "docx", "odt", "rtf", "txt", "md", "pages"]);
register("sheet", ["xls", "xlsx", "csv", "tsv", "ods", "numbers"]);
register("slides", ["ppt", "pptx", "odp", "key"]);
register("archive", ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"]);
register("code", ["js", "ts", "py", "html", "css", "json", "vue", "rs", "go", "java", "c", "cpp", "h", "sql", "sh", "yaml", "yml", "xml"]);

export function kindOf(node: { type: string; name: string }): FileKind {
  if (node.type === "folder") return "folder";
  const ext = node.name.includes(".") ? node.name.split(".").pop()!.toLowerCase() : "";
  return EXTENSIONS[ext] || "other";
}

export function kindInfo(kind: FileKind): KindInfo {
  return KINDS[kind];
}

/** Just the icon colour from a kind's tint (no background). */
export function kindIconColor(kind: FileKind): string {
  return KINDS[kind].tint
    .split(" ")
    .filter((c) => c.startsWith("text-") || c.startsWith("dark:text-"))
    .join(" ");
}

export type FilterKey = "all" | "folders" | "documents" | "images" | "videos" | "archives";

export const FILTERS: { key: FilterKey; label: string; kinds: FileKind[] }[] = [
  { key: "all", label: "All types", kinds: [] },
  { key: "folders", label: "Folders", kinds: ["folder"] },
  { key: "documents", label: "Documents", kinds: ["pdf", "doc", "sheet", "slides"] },
  { key: "images", label: "Images", kinds: ["image"] },
  { key: "videos", label: "Videos", kinds: ["video"] },
  { key: "archives", label: "Archives", kinds: ["archive"] },
];
