# Offline pricing calculator — BSI / We Sell Stuff

Use Python 3 only. No internet, tokens, API keys or store updates:

```sh
python commerce/tools/pricing_audit.py commerce/tools/sample_historical_2026_10_13.csv
python -m unittest discover -s commerce/tools -p 'test_*.py' -v
```

CSV needs `name,retail,blank_cost,print_cost`. Optional costs:
`other_production_cost,platform_rate_pct,platform_fixed_fee,seller_shipping_cost,other_variable_cost`.
All figures USD. `print_cost` **adds to** `blank_cost`: a historic tee blank at
$9.50 plus front print $5.95 yields total cost $15.45, NOT $9.50.
For an already-combined production cost, set `print_cost=0` to avoid double counting.

**The CSV is dated historical sample data, not current Fourthwall inventory.**
Production margin is retail minus production cost. Estimated contribution also subtracts
only the additional fees and seller-borne variable costs explicitly supplied. These are not
net company profits, orders, or earned revenue. Shipping charged to buyer is not automatically
a seller expense; seller-paid shipping must be entered. The recommended price floor meets both
a 30% estimated contribution margin and $5 per-unit minimum unless CLI overrides them.
It is NOT a live approved price: pricing must also consider demand and verified current offers.

No automatic listing, publication or price changes. Preserve brand separation:
Trail Forge; Samurai/Japanese; Nordic/Norse; Celtic; Christian/Biblical.
Futuristic noir and retail licensing expansion remain out of scope.
