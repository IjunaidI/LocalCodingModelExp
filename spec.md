# Minimal pricing spec — 5 rules

Build `process_calculations(csv_path)`. It reads a CSV (header names may have extra
spaces; cells may be empty) and returns a list of dicts, one per row, each containing
the key `total_receivables`.

## Input columns
- `productid` : 1, 2, or 3
- `status` : individual or corporate (case-insensitive)
- `volume` : integer
- `season` : spring / summer / winter / autumn
- `customer` : strategic / non-strategic
- `tax verified` : the text "yes" or "no"

## Product rates
```
PRODUCT_RATES = {
    1: {"individual": 1000, "corporate": 900},
    2: {"individual": 1500, "corporate": 1200},
    3: {"individual": 2000, "corporate": 1700},
}
```

## The 5 rules (apply in order)
1. **Rate**: pick the rate from PRODUCT_RATES using productid and status.
2. **Base**: `base = volume * rate`.
3. **Spring discount**: if season is spring, multiply base by 0.95 (a 5% discount);
   otherwise leave it unchanged.
4. **Strategic discount**: if customer is strategic, multiply by another 0.95
   (a further 5% discount); otherwise leave it unchanged.
5. **Tax withholding**: if `tax verified` is the text "no", multiply by 0.97
   (a 3% withholding); if it is "yes", leave it unchanged.

`total_receivables` is the value after applying rules 1–5 in order.

Output: list of dicts, each with key `total_receivables`.
