import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { ApiError } from "../../lib/api";
import { rules, useForm } from "../useForm";

describe("useForm", () => {
  it("validates on blur, then live, and maps server field errors", async () => {
    const form = useForm({ email: "", password: "" }, { email: [rules.required(), rules.email()], password: [rules.minLength(12)] });
    form.values.email = "nope";
    form.blur("email");
    expect(form.errors.email).toMatch(/valid email/);
    form.values.email = "a@b.co";
    await nextTick();
    expect(form.errors.email).toBeUndefined();

    const ok = await form.submit(async () => {
      throw new ApiError("HTTP 400", 400, { error: "x", details: { password: ["This password is too common."] } });
    });
    expect(ok).toBe(false);
    form.values.password = "a-long-enough-password";
    form.blur("password");
    expect(form.errors.password).toBeUndefined();
  });
});
