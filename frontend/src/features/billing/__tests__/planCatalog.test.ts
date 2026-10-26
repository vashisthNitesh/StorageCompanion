import { describe, expect, it } from "vitest";
import type { Plan } from "../../../stores/billing";
import { YEARLY_PAID_MONTHS, monthlyPrice, priceFor, yearlyBreakdown } from "../planCatalog";

const plan = (price_monthly: string) => ({ code: "value", price_monthly, price_yearly: "0" }) as unknown as Plan;

describe("plan pricing", () => {
  it("charges the monthly price for a month", () => {
    expect(priceFor(plan("149.00"), "monthly")).toBe(149);
  });

  it("charges ten months for a year, ignoring the stored yearly column", () => {
    expect(YEARLY_PAID_MONTHS).toBe(10);
    expect(priceFor(plan("149.00"), "yearly")).toBe(1490);
  });

  it("shows the struck-through full year, the saving and the effective monthly price", () => {
    expect(yearlyBreakdown(plan("149.00"))).toEqual({ full: 1788, price: 1490, perMonth: 124, saving: 298 });
    expect(yearlyBreakdown(plan("39.00"))).toEqual({ full: 468, price: 390, perMonth: 33, saving: 78 });
  });

  it("checkout total equals the yearly price and full minus saving", () => {
    for (const m of ["39.00", "89.00", "149.00", "249.00", "449.00"]) {
      const y = yearlyBreakdown(plan(m));
      expect(y.full - y.saving).toBe(y.price);
      expect(priceFor(plan(m), "yearly")).toBe(monthlyPrice(plan(m)) * 10);
    }
  });
});
