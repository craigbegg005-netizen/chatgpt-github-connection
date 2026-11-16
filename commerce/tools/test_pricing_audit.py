import unittest
from pricing_audit import audit

class PricingAuditTests(unittest.TestCase):
    def test_tee_print_cost_additive(self):
        x = audit(dict(name="Tee", retail="28", blank_cost="9.50", print_cost="5.95"))
        self.assertEqual(x["production_cost_usd"], "15.45")
        self.assertEqual(x["gross_production_margin_usd"], "12.55")
        self.assertEqual(x["gross_production_margin_pct"], "44.82")
    def test_historical_poster_mug(self):
        p = audit(dict(name="Poster", retail=25, blank_cost=5.50, print_cost=0))
        m = audit(dict(name="Mug", retail=20, blank_cost=5.95, print_cost=0))
        self.assertEqual(p["gross_production_margin_usd"], "19.50")
        self.assertEqual(m["gross_production_margin_usd"], "14.05")
    def test_fee_shipping_changes_contribution(self):
        x = audit(dict(name="Tee", retail=28, blank_cost=9.50, print_cost=5.95,
                       platform_rate_pct=5, platform_fixed_fee=.30, seller_shipping_cost=3))
        self.assertEqual(x["estimated_contribution_usd"], "7.85")
        self.assertFalse(x["meets_margin_gate"])
        self.assertGreater(float(x["price_floor_target_usd"]), 28)
    def test_zero_retail(self):
        x = audit(dict(name="Sample", retail=0, blank_cost=1, print_cost=0))
        self.assertIsNone(x["estimated_contribution_pct"])
    def test_bad_values_fail_closed(self):
        x = dict(name="Sample", retail=5, blank_cost=1, print_cost=0)
        for v in ("nan", "-1", "Infinity"):
            with self.assertRaises(ValueError):
                audit({**x, "retail": v})
        with self.assertRaises(ValueError):
            audit({**x, "platform_rate_pct": 10}, target_margin_pct=97)

if __name__ == "__main__":
    unittest.main()
