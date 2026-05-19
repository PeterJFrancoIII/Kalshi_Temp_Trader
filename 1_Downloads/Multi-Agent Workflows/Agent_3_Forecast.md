## Agent 3 — Forecast Model Layer

Model:
Gemini 3.5 Flash High/Low
Alt model:
Sonnet 4.6

**Role:** Own and maintain the integer-temperature probability distribution pipeline for KMIA daily max temperature forecasting.

---

### What I build

A canonical `Dict[int, float]` distribution over Fahrenheit integer temperatures (e.g. `{83: 0.12, 84: 0.21, 85: 0.34, ...}`). This is the core probabilistic output that every downstream consumer — signal generation, contract mapping, calibration scoring — reads from.

---

### Files I own

| File                                                                                                                                                   | Purpose                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">distribution_utils.py</span>`              | Shared math: build discrete normal, shift, zero-floor, normalize, CDF, fixed-bin aggregation                               |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">rules_model_v2.py</span>`                  | Blends climatology + NWS forecast → outputs `integer_distribution` + backward-compat `probability_bins`               |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">twc_daily_max_distribution.py</span>`      | Converts TWC hourly PDFs → integer daily-max distribution                                                                 |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">kmia_observation_bias_corrector.py</span>` | Applies NWS live obs constraints (truncation, sea breeze, warm ramp) to integer dist                                       |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">kmia_distribution_blender.py</span>`       | Blends TWC + NBM + HRRR into one canonical integer distribution                                                            |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">contract_probability_mapper.py</span>`     | Integrates integer dist over arbitrary Kalshi contract ranges                                                              |
| `<span class="md-inline-path-prefix">backend/src/forecasting/</span><span class="md-inline-path-filename">bin_converter.py</span>`                   | Legacy: integer °F → 6 fixed bin label (kept for `<span class="md-inline-path-filename">rules_model.py</span>` compat) |

---

### The pipeline in one line

NWS forecast_high_f

  → build_integer_distribution()          # discrete normal, std=3°F

  → apply_weather_suppression_integer()   # thunderstorm/rain/overcast cooling shifts

  → zero_impossible_temps()               # floor at observed max

  → integer_dist_to_fixed_bins()          # for display / legacy callers

  → map_distribution_to_contracts()       # → per-ticker probability for signal gen

---

### Key contract with downstream agents

* **Output format:** `integer_distribution: Dict[int, float]` — keys are `int` °F, values sum to 1.0.
* **Fixed bins are display-only.** The 6 bins (`<=78` … `>=87`) are produced for backward compatibility. All active signal and calibration logic should consume `integer_distribution`.
* **No live trading.** Every file carries `# NO REAL TRADING EXECUTION / DRY-RUN / PAPER EVALUATION ONLY`.
* **Test suite:** `TestDistributionUtils` (27 tests), `TestTWCDailyMaxDistribution`, `TestKMIADistributionBlender`, `TestKmiaObservationBiasCorrector`, `TestContractProbabilityMapper` — all in `<span class="md-inline-path-filename">run_tests.py</span>`, 209 total pass.
