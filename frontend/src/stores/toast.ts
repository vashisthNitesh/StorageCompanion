// Compatibility shim: older call sites use useToastStore(); it forwards to the sonner-based service.
import { toast } from "../lib/toast";

export function useToastStore() {
  return {
    success: (m: string) => toast.success(m),
    error: (m: string) => toast.error(m),
    info: (m: string) => toast.info(m),
  };
}
