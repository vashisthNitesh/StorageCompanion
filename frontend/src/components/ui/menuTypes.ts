import type { Component } from "vue";

export type MenuEntry =
  | {
      label: string;
      icon?: Component;
      shortcut?: string;
      danger?: boolean;
      disabled?: boolean;
      onSelect: () => void;
    }
  | { separator: true }
  | { heading: string };

export const menuContentClass =
  "z-[60] min-w-[220px] rounded-lg border border-line bg-surface-raised p-1 shadow-md animate-pop-in focus:outline-none";
export const menuItemClass =
  "flex h-8 cursor-default select-none items-center gap-2.5 rounded px-2.5 text-base text-fg outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[highlighted]:bg-canvas-subtle";
export const menuDangerClass = "text-danger data-[highlighted]:bg-danger-soft";
