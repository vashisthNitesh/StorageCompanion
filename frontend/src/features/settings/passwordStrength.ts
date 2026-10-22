// Small, dependency-free strength estimate for the password form.
const COMMON = new Set(
  [
    "password", "password1", "password123", "passw0rd", "123456", "12345678", "123456789", "1234567890", "qwerty",
    "qwerty123", "abc123", "111111", "iloveyou", "admin", "welcome", "letmein", "monkey", "dragon", "football",
    "baseball", "sunshine", "princess", "shadow", "superman", "michael", "india123", "india@123", "smartspace",
    "smartspace123", "changeme", "qwertyuiop", "asdfghjkl", "zaq12wsx", "1q2w3e4r", "aa123456", "p@ssw0rd",
  ].map((p) => p.toLowerCase())
);

export interface StrengthResult {
  score: 0 | 1 | 2 | 3 | 4;
  label: "Too weak" | "Weak" | "Fair" | "Good" | "Strong";
  checks: { label: string; ok: boolean }[];
}

export function isCommonPassword(pw: string): boolean {
  const lower = pw.toLowerCase();
  return COMMON.has(lower) || COMMON.has(lower.replace(/[0-9!@#$%^&*]+$/, "")) || /^(.)\1+$/.test(pw);
}

export function passwordStrength(pw: string, current = ""): StrengthResult {
  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((r) => r.test(pw)).length;
  const checks = [
    { label: "At least 12 characters", ok: pw.length >= 12 },
    { label: "Different from your current password", ok: !!pw && pw !== current },
    { label: "Not a common or easily guessed password", ok: !!pw && !isCommonPassword(pw) },
  ];
  let score = 0;
  if (pw.length >= 12) score++;
  if (pw.length >= 16) score++;
  if (classes >= 3) score++;
  if (pw.length >= 12 && !isCommonPassword(pw) && classes >= 2) score++;
  if (!checks.every((c) => c.ok)) score = Math.min(score, 1);
  const s = Math.min(4, score) as StrengthResult["score"];
  return { score: s, label: (["Too weak", "Weak", "Fair", "Good", "Strong"] as const)[s], checks };
}
