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

/** Months charged for a year: yearly plans are 12 months for the price of 10. */
export const YEARLY_PAID_MONTHS = 10;

export function monthlyPrice(plan: Plan): number {
  return parseFloat(plan.price_monthly);
}

/** What the period costs. The server computes the actual charge the same way (monthly × 10 for a year). */
export function priceFor(plan: Plan, interval: "monthly" | "yearly"): number {
  return interval === "yearly" ? monthlyPrice(plan) * YEARLY_PAID_MONTHS : monthlyPrice(plan);
}

/** Yearly figures for display: the full 12-month price (struck through), the effective monthly price and the saving. */
export function yearlyBreakdown(plan: Plan) {
  const m = monthlyPrice(plan);
  return { full: m * 12, price: m * YEARLY_PAID_MONTHS, perMonth: Math.round((m * YEARLY_PAID_MONTHS) / 12), saving: m * (12 - YEARLY_PAID_MONTHS) };
}


export type PlanAction = "extend" | "upgrade" | "switch" | "choose";

export function actionFor(plan: Plan, currentCode: string | null | undefined, plans: Plan[]): PlanAction {
  if (!currentCode) return "choose";
  if (plan.code === currentCode) return "extend";
  const current = plans.find((p) => p.code === currentCode);
  if (!current) return "choose";
  return parseFloat(plan.price_monthly) > parseFloat(current.price_monthly) ? "upgrade" : "switch";
}


/** What a plan card lists: its own limits first, then what every plan gets. */
export function planFeatures(plan: Plan): string[] {
  return [
    `${storageLabel(plan.storage_bytes)} of encrypted storage`,
    `Files up to ${storageLabel(plan.max_file_size)} each`,
    `${plan.version_retention_days}-day version history`,
    "Unmetered downloads",
    "Preview photos, videos and documents",
  ];
}


/** Button label on a plan card, relative to the person's current plan. */
export function ctaLabel(plan: Plan, action: PlanAction): string {
  return { extend: "Add more time", upgrade: "Upgrade", switch: `Switch to ${plan.name}`, choose: `Get ${plan.name}` }[action];
}

/** Heading for checkout. */
export function checkoutHeading(plan: Plan, action: PlanAction): string {
  return { extend: `Add time to ${plan.name}`, upgrade: `Upgrade to ${plan.name}`, switch: `Switch to ${plan.name}`, choose: `Get ${plan.name}` }[action];
}
