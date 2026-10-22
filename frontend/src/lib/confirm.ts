import { reactive } from "vue";

export interface ConfirmOptions {
  title: string;
  body?: string;
  /** Names the action, e.g. "Delete 3 files" — never "OK". */
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  /** Requires the user to type this text before confirming (permanent deletes). */
  typeToConfirm?: string;
  /** Runs inside the dialog with a loading state; errors are shown in the dialog. */
  action?: () => Promise<unknown>;
}

interface ConfirmState {
  open: boolean;
  options: ConfirmOptions | null;
  resolve: ((ok: boolean) => void) | null;
}

export const confirmState = reactive<ConfirmState>({ open: false, options: null, resolve: null });

/** In-app replacement for window.confirm(). Resolves true when confirmed (and the action succeeded). */
export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  confirmState.resolve?.(false);
  return new Promise((resolve) => {
    confirmState.options = options;
    confirmState.resolve = resolve;
    confirmState.open = true;
  });
}

export function settleConfirm(ok: boolean) {
  confirmState.open = false;
  const resolve = confirmState.resolve;
  confirmState.resolve = null;
  resolve?.(ok);
}
