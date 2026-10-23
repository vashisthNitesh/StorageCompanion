import type { Plan } from "../../stores/billing";

/** What every plan really gets (from product behaviour, not marketing copy). */
export const INCLUDED_IN_ALL = [
  "Encrypted on your device",
  "Original quality, never compressed",
  "Unmetered downloads",
  "Two-step verification",
  "Search across all folders",
];

/** Plan highlighted as the best fit for most people. */
export const RECOMMENDED_CODE = "value";

const AUDIENCE: Record<string, string> = {
  entry: "Documents, receipts and backups",
  smart: "Personal photo and video libraries",
  value: "Photographers and 4K video",
  super: "Studios and video editors",
  mega: "Agencies and large archives",
};

export function storageLabel(bytes: number): string {
  const gb = bytes / 1024 ** 3;
  if (gb >= 1000) return `${+(gb / 1000).toFixed(1)} TB`;
  return `${Math.round(gb)} GB`;
}

export function audienceFor(plan: Plan): string {
  return AUDIENCE[plan.code] ?? plan.description.split(/[.,]/)[0];
}

export function priceFor(plan: Plan, interval: "monthly" | "yearly"): number {
  return parseFloat(interval === "yearly" ? plan.price_yearly : plan.price_monthly);
}

export function yearlySavingsPercent(plans: Plan[]): number {
  const savings = plans.map((p) => 1 - parseFloat(p.price_yearly) / (parseFloat(p.price_monthly) * 12)).filter((s) => s > 0);
  return savings.length ? Math.round(Math.min(...savings) * 100) : 0;
}

export type PlanAction = "extend" | "upgrade" | "switch" | "choose";

export function actionFor(plan: Plan, currentCode: string | null | undefined, plans: Plan[]): PlanAction {
  if (!currentCode) return "choose";
  if (plan.code === currentCode) return "extend";
  const current = plans.find((p) => p.code === currentCode);
  if (!current) return "choose";
  return parseFloat(plan.price_monthly) > parseFloat(current.price_monthly) ? "upgrade" : "switch";
}

export const GST_RATE = 0.18;
export function gstBreakdown(total: number) {
  const base = Math.round((total / (1 + GST_RATE)) * 100) / 100;
  return { base, gst: Math.round((total - base) * 100) / 100, total };
}
