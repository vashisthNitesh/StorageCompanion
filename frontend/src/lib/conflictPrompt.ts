import { reactive } from "vue";

export type ConflictChoice = "replace" | "keep-both" | "skip";

interface ConflictState {
  open: boolean;
  fileName: string;
  folderName: string;
  remaining: number;
  resolve: ((r: { choice: ConflictChoice; applyToAll: boolean } | null) => void) | null;
}

export const conflictState = reactive<ConflictState>({ open: false, fileName: "", folderName: "", remaining: 0, resolve: null });

/** Asks what to do with a file whose name already exists. Resolves null if the whole upload is cancelled. */
export function askConflict(fileName: string, folderName: string, remaining: number) {
  return new Promise<{ choice: ConflictChoice; applyToAll: boolean } | null>((resolve) => {
    Object.assign(conflictState, { open: true, fileName, folderName, remaining, resolve });
  });
}

export function settleConflict(result: { choice: ConflictChoice; applyToAll: boolean } | null) {
  conflictState.open = false;
  const resolve = conflictState.resolve;
  conflictState.resolve = null;
  resolve?.(result);
}
