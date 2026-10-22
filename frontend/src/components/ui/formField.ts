import { inject, provide, type ComputedRef, type InjectionKey } from "vue";

export interface FormFieldContext {
  id: string;
  describedBy: ComputedRef<string | undefined>;
  invalid: ComputedRef<boolean>;
  required: ComputedRef<boolean>;
}

const KEY: InjectionKey<FormFieldContext> = Symbol("form-field");

export function provideFormField(ctx: FormFieldContext) {
  provide(KEY, ctx);
}

/** Lets inputs pick up id / aria-describedby / aria-invalid from the surrounding UiFormField. */
export function useFormField(): FormFieldContext | undefined {
  return inject(KEY, undefined);
}
