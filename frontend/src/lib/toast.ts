import { toast as sonner } from "vue-sonner";

interface ToastAction {
  label: string;
  onClick: () => void;
}
interface ToastOptions {
  description?: string;
  action?: ToastAction;
  duration?: number;
  id?: string | number;
}

function opts(o: ToastOptions = {}) {
  return {
    id: o.id,
    description: o.description,
    duration: o.duration,
    action: o.action ? { label: o.action.label, onClick: () => o.action!.onClick() } : undefined,
  };
}

/** App-wide notifications. Messages must already be human copy (see normalizeApiError). */
export const toast = {
  success: (message: string, o?: ToastOptions) => sonner.success(message, opts(o)),
  info: (message: string, o?: ToastOptions) => sonner.info(message, opts(o)),
  error: (message: string, o?: ToastOptions & { retry?: () => void }) =>
    sonner.error(message, {
      ...opts(o),
      duration: o?.duration ?? 7000,
      action: o?.retry ? { label: "Retry", onClick: () => o.retry!() } : opts(o).action,
    }),
  loading: (message: string, o?: ToastOptions) => sonner.loading(message, opts(o)),
  /** Success toast with an Undo action, for reversible operations. */
  undoable: (message: string, onUndo: () => void, o?: ToastOptions) =>
    sonner.success(message, { ...opts(o), duration: 6000, action: { label: "Undo", onClick: onUndo } }),
  dismiss: (id?: string | number) => sonner.dismiss(id),
};
