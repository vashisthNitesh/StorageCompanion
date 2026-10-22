import { cn } from "./cn";

export function inputClasses(opts: { invalid?: boolean; size?: "sm" | "md" | "lg"; extra?: string; block?: boolean }) {
  return cn(
    opts.block === false ? "inline-flex" : "block w-full",
    "rounded border bg-surface text-fg placeholder:text-fg-subtle shadow-xs",
    "transition-[border-color,box-shadow] duration-fast ease-out",
    "focus:outline-none focus-visible:outline-none focus:ring-4",
    "disabled:cursor-not-allowed disabled:bg-canvas-subtle disabled:text-fg-subtle",
    opts.invalid
      ? "border-danger focus:border-danger focus:ring-danger/15"
      : "border-line-strong hover:border-fg-subtle/60 focus:border-primary focus:ring-primary/15",
    opts.size === "sm" ? "h-8 px-2.5 text-sm" : opts.size === "lg" ? "h-11 px-3.5 text-md" : "h-9 px-3 text-base",
    opts.extra
  );
}
