Deep Research 3

To the Trading Strategy Committee:
As of May 5, 2026, the forecasting landscape for Miami International Airport (KMIA) has shifted following the operational implementation of **NBM v5.0** (April 15, 2026). This technical analysis outlines a probabilistic system optimized for the 11:00 AM ET Kalshi market opening, prioritizing localized sea-breeze dynamics and recent climate non-stationarity.
### A. Recommended 24-Hour End-to-End Architecture
We recommend a **Two-Stage Multi-Model Ensemble Post-Processing (EMPP)** architecture.
 1. **Ingestion Layer:** At 10:45 AM ET (1445 UTC), trigger a pipeline to ingest the **12Z HRRR** (which provides 48-hour coverage) and the **06Z NBM v5.0** (or the latest hourly update).
 2. **Feature Extraction:** Extract station-level percentiles (10th, 25th, 50th, 75th, 90th) from NBM and hourly wind/temperature fields from HRRR to compute sea-breeze timing.
 3. **Probabilistic Core:** Use a **Natural Gradient Boosting (NGB)** or **Quantile Gradient Boosting (QGB)** model to predict the parameters of a normal or skewed-normal distribution for T_{MAX}.
 4. **Isotonic Calibration:** Map the continuous distribution into the specific Kalshi bins. Apply **CORP (Consistent, Optimally Binned, Reproducible, and Post-processed)** calibration to ensure bin probabilities are monotonic and reliable.
 5. **Execution Logic:** Compare the model-implied probability P_{mod} to the Kalshi breakeven probability P_{be}, where P_{be} = p + 0.07 \times p \times (1-p) for taker orders.[1, 2]
### B. Ranked List of Highest-Impact Improvements
| Rank | Improvement | Rationale |
|---|---|---|
| 1 | **NBM v5.0 Station Percentiles** | Uses quantile mapping to provide calibrated station-specific uncertainty. |
| 2 | **HRRR Sea-Breeze Classifier** | KMIA temperatures are binary: either capped by early marine air or spiking under delayed onset. |
| 3 | **Recent-Era Weighting** | 1950–1990 data is now systematically too cold; weighting 2010–2026 data reduces bias. |
| 4 | **CORP Isotonic Calibration** | Ensures that a "30% probability" forecast corresponds to a 30% observed frequency. |
| 5 | **12Z HRRR Nowcasting** | Captures same-day convective trends that influence the thermal state at Day D+1 market open. |
### C. Data-Source Comparison (11:00 AM ET Availability)
| Source | Latest Run | Lead Time to D+1 | Latency | Key Parameters |
|---|---|---|---|---|
| **NBM v5.0** | 12Z/13Z | ~24h | ~60m | MaxT QMD Mean, 10/25/50/75/90 percentiles. |
| **HRRR** | 12Z | 48h | ~90m | 10m wind direction, cloud fraction, 2m temp. |
| **GFS** | 06Z | 24h+ | ~3.5h | 850mb temp (air mass marker), synoptic ridging. |
| **ECMWF ENS** | 00Z | 24h+ | ~7h | Multi-member spread for tail-risk analysis. |
| **METAR** | 1453Z | Nowcast | Real-time | Current KMIA air temp and pressure trend. |
### D. Modeling-Method Comparison
| Method | Best Use Case | Pros | Cons |
|---|---|---|---|
| **NGBoost** | Distribution Params | Estimates full PDF (mean, SD) iteratively. | Prone to over-smoothing tails. |
| **Quantile Reg.** | Threshold Events | Flexible; handles skewed data well. | Quantiles can "cross" (non-monotonic). |
| **BMA** | Ensemble Blending | Weights models by past performance. | Complex implementation for station-level. |
| **EMOS** | Operational Speed | Fast; fits Gaussian to ensemble spread. | Captures spread but not complex features. |
### E. KMIA Sea-Breeze Feature Plan
Miami high temperatures are highly sensitive to the **Atlantic sea breeze front (SBF)**.
 * **Sea Breeze Onset Feature:** Defined as the hour when HRRR 10m wind shifts from West/Northwest (270^\circ-330^\circ) to Southeast/East (100^\circ-140^\circ).
 * **Thermal Gradient:** Difference between HRRR 2m temperature at KMIA and the sea surface temperature (SST) at nearby buoys.
 * **Critical Threshold:** If HRRR predicts SBF onset before 1:00 PM local time, we should systematically shift weight to the <=78 or 79-80 bins.
 * **Delayed Onset:** If HRRR predicts offshore flow through 4:00 PM, the probability of hit >=87 increases by an estimated 2.5 \times baseline.
### F. Backtesting and Calibration Plan
 * **Pristine Holdout:** Use May 2025–April 2026 as an out-of-sample test set to validate NBM v5.0 parallel performance.
 * **Evaluation Metrics:**
   * **Brier Score:** Total probabilistic accuracy.
   * **CRPS:** Skill of the full distribution.
   * **Reliability Diagrams:** Verify calibration of >=87 bin specifically.
 * **Lookahead Filter:** The backtest must use the **06Z NBM** or **12Z HRRR** only to mimic the 11 AM ET execution window.
### G. Minimal Viable Model (MVM)
 1. **Input:** 06Z NBM v5.0 station percentile data for KMIA (TXNP1 to TXNP9).
 2. **Model:** Simple Normal distribution fit using the 10th and 90th NBM percentiles as \mu \pm 1.28\sigma.
 3. **Output:** Integral of the Normal PDF over the Kalshi bin ranges.
 4. **Trading Rule:** Execute only if (\text{Model Prob} - \text{Price}) > 0.05.
### H. Ideal Production Model
 1. **Multi-Model Input:** Fusion of NBM v5.0, 12Z HRRR, and 00Z ECMWF ENS.
 2. **Machine Learning:** NGBoost using **12-month rolling training** to capture seasonal bias.
 3. **Specific Features:** Sea-breeze timing, convective cloud cover fraction, and 850mb temperature anomaly.
 4. **Calibration:** Post-processed with CORP isotonic regression to minimize **Expected Calibration Error (ECE)**.
### I. Operational Risks and Monitoring
 * **Settlement Mismatch:** Kalshi settles on the **NWS CLI** report, which can be revised. Preliminary METAR data may show 82.7$^\circ F$ (rounds to 83) while the CLI settles on 82. Never trade size on a 1-cent edge near a bin boundary.
 * **Rounding Nuance:** NWS CLI uses "round half-up asymmetric". 82.5$^\circ F$ becomes 83.
 * **Model Latency:** If 12Z HRRR is delayed, the system must fail-over to the 11Z run, which has an 18-hour horizon and may not fully cover the target Day D+1 afternoon.
 * **Sensor Malfunction:** Check the METAR remark field for $ (maintenance needed). If present, increase the model's uncertainty floor by 1.5 \times.
**Analyst Recommendation:** Beginners should prioritize the **<=78** and **>=87** tails during the transitional months (May/October) where the sea-breeze signal is strongest. Avoid high-stakes trading during model cutover weeks (e.g., this week) as NBM v5.0 stabilization may introduce short-term bias.
