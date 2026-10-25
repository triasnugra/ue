# Unified Engine (preview)
Upload via GitHub Web: Add file > Upload files (seluruh isi folder, termasuk `.github`). Lalu Settings > Pages > Source = **GitHub Actions**, Settings > Actions > Workflow permissions = **Read and write**, lalu Actions > "Analisis dan Deploy" > Run workflow.
- `engine/plan.py: calc_tp_sl` = inti TP/SL (beku). `engine/evaluate.py` = evaluator kronologis. `engine/journal.py: recover_legacy` = pemulihan simbol/waktu setup lama.
- Tes lokal: `python -m unittest discover -s tests -t .`
- Universe 100% dinamis via CCXT (Binance/Bybit/Bitget). TradingView tidak punya API data resmi, jadi tidak dipakai.
- Nilai guard (`max_entry_dist_atr`, dll.) adalah hipotesis awal: tetapkan, kunci, lalu uji; jangan disetel ulang setelah melihat hasil.
