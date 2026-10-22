import { nextTick, reactive, ref, watch } from "vue";
import { COPY, normalizeApiError, type NormalizedError } from "../lib/errors";

export type Rule<T> = (value: any, values: T) => string | null | undefined | false;

export const rules = {
  required:
    (message = "This field is required.") =>
    (v: any) =>
      (typeof v === "string" ? !v.trim() : v == null || v === false) ? message : null,
  email:
    (message = "Enter a valid email address, like name@example.com.") =>
    (v: string) =>
      v && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) ? message : null,
  minLength: (n: number, message?: string) => (v: string) =>
    v && v.length < n ? message ?? `Use at least ${n} characters.` : null,
  maxLength: (n: number, message?: string) => (v: string) =>
    v && v.length > n ? message ?? `Use ${n} characters or fewer.` : null,
  pattern: (re: RegExp, message: string) => (v: string) => (v && !re.test(v) ? message : null),
};

/**
 * Form state with our own validation (forms use `novalidate`): errors appear on blur,
 * then update live; server field errors are mapped onto the matching fields.
 */
export function useForm<T extends Record<string, any>>(
  initial: T,
  fieldRules: Partial<Record<keyof T, Rule<T>[]>> = {},
  options: { serverFieldMap?: Record<string, keyof T> } = {}
) {
  const values = reactive({ ...initial }) as T;
  // Keyed by field name; typed loosely because Vue's reactive() can't index generic keys.
  const errors: Record<string, string | undefined> = reactive({});
  const live: Record<string, boolean> = reactive({});
  const formError = ref("");
  const submitting = ref(false);
  const formEl = ref<HTMLFormElement | null>(null);

  function validateField(name: keyof T): boolean {
    for (const rule of fieldRules[name] ?? []) {
      const msg = rule(values[name], values);
      if (msg) {
        errors[name as string] = msg;
        return false;
      }
    }
    delete errors[name as string];
    return true;
  }

  function blur(name: keyof T) {
    if (values[name] === initial[name] && !live[name as string]) return;
    live[name as string] = true;
    validateField(name);
  }

  // After a field has been validated once, keep its message in sync while typing.
  watch(
    () => ({ ...values }),
    (next, prev) => {
      formError.value = "";
      for (const key of Object.keys(next) as (keyof T)[]) {
        if (next[key] !== prev?.[key]) {
          if (live[key as string]) validateField(key);
          // Fields whose rules depend on others (e.g. "confirm password").
          for (const other of Object.keys(fieldRules) as (keyof T)[]) if (other !== key && live[other as string]) validateField(other);
        }
      }
    }
  );

  async function focusFirstInvalid() {
    await nextTick();
    formEl.value?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
  }

  function validateAll(): boolean {
    let ok = true;
    for (const name of Object.keys(fieldRules) as (keyof T)[]) {
      live[name as string] = true;
      if (!validateField(name)) ok = false;
    }
    return ok;
  }

  function applyServerError(err: unknown): NormalizedError {
    const n = normalizeApiError(err);
    let mapped = false;
    for (const [serverField, message] of Object.entries(n.fieldErrors)) {
      const field = (options.serverFieldMap?.[serverField] ?? serverField) as keyof T;
      if (field in values) {
        errors[field as string] = message;
        live[field as string] = true;
        mapped = true;
      }
    }
    formError.value = mapped && n.message === COPY.validation ? "" : n.message;
    if (mapped) void focusFirstInvalid();
    return n;
  }

  /** Validates, then runs `fn`. Errors from `fn` become field / form errors. */
  async function submit(fn: (v: T) => Promise<unknown>): Promise<boolean> {
    formError.value = "";
    if (!validateAll()) {
      void focusFirstInvalid();
      return false;
    }
    submitting.value = true;
    try {
      await fn(values);
      return true;
    } catch (err) {
      applyServerError(err);
      return false;
    } finally {
      submitting.value = false;
    }
  }

  function reset(next: Partial<T> = {}) {
    Object.assign(values, initial, next);
    for (const k of Object.keys(errors)) delete errors[k];
    for (const k of Object.keys(live)) delete live[k];
    formError.value = "";
  }

  return { values, errors, formError, submitting, formEl, blur, validateAll, validateField, submit, reset, applyServerError };
}
