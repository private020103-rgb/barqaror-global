# Uzbek Quality Suite

Ushbu benchmark to'plami quyidagi subsetlardan iborat:

- `lotin_kirill_mapping`: lotin↔kirill transliteratsiya holatlari.
- `apostrof_imlo_variants`: apostrof (`'`, `ʻ`, `` ` ``) va imlo variantlari.
- `rasmiy_norasmiy_uslub`: rasmiy vs norasmiy stil mosligi va mazmunni saqlash.
- `sheva_robustness`: sheva elementlarini adabiy/standart ko'rinishga normallashtirish.

## Thresholdlar

Thresholdlar `metrics_thresholds.json` faylida saqlanadi va har subset uchun alohida metric qo'yilgan.

## Ishga tushirish

```bash
python eval/uzbek_quality_suite/evaluate.py \
  --predictions-dir eval/uzbek_quality_suite/predictions/example \
  --out eval/uzbek_quality_suite/results/latest_results.json

python eval/uzbek_quality_suite/update_weekly_report.py \
  --results eval/uzbek_quality_suite/results/latest_results.json \
  --report eval/weekly_report.md
```

## Haftalik reportga avtomatik qo'shish

`.github/workflows/weekly-uzbek-quality-report.yml` workflow har hafta ishga tushadi:

1. benchmark natijasini hisoblaydi;
2. `eval/weekly_report.md` ni yangilaydi;
3. o'zgarish bo'lsa branchga commit/push qiladi.
