#!/usr/bin/env python3
"""Zero-spend, offline estimated unit margin audit. Does not change Fourthwall prices."""
import argparse
import csv
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP

CENT = Decimal("0.01")
def amount(value, name):
    try:
        v = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name}: numeric USD value required") from exc
    if not v.is_finite() or v < 0:
        raise ValueError(f"{name}: negative or nonfinite value")
    return v

def usd(value):
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))

def ceil_cents(value):
    return (value / CENT).to_integral_value(rounding=ROUND_CEILING) * CENT

def audit(row, target_margin_pct="30", min_contribution="5"):
    """Historical/examples are NOT live catalog data; resulting profit is NOT net company profit."""
    name = str(row.get("name", "")).strip()
    if not name:
        raise ValueError("name required")
    price = amount(row["retail"], "retail")
    blank = amount(row["blank_cost"], "blank_cost")
    printing = amount(row["print_cost"], "print_cost")
    extra_production = amount(row.get("other_production_cost") or 0, "other_production_cost")
    rate = amount(row.get("platform_rate_pct") or 0, "platform_rate_pct") / 100
    fixed_fee = amount(row.get("platform_fixed_fee") or 0, "platform_fixed_fee")
    seller_shipping = amount(row.get("seller_shipping_cost") or 0, "seller_shipping_cost")
    other_costs = amount(row.get("other_variable_cost") or 0, "other_variable_cost")
    target = amount(target_margin_pct, "target_margin_pct") / 100
    minimum = amount(min_contribution, "min_contribution")
    if rate >= 1 or target >= 1 or rate + target >= 1:
        raise ValueError("platform fee rate + target margin must be below 100%")
    production = blank + printing + extra_production
    fee_total = price * rate + fixed_fee + seller_shipping + other_costs
    contribution = price - production - fee_total
    floor_fixed = production + fixed_fee + seller_shipping + other_costs
    floor_target = ceil_cents(floor_fixed / (Decimal(1) - rate - target))
    floor_contrib = ceil_cents((floor_fixed + minimum) / (Decimal(1) - rate))
    return {
        "name": name,
        "retail_usd": usd(price),
        "production_cost_usd": usd(production),
        "gross_production_margin_usd": usd(price - production),
        "gross_production_margin_pct": usd((price - production) / price * 100) if price else None,
        "estimated_variable_fees_usd": usd(fee_total),
        "estimated_contribution_usd": usd(contribution),
        "estimated_contribution_pct": usd(contribution / price * 100) if price else None,
        "price_floor_target_usd": usd(max(floor_target, floor_contrib)),
        "meets_contribution_gate": contribution >= minimum,
        "meets_margin_gate": bool(price and contribution / price >= target),
        "assumptions": "Only explicit costs included; NOT net company profit; verify live catalog costs."
    }

def main():
    p = argparse.ArgumentParser(description="Offline, estimate-only product pricing audit")
    p.add_argument("csv_file")
    p.add_argument("--target-margin-pct", default="30")
    p.add_argument("--min-contribution", default="5")
    p.add_argument("--output", choices=("json","csv"), default="json")
    a = p.parse_args()
    try:
        with open(a.csv_file, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError("CSV has no products")
        out = [audit(row, a.target_margin_pct, a.min_contribution) for row in rows]
    except (OSError, KeyError, ValueError) as exc:
        print(f"Pricing audit failed: {exc}", file=sys.stderr)
        return 2
    if a.output == "json":
        print(json.dumps(out, indent=2))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    return 0

if __name__ == "__main__":
    sys.exit(main())
