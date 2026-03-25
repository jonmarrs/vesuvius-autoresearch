# Local Data Manifest

This document lists the offline datasets currently built and stored in `local_data/`. These datasets are completely excluded from git due to their massive size (~63GB total). To regenerate these datasets locally, run the interactive downloader: `python3 scripts/download_data.py`.

## Generated 1GB Continuous Cross-Scroll Datasets

| Dataset | Size | Status |
|---|---|---|
| `MiniRealScroll_1_1GB` | 959.35 MB | Ready |
| `MiniRealScroll_5_1GB` | 252.01 MB | Ready |
| `PHerc0009B_1GB` | 925.02 MB | Ready |
| `PHerc0125_1GB` | 915.22 MB | Ready |
| `PHerc0139_1GB` | 959.35 MB | Ready |
| `PHerc0139_div_100_1GB` | 499.73 MB | Ready |
| `PHerc0139_div_10_1GB` | 984.89 MB | Ready |
| `PHerc0139_div_20_1GB` | 909.23 MB | Ready |
| `PHerc0139_div_30_1GB` | 960.08 MB | Ready |
| `PHerc0139_div_40_1GB` | 1013.37 MB | Ready |
| `PHerc0139_div_50_1GB` | 936.57 MB | Ready |
| `PHerc0139_div_60_1GB` | 995.38 MB | Ready |
| `PHerc0139_div_70_1GB` | 1001.71 MB | Ready |
| `PHerc0139_div_80_1GB` | 1011.62 MB | Ready |
| `PHerc0139_div_90_1GB` | 1018.69 MB | Ready |
| `PHerc0172_1GB` | 252.01 MB | Ready |
| `PHerc0172_div_0_1GB` | 939.54 MB | Ready |
| `PHerc0172_div_100_1GB` | 809.62 MB | Ready |
| `PHerc0172_div_10_1GB` | 1024.01 MB | Ready |
| `PHerc0172_div_20_1GB` | 1023.97 MB | Ready |
| `PHerc0172_div_30_1GB` | 1024.01 MB | Ready |
| `PHerc0172_div_40_1GB` | 1024.01 MB | Ready |
| `PHerc0172_div_50_1GB` | 1023.95 MB | Ready |
| `PHerc0172_div_60_1GB` | 1023.96 MB | Ready |
| `PHerc0172_div_70_1GB` | 1023.98 MB | Ready |
| `PHerc0172_div_80_1GB` | 1021.90 MB | Ready |
| `PHerc0172_div_90_1GB` | 1023.90 MB | Ready |
| `PHerc0175A_1GB` | 373.03 MB | Ready |
| `PHerc0175B_1GB` | 232.73 MB | Ready |
| `PHerc0191_1GB` | 453.53 MB | Ready |
| `PHerc0211_1GB` | 397.21 MB | Ready |
| `PHerc0257_1GB` | 378.80 MB | Ready |
| `PHerc0268_1GB` | 363.91 MB | Ready |
| `PHerc0306B_1GB` | 196.02 MB | Ready |
| `PHerc0332_1GB` | 918.54 MB | Ready |
| `PHerc0332_div_100_1GB` | 799.18 MB | Ready |
| `PHerc0332_div_10_1GB` | 966.26 MB | Ready |
| `PHerc0332_div_20_1GB` | 1023.55 MB | Ready |
| `PHerc0332_div_30_1GB` | 1022.85 MB | Ready |
| `PHerc0332_div_40_1GB` | 1022.95 MB | Ready |
| `PHerc0332_div_50_1GB` | 1022.32 MB | Ready |
| `PHerc0332_div_60_1GB` | 1022.08 MB | Ready |
| `PHerc0332_div_70_1GB` | 1022.30 MB | Ready |
| `PHerc0332_div_80_1GB` | 1023.26 MB | Ready |
| `PHerc0332_div_90_1GB` | 1023.46 MB | Ready |
| `PHerc0343P_1GB` | 284.43 MB | Ready |
| `PHerc0343_1GB` | 946.67 MB | Ready |
| `PHerc0358_1GB` | 720.36 MB | Ready |
| `PHerc0483A_1GB` | 157.34 MB | Ready |
| `PHerc0483B_1GB` | 636.31 MB | Ready |
| `PHerc0490A_1GB` | 653.45 MB | Ready |
| `PHerc0490B_1GB` | 886.86 MB | Ready |
| `PHerc0500P2_1GB` | 383.71 MB | Ready |
| `PHerc0800_1GB` | 845.37 MB | Ready |
| `PHerc0813_1GB` | 951.84 MB | Ready |
| `PHerc0814_1GB` | 803.63 MB | Ready |
| `PHerc0826_1GB` | 872.17 MB | Ready |
| `PHerc0841_1GB` | 419.92 MB | Ready |
| `PHerc0846A_1GB` | 695.20 MB | Ready |
| `PHerc0846B_1GB` | 664.23 MB | Ready |
| `PHerc1203_1GB` | 849.65 MB | Ready |
| `PHerc1218_1GB` | 933.22 MB | Ready |
| `PHerc1299_1GB` | 981.57 MB | Ready |
| `PHerc1447_1GB` | 952.02 MB | Ready |
| `PHerc1451_1GB` | 350.75 MB | Ready |
| `PHerc1545_1GB` | 745.50 MB | Ready |
| `PHercMAN5_1GB` | 839.47 MB | Ready |
| `PHercMANB_1GB` | 945.06 MB | Ready |
| `PHercMANBp_1GB` | 763.96 MB | Ready |
| `RealScroll_1_1GB` | 959.35 MB | Ready |
| `RealScroll_5_1GB` | 252.01 MB | Ready |

## Sub-sectional Division Datasets (11x 1GB Splits)

These represent 1GB slices taken at 10% depth intervals through the full scroll volumes to ensure diverse topological representation.

| Dataset | Scroll | Division |
|---|---|---|
| `PHerc0139_div_0_1GB` | PHerc0139 | 0% |
| `PHerc0139_div_100_1GB` | PHerc0139 | 100% |
| `PHerc0139_div_10_1GB` | PHerc0139 | 10% |
| `PHerc0139_div_20_1GB` | PHerc0139 | 20% |
| `PHerc0139_div_30_1GB` | PHerc0139 | 30% |
| `PHerc0139_div_40_1GB` | PHerc0139 | 40% |
| `PHerc0139_div_50_1GB` | PHerc0139 | 50% |
| `PHerc0139_div_60_1GB` | PHerc0139 | 60% |
| `PHerc0139_div_70_1GB` | PHerc0139 | 70% |
| `PHerc0139_div_80_1GB` | PHerc0139 | 80% |
| `PHerc0139_div_90_1GB` | PHerc0139 | 90% |
| `PHerc0172_div_0_1GB` | PHerc0172 | 0% |
| `PHerc0172_div_100_1GB` | PHerc0172 | 100% |
| `PHerc0172_div_10_1GB` | PHerc0172 | 10% |
| `PHerc0172_div_20_1GB` | PHerc0172 | 20% |
| `PHerc0172_div_30_1GB` | PHerc0172 | 30% |
| `PHerc0172_div_40_1GB` | PHerc0172 | 40% |
| `PHerc0172_div_50_1GB` | PHerc0172 | 50% |
| `PHerc0172_div_60_1GB` | PHerc0172 | 60% |
| `PHerc0172_div_70_1GB` | PHerc0172 | 70% |
| `PHerc0172_div_80_1GB` | PHerc0172 | 80% |
| `PHerc0172_div_90_1GB` | PHerc0172 | 90% |
| `PHerc0332_div_0_1GB` | PHerc0332 | 0% |
| `PHerc0332_div_100_1GB` | PHerc0332 | 100% |
| `PHerc0332_div_10_1GB` | PHerc0332 | 10% |
| `PHerc0332_div_20_1GB` | PHerc0332 | 20% |
| `PHerc0332_div_30_1GB` | PHerc0332 | 30% |
| `PHerc0332_div_40_1GB` | PHerc0332 | 40% |
| `PHerc0332_div_50_1GB` | PHerc0332 | 50% |
| `PHerc0332_div_60_1GB` | PHerc0332 | 60% |
| `PHerc0332_div_70_1GB` | PHerc0332 | 70% |
| `PHerc0332_div_80_1GB` | PHerc0332 | 80% |
| `PHerc0332_div_90_1GB` | PHerc0332 | 90% |
