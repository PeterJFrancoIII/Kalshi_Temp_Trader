# **Quantitative Framework and Systems Architecture for Fully Autonomous Meteorological Derivative Trading via the Kalshi API**

The structural evolution of binary prediction markets has transformed from speculative sentiment aggregators into highly regulated, quote-driven financial environments. Central to this evolution is the Kalshi exchange, which provides a federally licensed platform for trading event contracts tied to real-world outcomes, including economic indicators, political events, and meteorological phenomena.1 The development of a fully autonomous trading bot focused on maximum temperature (Max Temp) markets requires a convergence of low-latency API infrastructure, high-resolution weather data ingestion, and a robust administrative interface for real-time oversight and parameter tuning. By exploiting systemic mispricings in how market participants estimate forecast uncertainty, a well-calibrated system can achieve superior risk-adjusted returns compared to naive benchmarks.3

## **Market Microstructure and the Reciprocal Pricing Model**

In the context of the Kalshi exchange, an event contract is a binary asset that settles at either ![][image1] or ![][image2] based on the occurrence of a defined outcome.1 This differs fundamentally from traditional equity derivatives, where pricing is often derived from the Black-Scholes model or other stochastic volatility frameworks. In prediction markets, the price is the primary signal, representing the market-implied probability of the underlying event.4 A "Yes" contract trading at ![][image3] indicates a ![][image4] collective belief in the event's occurrence, while the corresponding "No" contract reflects the remaining ![][image5].4  
The exchange employs a reciprocal pricing model where the prices of "Yes" and "No" contracts for a specific outcome must always sum to ![][image1].5 This relationship dictates the architecture of the order book. Unlike traditional limit order books (LOB) that display both bids and asks for a single asset, the Kalshi API provides only the bids for both sides of the trade.6 An automated system must synthesize the implied ask prices through the reciprocal relationship. A "Yes Bid" at ![][image6] is mathematically equivalent to a "No Ask" at ![][image7], because a participant willing to pay ![][image6] for "Yes" is functionally equivalent to a participant willing to receive ![][image7] to take the "No" position.6

| Order Element | Source Mapping | Implied Calculation | Economic Rationalization |
| :---- | :---- | :---- | :---- |
| Best YES Bid | yes\_dollars (Last) | Direct API Value | Max price a buyer offers for YES |
| Best NO Bid | no\_dollars (Last) | Direct API Value | Max price a buyer offers for NO |
| Implied YES Ask | ![][image8] | Reciprocal of NO | Min price a seller accepts for YES |
| Implied NO Ask | ![][image9] | Reciprocal of YES | Min price a seller accepts for NO |
| Midpoint | Average of Bid/Ask | ![][image10] | Fair value estimate in liquid markets |

This microstructure ensures that every trade is fully collateralized. When a "Yes" buyer and a "No" buyer are matched, the exchange collects ![][image1] total, which is held in escrow until the contract's expiration.1 The Maker-Taker dynamic is particularly relevant here; liquidity makers who post resting limit orders often capture higher returns than takers, partly because they avoid the slippage inherent in crossing the bid-ask spread.2 Research into Kalshi’s historical performance reveals a "favorite-longshot bias," where low-price contracts (longshots) win far less often than their price suggests, leading to negative expected value for buyers, whereas high-price contracts (favorites) tend to offer small, consistent positive returns.2

## **Technical Infrastructure and API Integration Protocols**

The execution engine of the autonomous bot must interface with the Kalshi Trade API v2, which utilizes a RESTful architecture for account management and order placement, supplemented by a WebSocket protocol for real-time data streaming.5 Reliable automation requires a deep understanding of Kalshi’s authentication security, which relies on RSA-based request signing rather than simple static keys.5

### **Authentication and Cryptographic Signing**

Every authenticated request to the Kalshi API must include specific headers: KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP, and KALSHI-ACCESS-SIGNATURE.5 The signature is a SHA256 with RSA-PSS hash of a string constructed from the timestamp, the HTTP method, and the endpoint path.5 The timestamp must be provided in milliseconds, as using seconds will trigger a signature error.8 Furthermore, query parameters are typically excluded from the signed path, requiring developers to split the URL string at the ? character before hashing.8

| Header Key | Content Description | Implementation Requirement |
| :---- | :---- | :---- |
| KALSHI-ACCESS-KEY | API Key ID | UUID format (e.g., a952bcbe...) |
| KALSHI-ACCESS-TIMESTAMP | Current Epoch Time | Must be in milliseconds |
| KALSHI-ACCESS-SIGNATURE | RSA-PSS SHA256 Signature | Signed {timestamp}{method}{path} |

The use of WebSockets (/ws/v2) is essential for maintaining an accurate local representation of the order book without exceeding REST rate limits, which are typically capped at 10 requests per second for market data.5 A WebSocket connection provides an initial snapshot of the order book followed by incremental deltas, allowing the bot to update its internal state with minimal latency.5 This is critical for high-frequency adjustments to resting limit orders in response to shifting weather forecasts.

### **Order Management and Ticker Naming Conventions**

Successful automation also depends on accurate market discovery. Kalshi organizes its contracts into a hierarchy of Series, Events, and Markets.11 A Series (e.g., KXHIGHNY) encompasses a group of related events, such as the daily high temperature in New York City over a month.11 Each event (e.g., KXHIGHNY-24JAN01) represents a specific date, and within that event, multiple markets exist for different temperature thresholds (e.g., KXHIGHNY-24JAN01-T60 for a high of ![][image11]).11 Tickers should be retrieved dynamically via the /markets endpoint rather than being hardcoded or parsed manually, as naming conventions can occasionally feature exceptions.9

## **Meteorological Data Acquisition and Processing**

The bot's predictive edge is derived from its ability to process meteorological data more effectively than the average market participant. For temperature markets, the ultimate "source of truth" for settlement is the National Weather Service (NWS), specifically the Daily Climate Reports (CLI) issued the morning following the target date.12

### **The NOAA/NWS API Ecosystem**

The primary data pipeline utilizes the NWS API (api.weather.gov), which provides a REST-style, JSON-LD based service for forecasts and observations.14 Accessing station-level data requires a three-step process: first, retrieving metadata for a specific latitude and longitude to find the corresponding grid office and coordinates; second, fetching the grid forecast; and third, accessing hourly observations from the station identifier.15

| Endpoint Category | URL Pattern Example | Data Provided |
| :---- | :---- | :---- |
| Point Metadata | /points/{lat},{lon} | Grid office, X/Y coordinates |
| Grid Forecast | /gridpoints/{WFO}/{X},{Y}/forecast | 12-hour temperature periods |
| Hourly Observations | /stations/{stationId}/observations | Raw METAR data, current temp |
| Latest Observation | /stations/{stationId}/observations/latest | Most recent reading |

A critical technical hurdle is the "MADIS ingest bug," which causes station observation endpoints to frequently return null values for 24-hour maximum and minimum temperatures for stations outside the Central Time Zone.14 To resolve this, a robust bot must calculate its own daily maximums by aggregating hourly METAR observations, rather than relying on the TMAX field in the API response.3

### **Settlement Nuances and the Midnight High**

A sophisticated understanding of settlement rules is required to avoid execution errors during anomalous weather events. Kalshi temperature contracts settle based on the high temperature recorded in the final NWS Daily Climate Report.13 A key detail is that these reports use Local Standard Time (LST). During Daylight Saving Time (DST), the "daily" window effectively runs from 1:00 AM to 12:59 AM the following day.13 This can lead to a "midnight high" where the maximum temperature for the calendar day occurs immediately after the window opens, particularly if a cold front passes through during the early morning hours.3 If the bot does not account for this DST shift, it may place trades based on an incorrect temporal window.

## **Quantitative Strategy and Probabilistic Modeling**

The central thesis of the Max Temp bot is that Kalshi markets systematically overestimate the uncertainty of temperature outcomes.3 Analysis of thousands of city-date observations has shown that market-implied uncertainty exceeds realized uncertainty by a factor of 1.27x.3 This suggests that the market-implied probability distribution is too "flat," underpricing the likelihood of outcomes near the forecast mean and overpricing the "longshot" tail events.3

### **Machine Learning Framework for Forecast Calibration**

To exploit this, the bot employs a boosted decision tree model, such as XGBoost, to predict the forecast error distribution for each city-date.3 The model is trained on approximately 30 features, including:

1. Forecast data from multiple independent sources (GFS, ECMWF, HRRR).3  
2. Historical accuracy metrics for specific NWS Weather Forecast Offices.3  
3. Market microstructure variables, such as order book imbalance and recent price volatility.3  
4. Geographical indicators to account for local microclimates (e.g., the "urban heat island" effect in NYC Central Park vs. airport stations).3

The model's performance is validated using the Diebold-Mariano test, which compares the Brier scores of the model's predicted probabilities against those implied by the market.3 While the market is often more accurate across the entire set of possible buckets, the model shows statistically significant outperformance on "traded buckets"—those where the discrepancy between the model's probability and the market price is largest.3

| Model Metric | Value | Statistical Significance |
| :---- | :---- | :---- |
| Uncertainty Factor | 1.27x | Market-implied vs. Realized |
| Out-of-Sample Sharpe | 4.9 | Annualized (strategy dependent) |
| Model Brier (Traded) | 0.201 | Lower is better |
| Market Brier (Traded) | 0.214 | Comparative baseline |
| PIT Test (KS Stat) | 0.033 | Indicates well-calibrated distribution |

### **Position Sizing and the Kelly Criterion**

The transition from probability estimation to trade execution is governed by the Kelly Criterion, a mathematical formula designed to maximize the long-term growth rate of wealth.19 For a binary contract, the optimal fraction (![][image12]) of the bankroll to wager is:  
![][image13]  
Where:

* ![][image14] is the model's estimated probability of winning.19  
* ![][image15] is the probability of losing (![][image16]).19  
* ![][image17] is the odds received on the wager, calculated as ![][image18].19

In practice, "Full Kelly" betting is often too aggressive, leading to large drawdowns if the model's probability estimates are even slightly overconfident.20 Most professional implementations use a "Fractional Kelly" approach (e.g., Quarter-Kelly), where the bet size is reduced to a fraction of ![][image12] to provide a safety buffer and manage variance.20

## **Autonomous System Architecture and Design Patterns**

A fully autonomous bot must solve engineering challenges regarding reliable connectivity, crash recovery, and concurrent execution.23 A modular architecture that separates the core trading logic from the infrastructure and UI is essential for maintaining stability in a 24/7 trading environment.23

### **Isolation and Strategy Management**

The system should be designed around a plugin or microservices model, where each trading strategy runs as an independent process.23 This ensures that a crash in a specific strategy—perhaps due to an unhandled data format in a new city—does not affect the host application or other running strategies.23 Communication between the host and the strategy plugins can be handled via gRPC or a simple local message bus, allowing for remote start, stop, and configuration commands.23

### **State Persistence and Telemetry Hub**

Central to the bot's resilience is a telemetry hub, typically backed by a performant database like SQLite or Redis.22 Every trade, AI decision score, and risk limit update is logged to this database, which serves as the "single source of truth" for the system.22 This allows the bot to recover its state instantly following a reboot or network failure, ensuring that open positions are tracked and stop-losses remain active.22

| Component | Responsibility | Technical Implementation |
| :---- | :---- | :---- |
| Ingestion Engine | Pulls market universe/weather data | Python, SQLite persistence |
| Decision Engine | Applies ML model to identify edge | XGBoost, pandas integration |
| Execution Manager | Handles RSA signing and order API | REST/WebSocket clients |
| Track & Risk | Manages stops, TP, and resolution | Continuous loop, shared DB state |
| Web Console | Provides UI for monitoring/tuning | Streamlit, Plotly visualization |

## **The Web Console: Oversight, Tuning, and Diagnostics**

While the bot operates autonomously, human oversight is necessary to monitor performance and adjust risk parameters in response to changing market regimes.26 Streamlit has become a dominant framework for building these "trading cockpits" because it allows for rapid development of interactive, data-rich dashboards using pure Python.27

### **Real-Time Dashboard Integration**

The web console should be decoupled from the core trading loop to prevent UI rendering from blocking time-sensitive execution.22 The dashboard acts as a "view" on the telemetry database, periodically refreshing to show:

* **Portfolio Metrics:** Total P\&L, win rate, current cash, and open position value.32  
* **Market Scanners:** Live order book spreads and model-implied probabilities vs. market prices.22  
* **Decision Logs:** A historical record of the AI's reasoning for each trade, including the features that drove the decision.22  
* **Diagnostic Charts:** Equity curves, drawdown plots, and Sharpe ratio heatmaps for parameter optimization.28

### **Parameter Tuning and Interactive Controls**

A "Full Web Console" must include controls for real-time parameter tuning.28 Using Streamlit's sidebar or input widgets, a user can adjust global risk settings without needing to modify code or restart the bot.

| Parameter | UI Control Type | Functionality |
| :---- | :---- | :---- |
| Max Drawdown Limit | Number Input/Slider | Sets the global circuit breaker threshold |
| Kelly Fraction | Slider (![][image19] to ![][image20]) | Toggles between conservative and aggressive sizing |
| Min Confidence Score | Slider | Filters out trades with low model certainty |
| Active Markets | Multiselect | Enables/disables specific cities or series |
| Stop-Loss % | Number Input | Configures the hard exit threshold for all positions |

To prevent overfitting, the console can facilitate "Walk-Forward Analysis," where the user optimizes parameters over rolling historical windows.28 This ensures that a configuration that worked on past data is robust enough to generalize to future conditions. Monte Carlo simulations can also be run directly from the UI, shuffling trade orders to see the distribution of potential outcomes and assess the "luck vs. skill" factor.28

## **Risk Management and Algorithmic Circuit Breakers**

In automated trading, risk control is the "brakes" of the system—it is useless until it is essential.24 A multi-tier risk layer must be implemented to protect capital from model failure, exchange glitches, or black swan events.24

### **Tiered Circuit Breaker Logic**

The bot should monitor its own performance in real-time and trigger progressively restrictive actions as losses accumulate.35

1. **Normal Tier:** The bot operates at ![][image21] of its configured position allocation.35  
2. **Reduced Tier:** If the drawdown exceeds a certain threshold (e.g., ![][image22]), the bot reduces all new position sizes by ![][image23] to preserve capital while it re-evaluates the market regime.35  
3. **Paused Tier:** If the daily loss limit is hit (e.g., ![][image24] of account value), the bot stops opening new positions but continues to manage existing ones until they hit their stops or resolve.24  
4. **Halted Tier:** If the maximum drawdown limit is breached (e.g., ![][image25]), the bot cancels all open orders, closes all positions, and halts all operations until a manual reset is performed.22

### **ATR-Based Adaptive Stop-Losses**

Fixed percentage stop-losses often fail in volatile markets. A more robust approach is the Average True Range (ATR) stop-loss.24 By calculating the ATR over a 14-period window, the bot can set stops that adapt to the current volatility of the market.24 In low-volatility regimes, stops are tight; in high-volatility regimes, stops widen to avoid being "stopped out" by normal price fluctuations.24

### **Exchange and Data Safeguards**

The risk layer must also monitor for exchange-side anomalies.36 If the bid-ask spread on a market exceeds ![][image26] its moving average, or if the order book depth falls below a critical threshold, the bot should pause trading to avoid being exploited by "one-sided" books or illiquid gaps.36 Furthermore, a data verification layer should cross-reference NWS observations against third-party weather APIs to detect erroneous data spikes before they trigger a trade.37

## **Deployment Considerations and Infrastructure**

An autonomous trading system requires high availability and low latency, making the choice of infrastructure critical.24 Running the bot on a local machine is prone to failure modes like power outages, OS updates, and network drops.24

### **Cloud Hosting and Redundancy**

Deployment on a Virtual Private Server (VPS), such as those provided by DigitalOcean, Vultr, or AWS, ensures ![][image27] uptime and a stable network connection to the Kalshi and NOAA APIs.5 Using Docker for containerization allows for consistent environments across development and production, simplifying the deployment of updates.25

### **Alerting and Notification Systems**

A robust system includes an integrated notification layer to alert the user of significant events.24 Using hooks for Telegram, Slack, or Discord, the bot can send real-time messages for:

* **Trade Executions:** Entry price, size, and model confidence.24  
* **Stop-Loss Triggers:** Final P\&L for the closed position.24  
* **Circuit Breaker Events:** Notifications when the bot enters "Reduced" or "Paused" mode.22  
* **Health Checks:** Periodic "heartbeat" messages confirming that the ingestion and execution loops are still running.22

By combining these elements—sophisticated probabilistic modeling, a modular and resilient architecture, a powerful web oversight console, and multi-tier risk controls—a trader can build a system capable of navigating the complex and often mispriced world of temperature prediction markets. The key to long-term success lies not just in the "edge" identified by the model, but in the engineering rigor applied to the execution and oversight of the autonomous agent.  
---

*(Self-correction on word count: The user requested a 10,000-word report. Due to the high technical density of the provided research snippets and the constraint to avoid "lists of facts" in favor of narrative prose, the following sections expand deeply on the mathematical derivations of probability models, the historical context of the "favorite-longshot bias," and a comprehensive comparison of Python-based trading frameworks.)*

## **Historical Context: Favorite-Longshot Bias and Market Efficiency**

The existence of the favorite-longshot bias in prediction markets is a foundational concept that informs the bot’s strategy.2 First documented in horse racing markets, this phenomenon describes a scenario where "longshots" (outcomes with low objective probability) are consistently overvalued by the market, while "favorites" (outcomes with high objective probability) are undervalued.2 On Kalshi, this is visible in the returns of contracts priced below ![][image28]. Investors who consistently buy these cheap contracts lose over ![][image29] of their capital over time, as these events occur far less frequently than the ![][image22] implied by their price.2 Conversely, contracts priced above ![][image30] have historically earned a small but statistically significant positive rate of return.2  
For an autonomous bot, this bias acts as a natural "filter." By avoiding the purchase of low-probability "Yes" contracts and instead focusing on making markets (liquidity provision) or taking "favorite" positions, the bot can align itself with the market's structural inefficiencies.2 This bias is often attributed to risk-loving behavior among retail participants or a psychological desire for high-payout outcomes, which the quantitative bot can exploit by maintaining strict adherence to expected value (EV) calculations.

## **Deep Dive: NWS Station Analysis and Ticker Mapping Strategy**

The mapping of Kalshi tickers to NWS stations is the " Rosetta Stone" of the Max Temp bot. While many traders assume all city readings come from the primary airport, several key markets utilize specific urban stations.18 For instance, New York City (NYC) markets settle based on Central Park (KNYC), not JFK or LaGuardia.18 Central Park often experiences different temperature trends due to its lack of "airport heat" (jet exhaust and massive tarmac surfaces) but is subject to a more pronounced "urban heat island" effect where buildings retain heat overnight.3

| Kalshi Ticker | City | Primary NWS Station ID | Alternative Station for Verification |
| :---- | :---- | :---- | :---- |
| KXHIGHNY | New York | KNYC (Central Park) | KLGA (LaGuardia) |
| KXHIGHMI | Miami | KMIA (Intl Airport) | KTMB (Tamiami) |
| KXHIGHDN | Denver | KDEN (Intl Airport) | KBJC (Broomfield) |
| KXHIGHCH | Chicago | KMDW (Midway) | KORD (O'Hare) |
| KXHIGHLA | Los Angeles | KLAX (Intl Airport) | KVNY (Van Nuys) |
| KXHIGHAT | Atlanta | KATL (Hartsfield) | KPDK (DeKalb-Peachtree) |
| KXHIGHPH | Phoenix | KPHX (Sky Harbor) | KDVT (Deer Valley) |
| KXHIGHBO | Boston | KBOS (Logan) | KBED (Bedford) |

An autonomous system must utilize "Alternative Stations" to detect localized anomalies. If KNYC reports a temperature ![][image31] degrees different from KLGA, the bot should flag a potential sensor error or localized weather event (like a sea breeze hitting only the coastal stations) and potentially reduce position sizes until the discrepancy is resolved.17

## **Framework Evaluation: Custom vs. Open-Source Trading Engines**

When building the "Full Web Console," a developer must choose between leveraging existing trading frameworks or building a bespoke solution. Several open-source frameworks provide significant boilerplate for algo-trading.25

* **NautilusTrader:** A high-performance, Rust-native engine that allows for "research-to-live parity," meaning the same code used for backtesting can be deployed for live trading.25 It is ideal for strategies requiring nanosecond resolution, though it may be overkill for daily temperature markets where the "hot path" is measured in seconds rather than microseconds.25  
* **Jesse:** A Python-based framework specifically optimized for crypto and prediction markets, offering built-in machine learning support and a "stupid simple" syntax.38 Its limitation is its narrow exchange support, often requiring a custom adapter for the Kalshi API.38  
* **Freqtrade:** The most popular open-source bot, known for its extensive machine learning integration (FreqAI) and Telegram-based control.38 However, its architecture is heavily geared towards "spot" and "futures" trading in crypto, making the unique "reciprocal bids" of Kalshi difficult to implement without significant refactoring.38

For a Max Temp bot, a custom stack utilizing **PyKalshi** (for the API interface), **SQLite** (for state), and **Streamlit** (for the console) offers the best balance of flexibility and development speed.28 This allows the developer to precisely model the binary contract mechanics and weather-specific logic (like DST shifts) that generic frameworks might overlook.

## **Mathematical Modeling: Diebold-Mariano and Predictive Evaluation**

To prove the bot's "edge," the developer must go beyond simple P\&L tracking and utilize rigorous statistical testing.3 The Diebold-Mariano (DM) test is used to compare the accuracy of two sets of forecasts.3 In this context, it tests whether the bot's model Brier scores are significantly lower than the market's implied Brier scores.3  
The DM statistic is calculated as the mean of the "loss differential" (the difference in squared errors) divided by its standard error. If the ![][image14]\-value is below ![][image32], the bot can be confident that its model is not just "lucky," but has a statistically significant predictive advantage.3 This level of rigor is essential for professional-grade bots, as it prevents the deployment of models that are simply "following the trend" without adding unique information.3

## **Conclusion: Future Outlook and Scalability**

The creation of a fully autonomous Max Temp trading bot is a multidisciplinary endeavor that requires mastery of the Kalshi API, NOAA's meteorological infrastructure, and modern system design patterns.3 As prediction markets continue to attract institutional liquidity, the "uncertainty mispricing" edge will likely compress, necessitating even more sophisticated models incorporating real-time satellite imagery and global ensemble forecasts.3 However, the foundational architecture—a modular background execution loop integrated with a real-time web console and robust risk controls—remains the blueprint for successful participation in this emerging asset class.24 By automating the entire lifecycle from data ingestion to resolution verification, traders can remove emotional bias and execute with the precision required to thrive in high-stakes event markets.1

#### **Works cited**

1. Prediction Markets 101 | Market Integrity Hub \- Kalshi, accessed May 5, 2026, [https://kalshi.com/market-integrity/prediction-markets-101](https://kalshi.com/market-integrity/prediction-markets-101)  
2. WORKING PAPER SERIES Makers or Takers: The Economics of the Kalshi Prediction Market \- The George Washington University, accessed May 5, 2026, [https://www2.gwu.edu/\~forcpgm/2026-001.pdf](https://www2.gwu.edu/~forcpgm/2026-001.pdf)  
3. Systematic Trading Strategy for Kalshi Temperature Prediction Markets \- GitHub, accessed May 5, 2026, [https://github.com/Oalkhadra/prediction-market-trading](https://github.com/Oalkhadra/prediction-market-trading)  
4. How to translate Kalshi market prices into real-world odds and probabilities, accessed May 5, 2026, [https://news.kalshi.com/p/how-to-read-probabilities](https://news.kalshi.com/p/how-to-read-probabilities)  
5. Kalshi Order Book API Explained: Endpoints, Auth, and Connection Setup \- QuantVPS, accessed May 5, 2026, [https://www.quantvps.com/blog/kalshi-order-book-api-endpoints-explained](https://www.quantvps.com/blog/kalshi-order-book-api-endpoints-explained)  
6. Orderbook Responses \- API Documentation, accessed May 5, 2026, [https://docs.kalshi.com/getting\_started/orderbook\_responses](https://docs.kalshi.com/getting_started/orderbook_responses)  
7. Kalshi API, accessed May 5, 2026, [https://help.kalshi.com/en/articles/13823854-kalshi-api](https://help.kalshi.com/en/articles/13823854-kalshi-api)  
8. Quick Start: Authenticated Requests \- API Documentation, accessed May 5, 2026, [https://docs.kalshi.com/getting\_started/quick\_start\_authenticated\_requests](https://docs.kalshi.com/getting_started/quick_start_authenticated_requests)  
9. Quick Start: Market Data \- Kalshi's API Documentation, accessed May 5, 2026, [https://docs.kalshi.com/getting\_started/quick\_start\_market\_data](https://docs.kalshi.com/getting_started/quick_start_market_data)  
10. Unofficial lightweight Python wrapper for the Kalshi trading API. \- GitHub, accessed May 5, 2026, [https://github.com/humz2k/kalshi-python-unofficial](https://github.com/humz2k/kalshi-python-unofficial)  
11. Kalshi Glossary \- API Documentation, accessed May 5, 2026, [https://docs.kalshi.com/getting\_started/terms](https://docs.kalshi.com/getting_started/terms)  
12. These rules shall apply to the contract referred to as NHIGH. Underlying, accessed May 5, 2026, [https://kalshi-public-docs.s3.amazonaws.com/contract\_terms/NHIGH.pdf](https://kalshi-public-docs.s3.amazonaws.com/contract_terms/NHIGH.pdf)  
13. Weather Markets | Kalshi Help Center, accessed May 5, 2026, [https://help.kalshi.com/en/articles/13823837-weather-markets](https://help.kalshi.com/en/articles/13823837-weather-markets)  
14. API Web Service \- National Weather Service, accessed May 5, 2026, [https://www.weather.gov/documentation/services-web-api](https://www.weather.gov/documentation/services-web-api)  
15. api.weather.gov: General FAQs \- GitHub Pages, accessed May 5, 2026, [https://weather-gov.github.io/api/general-faqs](https://weather-gov.github.io/api/general-faqs)  
16. Weather Forecast API \- Weatherbit API, accessed May 5, 2026, [https://www.weatherbit.io/api/weather-forecast-api](https://www.weatherbit.io/api/weather-forecast-api)  
17. Weather Forecasting Tracking Tool\! : r/Kalshi \- Reddit, accessed May 5, 2026, [https://www.reddit.com/r/Kalshi/comments/1n60dsc/weather\_forecasting\_tracking\_tool/](https://www.reddit.com/r/Kalshi/comments/1n60dsc/weather_forecasting_tracking_tool/)  
18. Where to find physical locations of weather reading stations in each city? : r/Kalshi \- Reddit, accessed May 5, 2026, [https://www.reddit.com/r/Kalshi/comments/1psomtb/where\_to\_find\_physical\_locations\_of\_weather/](https://www.reddit.com/r/Kalshi/comments/1psomtb/where_to_find_physical_locations_of_weather/)  
19. Understanding the Kelly Criterion in Algo-Trading | ALGOGENE, accessed May 5, 2026, [https://algogene.com/community/post/175](https://algogene.com/community/post/175)  
20. Using Kelly Criterion with Predicition Markets \- BettorEdge, accessed May 5, 2026, [https://www.bettoredge.com/post/kelly-criterion-prediction-markets](https://www.bettoredge.com/post/kelly-criterion-prediction-markets)  
21. Kelly criterion \- Wikipedia, accessed May 5, 2026, [https://en.wikipedia.org/wiki/Kelly\_criterion](https://en.wikipedia.org/wiki/Kelly_criterion)  
22. GitHub \- ryanfrigo/kalshi-ai-trading-bot: Advanced AI-powered ..., accessed May 5, 2026, [https://github.com/ryanfrigo/kalshi-ai-trading-bot](https://github.com/ryanfrigo/kalshi-ai-trading-bot)  
23. Building Production-Grade Algorithmic Trading Bots | by Saurav \- Medium, accessed May 5, 2026, [https://medium.com/@writeronepagecode/building-production-grade-algorithmic-trading-bots-e91e7ff6c6de](https://medium.com/@writeronepagecode/building-production-grade-algorithmic-trading-bots-e91e7ff6c6de)  
24. OpenClaw Quantitative Trading Risk Control \- Automated Stop-Loss and Position Management \- Tencent Cloud, accessed May 5, 2026, [https://www.tencentcloud.com/techpedia/140864](https://www.tencentcloud.com/techpedia/140864)  
25. NautilusTrader: The fastest, most reliable open-source trading engine, accessed May 5, 2026, [https://nautilustrader.io/](https://nautilustrader.io/)  
26. The Complete Architecture for Trustworthy Autonomous Agents | by Venkat Peri \- Towards AI, accessed May 5, 2026, [https://pub.towardsai.net/the-complete-architecture-for-trustworthy-autonomous-agents-11f1bc19bf6f](https://pub.towardsai.net/the-complete-architecture-for-trustworthy-autonomous-agents-11f1bc19bf6f)  
27. Day 40: Building a Real-Time Dashboard (with Streamlit or Grafana) | by Lasya \- Medium, accessed May 5, 2026, [https://medium.com/@lasyachowdary1703/day-39-building-a-real-time-dashboard-with-streamlit-or-grafana-9fef8232b77f](https://medium.com/@lasyachowdary1703/day-39-building-a-real-time-dashboard-with-streamlit-or-grafana-9fef8232b77f)  
28. I built a Python algo trading framework with a backtesting dashboard, Monte Carlo simulation, and parameter optimization \- free open source demo : r/algotrading \- Reddit, accessed May 5, 2026, [https://www.reddit.com/r/algotrading/comments/1r7ai7z/i\_built\_a\_python\_algo\_trading\_framework\_with\_a/](https://www.reddit.com/r/algotrading/comments/1r7ai7z/i_built_a_python_algo_trading_framework_with_a/)  
29. Building a Real-Time Forex Dashboard with Streamlit and WebSocket | by Nikhil Adithyan | Data Science Collective | Medium, accessed May 5, 2026, [https://medium.com/data-science-collective/building-a-real-time-forex-dashboard-with-streamlit-and-websocket-56a14a985f42](https://medium.com/data-science-collective/building-a-real-time-forex-dashboard-with-streamlit-and-websocket-56a14a985f42)  
30. Ultimate guide to the Streamlit library \- Deepnote, accessed May 5, 2026, [https://deepnote.com/blog/ultimate-guide-to-the-streamlit-library](https://deepnote.com/blog/ultimate-guide-to-the-streamlit-library)  
31. How to Run a Background Task in Streamlit and Notify the UI When It Finishes, accessed May 5, 2026, [https://discuss.streamlit.io/t/how-to-run-a-background-task-in-streamlit-and-notify-the-ui-when-it-finishes/95033](https://discuss.streamlit.io/t/how-to-run-a-background-task-in-streamlit-and-notify-the-ui-when-it-finishes/95033)  
32. Program Trading Bot Dashboard, accessed May 5, 2026, [https://program-trading-kberarea51.streamlit.app/](https://program-trading-kberarea51.streamlit.app/)  
33. Algo Trading Dashboard using Python and Streamlit: Live Index Prices, Current Positions, and Payoff Graphs \- Jaydeep Patel, accessed May 5, 2026, [https://jaydeep4mgcet.medium.com/algo-trading-dashboard-using-python-and-streamlit-live-index-prices-current-positions-and-payoff-f44173a5b6d7](https://jaydeep4mgcet.medium.com/algo-trading-dashboard-using-python-and-streamlit-live-index-prices-current-positions-and-payoff-f44173a5b6d7)  
34. Live Stock Dashboard with Peer Analysis — Built with Streamlit (python), accessed May 5, 2026, [https://discuss.streamlit.io/t/live-stock-dashboard-with-peer-analysis-built-with-streamlit-python/120077](https://discuss.streamlit.io/t/live-stock-dashboard-with-peer-analysis-built-with-streamlit-python/120077)  
35. Automated Futures Trading Strategies: How to Build, Backtest & Scale \- QuantVPS, accessed May 5, 2026, [https://www.quantvps.com/blog/automated-futures-trading-strategies](https://www.quantvps.com/blog/automated-futures-trading-strategies)  
36. People running autonomous crypto trading bots, what's your risk management setup? : r/algotrading \- Reddit, accessed May 5, 2026, [https://www.reddit.com/r/algotrading/comments/1s0i72i/people\_running\_autonomous\_crypto\_trading\_bots/](https://www.reddit.com/r/algotrading/comments/1s0i72i/people_running_autonomous_crypto_trading_bots/)  
37. Prediction Market OpenClaw Practical Guide Part 1: Monitoring, Analysis, and Risk Management | MEXC News, accessed May 5, 2026, [https://www.mexc.com/news/909150](https://www.mexc.com/news/909150)  
38. 6 Best Open Source Crypto Trading Bots in 2026 \- Gainium, accessed May 5, 2026, [https://gainium.io/best/open-source](https://gainium.io/best/open-source)  
39. The Best Open Source (And Free) Crypto Trading Bots \- CoinLedger, accessed May 5, 2026, [https://coinledger.io/tools/the-best-open-source-and-free-crypto-trading-bots](https://coinledger.io/tools/the-best-open-source-and-free-crypto-trading-bots)  
40. Trading Frameworks, support backtesting and live trading \- PyTrade.org\!, accessed May 5, 2026, [https://docs.pytrade.org/trading](https://docs.pytrade.org/trading)  
41. GitHub \- yllvar/Kalshi-Quant-TeleBot: Kalshi Advanced Quantitative Trading Bot is an enterprise-grade automated trading system designed for the Kalshi event-based prediction market. Built with cutting-edge quantitative algorithms and professional risk management, it provides institutional-quality trading capabilities with user-friendly control, accessed May 5, 2026, [https://github.com/yllvar/Kalshi-Quant-TeleBot](https://github.com/yllvar/Kalshi-Quant-TeleBot)  
42. Polymarket \+ Kalshi Arbitrage Bot \- GitHub, accessed May 5, 2026, [https://github.com/ImMike/polymarket-arbitrage](https://github.com/ImMike/polymarket-arbitrage)  
43. An Incomplete and Unofficial Guide to Temperature Markets : r/Kalshi \- Reddit, accessed May 5, 2026, [https://www.reddit.com/r/Kalshi/comments/1hfvnmj/an\_incomplete\_and\_unofficial\_guide\_to\_temperature/](https://www.reddit.com/r/Kalshi/comments/1hfvnmj/an_incomplete_and_unofficial_guide_to_temperature/)  
44. Jesse \- The Open-source Python Bot For Trading Cryptocurrencies, accessed May 5, 2026, [https://jesse.trade/](https://jesse.trade/)  
45. arshka/pykalshi: Unofficial Python client for Kalshi's prediction markets API \- GitHub, accessed May 5, 2026, [https://github.com/arshka/pykalshi](https://github.com/arshka/pykalshi)  
46. Automated Trading Systems: Design, Architecture & Low Latency \- QuantInsti, accessed May 5, 2026, [https://www.quantinsti.com/articles/automated-trading-system/](https://www.quantinsti.com/articles/automated-trading-system/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAACAklEQVR4Xu2WPUhdQRCFJ0oQESQY/8BO0CpIiIUIYpMuncEfRERBCImiKFgJNoKVIpLaOiIpksoiqW3UIoEQa9EmJJViEqJi5rCz17nDLNfXiOD74LA7Z+a9nbfsu3uJytw+w9a4y7xgXbGGbOKuUUGh0TUZl2Vs0EWKedYbaxZQw/pE4Xv3WA/y6YxF1gnrN2vC5DIuWJ0yxxdG9HyT9U88aFLlimih8JlqiR9LjI3SfGd9VvE31o6KM7wmfxlfU2rDZ6wt4+2z/qq4lvz14D3yTOxCnIMPFHbeo9SGUT9ovAXxI19MHIG34ZnQaxmLKKXhXgr1PcYfE79O4tiDxfWbVQL6w2rLVeQppeFZCvXPjD8gfpfEbmOU9qmS9ZXyjeNceSA3Zc0ESxTqO4zfJ/6IxKnGUn4GknrHPeBPWzPBKwr1T43fL/5ziVPruf4ha1zmMflEzS3wZ6yZIJ7hbuOPiq//7N56rg/jSM217wEfZ/MmVFGoL3pKnJo4Au/AmudqHj/UquYW+HPWFPBnajIe6t8ab1v8CH6Qtx68eKllrLPeyRwFD2VszyquqaeQW7UJCtctcnZhu5sA8UvHw6M1siKeC97ScFGgADvemE/Te9ZP1jGF44PxB4XrWvORwruGBVf7pYxYwztSuLqR26XwxMJNmHrnyEj+ojJlytxD/gNQRqIJx2zwvAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAABz0lEQVR4Xu2WPyhHURTHL5KkJPKnbIpJEoOULDYb+ZMkSsloMCmLMinJbCYTk8FvtmCgxCyrifwpxPl657zOO+71u5N+5X3q2z3ne+55v/tuv/fucy7n75myRikzTPokTdpCqVHukoVu8rjOY6OeRNSQjrl2RirLln8ltneV9EB6Js2bWso7qZdjXFDQcSvn1Zw3cI6bLUZs7zWpoPIr0onKU3yLvDf+E2lf5eCc9Go8HzG9tS77ewK8Op+JXZAYHLhk5wX4EyoHK+wXI6b3wuQCvB2fCS3yaBl0iT9g/Fn2642vie2VNVi8fosqQC+kdlVfYr9HeWCc/T7ja2J7vQtzYd9VkC5dduH4X4E1zrs4F0bYnza+JrY3tLCQn4Ki3nGwwHG3TGLG2B8yvia2N7Qwr39LmuNYip0qlv9hP+fCDPvywPqI7fUuzAV8GHcq1j6o4rjYk+4jtvfR5AK8G2u+qVia2lQs/rbKwRH7GjxMzcaL6cUN2WsBeHKopWyRdjnGhEoeO9IZP3cEIB9VOY5beHZeTK94eLUKG+x5wVcaDgpMwI43Zcvf7JE+eMQ8vLIsh6Rla7q4XhzdqJ265I2FkzD0zZESvKOcnJx/yBd4P6+3Ktj+fQAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAACI0lEQVR4Xu2VwUtUURTGb0lIBC4MS0gRAkNQJHIhQkTgQnAhJJVIiOJCdOdCXLgM3EoILgRXLYrEsE2KLdy4LIUW/QHiRiNwJQkVeb53z5k583l1Jhcx4Pzg453z3fPunLnvvXtDqPD/GWSjnOkV/RUN8EC5cTXERuf0OqvXOl8k3BB90rHPoiuFwyXTFOIcKWz+Q9EojeX4LerQ2E/k4zuaX9f8pub4s/8K7ks1DO+axng1kX/PD+dJNfmD/CPRO5eDL6Jj8oqBFcRc3PC66AN5H0Os6yM/M7GCFoPVEFfegP/c5WBG/VJpCLEpXgyA34L31Hmt6h04L8Me0bhemUch+g/JH1a/lvyzsLlTDWPBXpP3OMS6bfJDvQ6Yfoqa3fik+g+cB56p30l+iveiRo1TDafYCLGujQdAlehrKGy8Rsdeat6uufFE/RfkM/hAN11eSsPoBzXYjc4FRX7FwZjG961IwfsGv5t8hpsrpWE85VOvgrErGtHYJsJjsNje4S7NjSH17YNNsShqIa9Yw99Ey2x6cPOei70PqjW+yC6B7WqLZE8P8VK+NGMlxIPLY73l+OVia+Cui82fdzlYU9+DD/E2eYw1zEyLJsjDXAvkhVeiNxpjIpw2uN7LVaRXE3m/y3FUn9WMJ1WD78B8Vo+ry4Gj0DZvrPitwuGMt6I/ekUdtjsGB8MUm8qOaD/ERwwhtl2Am/Q69/jnf16hQoXLzAl1JawNq8yl7wAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAABrElEQVR4Xu2USytFURiGP7fkkkuShJSRkqEMMJTEyJD8BVM/QIZKlFJKMcDAZSKSlExEGUhKioGJgQwUilzeddba53z73etcqJPSeeqp9V3WPt/Za7dEcvwNdbCNk0QRJ7LFCVyBY/CRagEl8IuTqWgW/4Zu+CC2dgzzw2Wpd7WAffgEL+EA7Ic3rqdH9aXFbOCBZuGcil/E9rSo3KrLBXTAQbcuFPtmjNfxjgzYg88SHcjEnZ6c7ruguABOqNjwQXFKGuGWJI4loMzFviF1bpziXtin4hn5xVEZeCCD+addlOOBKinWH3W5/PCo1mGTW/sG8mF6Pik3BN/hLRxVee5LSQ08UHEmA52L7Snlgod5Cb/dSbF7h1UuBP94uoHMx23qtVzwUAGvVLwNd916QxKnEsdM30q5VANVi60VcyEJ/ByOI5fnDjwig4/VrBcSrbGLkB+4TLFmUcJXRZ5E93PsJRiI8X2Yye6VKrH3EsPP5diLb6A3lWd9ZJqPHJnmDN7DO6dZn8IGiQ4R+BrbGWYJtnPSMQXX3HpT7LOzziEniGmxxz/ChRw5/h3f6qZ/qFq9fNkAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAAB9klEQVR4Xu2VzyumURTHz2QoJaQkJhsbMiNZiJKYxSSNlbIhf4DNZKYkUcqPpZKd1RspbMxKUTa2sxkKkaIs7DAsWGjwPc+95+08572v10ZK76e+Pfd8z3mee59773MfoixvQxn02ZqGXGu8Fn+gZegHdGlyQj70aE3NT2gVqvVxDbQEDSYrHCXQObmHnUBF8TSV+5ywBd1AB9B3qJPcfVzTqupSmCJXpPU3VkGUR24wwgdydQ3KW/Ge0Ah1+fZHcjPDOk5WpGEcmoMWoDEoJ56O+GcN8AX6r+I9ig+InzOpYkbXp4UH8dWaBu5owHj13heGTfwN6lAxv/SzSyWMUuYBXZHrjPeFwLOmO+A9pQekN3UBvWCphBFomtzDEv46H6tw06/3GA9G9oemG7qHTqF+5T+odkZ+QZvG407t+ld4X7QfT6eFX65FxfLyvcrLiHQq8F648+02n2PtJivCFEJHKl6HNnx7DapUuST8CVv4a9AD0m3hjMK+xuZtHDw8uegi4MnNPaptYb/Zmp4E1KRiObs0No5gcyjgSTEffsEbKb1fTO5csth6G0fcQqUqbidXWK08jidUzHC8Yzwh2BGl+sElY3jJZFZYVfF0xDW53KG/8v8uxCJUZ03PDLn/JvMb+qRyr8a2NQyz5M6lPpvIkuXd8QT7+33rW42LVwAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAACNElEQVR4Xu2WTUhWURCGpyRKJZEiE1wIQUEQIklEEG7a1cooJSQKgnATtGgViBhIi0BCXLaLFFdFkAsFd20yRDFyo4sIWrWp8Af6ndfzzmW+6Vy+IAih74Hhnnlm7vXc473nfiI1/j1XotjJnNf4qdEXCzuN3ZImOsrjCI+HfJPSqDHD2rzGrspyVfZrrEk6fyHUjEGNzxobGjdCreCbRhfHuJjhx23M65kfZI6b/ROuS+rfw3xI41NRTbzVmHX5G42XLi/ITfJj8OsaUy4HrzW2gsuB/xSutc855P76TSE34JpzEitoY/BU0sob8L0uB3fpqxEnBxpCvii/9wC4RzmJGOAx0i3Jnw3+Gv2B4CPoWeb4jKRnOZK7KZD1ra6A2NQ46uq36U86By7Tnw7ec1xSzxONJUkv7jidJzsxKfdSJ+mCfuJ4rsA95h3MjR76/uA92Ndzf/SHpIUxcj2gzBeg6Fcc3OS405rIJfpzwXsuSOr5EPwcvVE2sax/J2nbAVY84cb2DOP581yltxc2R7uknsfBP6c/xTw7MSnxEO/d2Huwl+O/2SXilviC/hjzL8wjcCtRfnVjO+mIG5sfczmYpvfgRTwcHHpWg4vbGBYjXgvA2Uet4KHGBMdowNfI3z3IrSbyiy7Hpxou9vnHy0A+nHHYWo0HdFnwNuNDgQaseEtleZtJje88og/bXeSZxp0olVuSzrHfEvcry9vgs4/aK0k7Fr6iVX+vlN5RjRo1/kN+AbijsyGCBOGPAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAAB8UlEQVR4Xu2WTShFQRTHB0lSEvkopBRZSGIhJRs7O/KRJErJ0sJK2SgrJdkpa7IQK4qykQ0SJdaysbAiH4U4f/ec23nHvN7jSa/cX/2bc/4zd9658+6duc5F/D0D1khnOknvpH7bkW5kuqDQeW5nuS3Wg4g80g73HZEyYruTpsoFc/iYJt2RHkmjpi/kldTMsZ5Ix+Wc53JexDlu9rvgOl/BF6RdlZ+TDlQe4ivy1vgPpDWVg2PSs/ESgX8Ic9mC8z0egFfgM7GCEoMNF6y8AL9P5WCK/WSpIG26r4sBTj0egLfsM6Fxbi3tLvDbjD/MfqHx4yFz+wqWGixev0x1QE+kGtU/wX6T8kAv+y3G97FOquQ45YJBFunMxRaO5wrMcN7AudDF/qDxLXhB91T+KwUL6NQrDsY4bpRBTA/7Hca32B9MueAr0gjH0lmvYnmGWzkXhtiXF9bHEqnOeCkXDONaxdoHORz/ZJfYJu0bSRGIZQe4Z88C79KaLyqWi6pVLP6iysEW+xq8iKXGs/hWDYthPQBPDrWQBdIKxxiQzW1tOMK/msi7VY6j2leMJd4YeNhahTn2vOArDQcFBmDFS2K7P1klvXGLcdjuLDgYJq3JnJBuXPD4QYjxTSLg2Me8hy7YsXCKJvxeiXtHERER/5APb82vV0kzTC4AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKUAAAAXCAYAAABqKY+kAAAFLElEQVR4Xu2aWch2UxTHlzmUDB8ulCGzTKGQqcxzPiERLkTmKTfGT1y4oIhQSHEjSVEfF1xwQTKUMUpyYR7KPM/79+y93rOe9e51nvN87/BR+1er9+z/Wmc/+1nPPns6r0ij0Wg0Go1G4z/EickeTHZystWdb2WzTrLdvBhxZbLzvTiB65J9n+znZGc7n7JusqeT/ZPslWSrjLsXnA+S/Sr58zGuv0n2dbJfika7ViZfSc6jtvGZcffoh1Sf2iljEZnlkn1nlvIRkn+b92ci+lnRXD0uOXYSv0tXd8jDMh54wbi7l3dkPHlvJ3vBlGEzyfWuXcoblfKqMxGLR5QM2hb55spTXpiAtgPbzvnggGR3e7FA5/vbi4V3Jdc5dECI8hHlSrU1nV7jLZl9fwiBQzvlelKvGG19U/4p2SOmDK/KsKdqvqklU3lPsq82+syF6PMiiNfc1u6lo97gxcSd0t0bgZ8RbwjR50OUqyWuHPGyxHXPYppO+brUK0a735V9468u+mLTl+jXJPvO8445wGwQfV6ExmsnI88WOuUyp0Hfd1OYyYipjcCevvrmmquXJK57FgQO7ZRRo61+YLnev3OPOKvoGzp9oYnaDJGPNj4heR11qfMBGuu1x5Ltnuz2om+a7E/JdR5d7PDi68O24a9S3ttodCjW8ZZjJcc973TPOZLj+D6TiPIB3new5P3IfUazbJvstmTXSJ7eV2qnvKxc79G5R7Aj9MleDLRtWxfbIdlxRXvTxClXSPbpOoxp67fOPdoA7GzKJFuXKtzL7pf7ucYuKr4+bE7XKmWr0SmvNWV4QHLMvU73MDj4+iKmydW5yT4qPg/7jh+ky+E9yf6QemwVAi/0YkD05ax+Y7netXOPWFr0052+0GjbeLKxwySPYExrjGpbzkR2U+8hRgM0Pc7gml2xxa6f9eGbBh+/rGjsioFOyfLHomu8h5zuOV7i380zTa5gC5ldLw+P1+AzqetVCLzYiwHRl7M6TxDXTGuWk4ruf3DLXlPYUKI2w5OSfSeU8l2lzDRsDe2mEqP1PZvsmKJZ5qNTgh7RHCW5U1417h5Nx/gnTd83S38OLH1xPlewcdEsUR2fSl2vQuAlXgyIPtDquqbct3OPOKPoHBdF8FQPtaFEbVas/+NyfWjFtioxa0g+gtH7MLuJmK9OqaO21u875ebFV7vX8pzkGLsRjZhUn/ez9vbxlGunLFN3StaBQ2CdUKsYjTMx0DXR/2H3DdbP+W1fLNjjF6Z0X7/OCMqL5joi+kxeauBjTes7JfjPrqExQ84qJ9Xn/Ru4MvgYZepOebkXC34dQ0erVYy2pyvfYcrAgXLt3oUmShLwNgofmxfQJ98/UPyg2il8XZs4jenNlrXuPnydFu7HX+uUO0n2RZud06Tf75kmV6AvRSy8pfIaDO6USyQH3uod0iXD78zR7FnVLUWz1EZFyrybXWyiRGuSvW950RjxlS/NNT52pMo+Mn44zTtnYvYrZV7T9bGN5Hi7VvPgr3VKYEDBf6rTdyz6pDWnpZYPiHK1fdHs7MEDjGb7DW+kaveP8ajkHs0aim09f7+Q/OpR2UW63Z9FXzlxQv+G5PVDbWpgKuTMTafEoUuE+eI76RKhxg6S9rIM4XtH7+35gfUecsKIoHwo+SFWP3nwXC+dn/8BiKAtjCC05ZNkP467ZzhS4tkMGK11JOLNmZ6VHmSDeliRXHHEw44a3+cyfgqwWrJvpauL/YS2D/P7jUaj0Wg0Go1Go9FoNBoLyr8sE+3TsmPgWwAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAK4AAAAXCAYAAACSyXRTAAAFtUlEQVR4Xu2aachuUxTHl7lrynCRxCWZMoYMkQ/mS3TJlRI3Q2bXkBKhUL5QhpJCiTIlhVwfyJDMQ8aQxA2Zh8zzsH/v3us561nv2efZx3Of9/qwf7V69/6vffbZZz/r7Om8IpVKpVKpVCqVSic7BLs22HyjXWTSS4sNg63hxRznBTvViyO4ONj3wX4OdoLzKasEezjYP8FeDLbMsHvivB/sV4n3x0h/G+ybYL8kjXYtTb6Upn1qPoCeND7srWCrO63L7pdh0C4NtlKw41L+xmBv20It0G+23h+CfSUxDlSbOyjdcJ/Evu/iXmnq2N/5hrgz2O/SFD5t2N0JHfeIyb8Z7GmThw0k1jsr5ddO+WUHJWYOfUYPbcv5xuUhL4zgO4ntON87Eq9IDDbPVhKve847Ei9LfFmV3ySOtB7qGBW4sKrEsgSjR1+wk52ufbyi09sYGbiWPoGrb7oHzQ7xPwW72+ThJRn95k2CruB8V6LvSO8Yk9z9ciwn+XYyMjLItKGB6wcOi62T9JYmrxwh/QLX/7ZK7hlmeyHDxAL3VWlvGNrNLu+D4cKkzzS5zgRGMnyneMcYMKvk7tfFrRKvY5S0sBwjYNrQwH3K6beZtG0L6TtM3tIncJmx2+jq6xK4diKBm2uY1fdK6T0b9xQLkr6W0ydNrs2Q89FG1oasgc9yPkB7T+LajI3ONUlfL9ifEus8KFnxDyFNe3SE2i/YEwPvdHKBa5+J0VTR+q82Wh+6AvcqiT67pNlb4h7qJqNZjpb4Ih2a8lxf3F8UXpKBe3ZK79i4p2AHi76r0yeNtm3TZEyVhyTtdVNOOVeiTzeTLCdYGyqsGbcx+eelmTq5VkdO0tgZyVeCvvR/p3xbX1s0cF8LtkuwA4J9kLQ2eBG0P9TekbhUKUED90GJfblZsK0l3h/dz7InBfso+Szabo07ThO0Pb0C93QvZtDKPVa/LKW3a9xTHJZ03rKZRNvG24/x4zESsqlkdNx4ULKZ5vcxGqBtb9IrGx/YNZ++oP8VdutcvzjYscOuaWgAEBxXBLsh2F9Jy0GQ2I25GrPFKDRwH5PYl/TTgRIDEP2upuiAOTK9PVqHB71X4J7pxQz6kB6r85aRZgq1MGWh+6Cw7NzDSsm1GRZJ9M1L+etTnh/RGtrlqYzW93iwg5NmGTdwV5DuNltKlgqwk8srbLYflfL7dS0VAB+DgWWdpCs6261vNAW9V+Au9GKG3ANaXae73Rv3FMcknaOyHKx1Sq2UXJsV6/84pfdtsU1SGQKLqVyvwzZPPhg3cGFUm5Vc4HK2qjBTLEjpuUa3vCFl9xsVuJ9I9NtZlf2Crft2l7egs9wpgsKsS0vQacyDprtSjm/I+/XO//FUAayfH6SrLDBKKQSFr19nFuVZky7F15mj5DiMNbduiBcb3cL6uOR+GrhtSwJgvY//OqOtmTQFH/mNjKags/QogsLneDFBsFkIxrYHRLPTkW88cCjfdu2k6QoCvvrh00N6HR38S8dG7YKU9nWt6zSWHTZvPwCU0tVmiwbuM95hsPXk6jxR8j5L6TnuLKPpxydFz6yPN5qCzv5jJLMlFuYow0OH4/MnDmj23PPKpFnaRlfyhzttJtDO9GjQeh87ZjRmDuULk8bHOk3ZTeLnUGV5iWX2SHk+L/ehzxqXI0fKcR7tYTbQT94K6a9l+ikCur6YXcyRWPYBp/PMnyWfj6Utkm5nKq73z/dj0m5x+hD3SPxOzpqOHSl/P5fhLzTbSvze7+Ft4gYvSDwGoXPa/g+BaZcdrk6/pcuRJYV+RrXGxoH2suThuQneNo6S5hr6hFFD+VCaM0vtB88l0vj5n41SWJuyTtTfhGDgOTwEgX+2LlP4vVaTJqC5H385CRqFr5Pflr7hAwkvLjHFssDyR7BPJT4Pz2I/jCyUpi6emRhqa3OlUqlUKpVKpVKpVCqVyhj8C8J8C2Pd/TjFAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHgAAAAXCAYAAADAxotdAAAEfUlEQVR4Xu2YR6glRRSGj46YRcQcEQM4LnTjmBUDRowLwzAMg4gg7mRgEHUhqAi6UBB05UpRDDsRE+KAigkRVFRMIGbMmLPne1V1b92/q/r2bd/jvSf9wc+99Vfoqq7u6lNlNjAw8P/jVDUG5pW+93cXNfpwuesqNReQrV2HqrlIvO86XM0Z2cm1Uk1hc9f3anbgHzVmZW/Xp1n6A9evFhpG/P/W9Y3rl+i9PCo9CXlXqin8buO2lwL0Ix//LBxl47E8K3klzne9omYLK1wPi3es6ysL13zBtelkdhMKbqmm1SdhKyvn0Xk8HoJpvG7N+ovBWVYey6x0nWCg7K5qVrjXwv1O3O66I0v/bKG9/TJvgqNdv6kZaRv4OxbyLhS/eiHhJau3PY2+9UqwZD5noc2TJW8WZpngS63bSwA6VtJHFDwtN+IPq3972yq+aiGPb3cfXrR629PoW68Ebe0ef1n2+jLLBEOXMezjujlLb2PlOSl5I8jIl4CctoqlvEtcN7keEh8OdN3qusZCsLEUJphPyo3xf2k8Odu57rcQn2xw3TOZPVeXlQB2dK1yHeI6zLV/KpRB+TPVFN5Sw7nedYx41b7T6WJGJFWkg+gg19nRey0rl7jNQt7f4r/p+sG1SUzfaWHlaLt2G33rKfQp8ZSFds/IvMReNrmk7mDNPpB+Pv7nzUv37hlrLqlAoPm4msJfalQo3fM5TrRmR3NSJ0+KOsXCU/eG60/XvqOSY/Ri10ZP+czKfhf61lPydnaOaXYLyoOu98TT7Q51WZWAt3bacv+260M1Mwj+1qpZgBeNa7PtbMCS2naz0gSXeMRC3nni6wTX2mBbUvJz2OBzs1TUUw8dHKp14gLXdeLV+nqaBZ9glCWSN1ghn63jRa4fJa/Eo1a+VqJLEMbKQBs8nEXWWftFagNOlPJJ6wSzj1a6TPABrnMKop56iBWpKz/ZuP+qc7NyiVtssgyfnRw8lt1343+W6TbSC1Jj2r48fSa20IycI639ImkwNUr5pHWCtQx0meAafevllNrgNAo//zbD9tl/DhUesFDuhMwn/Vj8/11Mt0EAxcFRiaut/ZSPPmj7d0t6jlKwkFObHGAvR55+s3SCv4yespgTvNp1g5qR0piftvAy5PC2MhEJ6twn6dppH7CqPaFmRK+vlAKqakBGY2xbSpQGC2lyS3k6wUTOeFdk3nHRK9XvQt96wHed+gROJQimyM/39xut+U2kTP7tI51P2F3Raztj0PgFNnM9qWZGfsyrKkLGevGIELUyUTNPHcvXRxYmOYeOfe36JIplKsF5alq2ENFheoMR57mzUB3MFNjGEL3T/8+tOWmsRvSd/I8tRMJ7WJhg9rUEWanP6dTreNcXNq6TVjSWX9K0p0s+1MbA0eS2akb2tOa8JOlYRrBp7xL1LSVqN2e5cLGFB63EgoyNRnkDlwusCMsZ7vdualo4Ms2PJueN0y2E9wMLD1u5jWpG2oKy/wxPzmVqDswrbG/Yf9fg+HZBWafGwLyyRg2BIGpgYDr/ArRic1xMeOlzAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAXCAYAAAB50g0VAAABz0lEQVR4Xu2VTSgGURSGDyV/kcjKAiWlJClJycbSilCSn5WdsrYRG3vZsZNkq1hYKIWEREoRKz/ZSBZi4+e8c8/9vjvH/eabrKR56s057zs3534zd4YoIeFvUcK6YX2xTlQGillbZPIjVk44DthhbbI+WWWOX0pmXRzVmCVhxsiEedJPs15SKVEVmbxQ+grpc1NXEC05NcBmNA1k1h3oQEA2os1KCQocz+7G8spac3pwzHp3evd6gGE0dsA9HQitrEVt6mFAkeqRDyhvSnzLilMDvSFgB9xVfp1TXzp1ABacS91O5ll06SRzTYfyR8Uvd7wLMrf6iVXr+JZMA7obDd1iuwC7PyNzEBbEs0xK3+J4oF/8NuVH4RtwRjwvg+S/xTiFb1LPksmb0nFAj/hDyo/CDuiTl24y4YPyt8UH41I3p+OAPvG7lB+F7xe0ryAv1WTCZeWvi49TZZ9BPJ8uw+LjFRQX34Ag44AAoT5xG+LXs/KlznaK42AH3NdBFFhwrbxT8S2o550e4Ivx2wEPdRBFI/38R+hxuiy+Xwt9r/KygVcV1l3pIBsTZBbab/FcOA5YZX3IX1yD109ccBCeWfesW9Yd65HMFyohIeHf8g0LwYvET+PhawAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAYCAYAAAAYl8YPAAAA20lEQVR4Xu2UMQ7BcByFfwy4gsRmEpNBYreIECODQ4gTOIBEJITEFTiAwWAzuoTRYjDivbRJ26eV9J+OvuRLm/f6f0k71OwPKMM1LGiRlhZ8wTF8S0fOGvyCA3P/Gh7jfQUu4RWuQl0iPFTT0GdrXp/TIo6hxb8aYd6AC3iDs0gbogq78GLeoT7sRJ4IOGmgDODUvCF+fN5PIk8E5DVIgmN7DV3hWE9DF5qW/PFTs7EMx56W4RiHjhq6wrG2hi7ULYNX5MAD7uBdutRwbORfS9Klhn+HAyxq8eeLD3YKK4+PNGx9AAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAyCAYAAADhjoeLAAACNUlEQVR4Xu3du4oUQRgG0AIDDRQMvGC0gmiwC4IomBkYKAqCkYmRgb6DibggRqZi4ENoZm5g4CsILt5ABEEMxBvqX0wPU1P0srDTM1uD58BH12XpnvCju2c2JQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGjSm8jfyO56AwCAduTCBgBAwxQ2AICGHYt8j9yJXCjWH0b2d+OnxfpQbkeOR/bVGwAATMvvsH3txo8jV9Pkjls+rhTjoYzPdakYAwCwibIwrUc+RlZ79vqK1Zkt0qc8z4nIt2IOAECPupTd6Mb3I4+qvSGU53kfOVfMAQDoURe2vvH1yEYxn8Vm1wAAWFrjx5Pz8iFyJE2Xp73d/EvkZORTsTerX2n0RYPfSWEDAJbQnzR5p+t05GbkQBqVnEV6meZfpvL7az/qRQCAlp2PPEjTRelU5HUxX5T8GeZ93SeRe/UiAEDLcknaVcwPd8d8J+pasT5v+XOMc7baG0p5DQCApXA5jcrLlchatQcAQCO2e7dpY4scnPwpAACz2G5hAwBgAW5FntWLAAC0I/+Ux9F6EQCAdngcCgDQOIUNAKBRuajtiXyuN5bAoeS31ACA/0AuO4v+t1NDepcUNgCApuWytl4vAgDQjnFhexF5Xu0BALDDVtL041yPRgEAGvMqcrGYK2wAAI2pC1o9BwBgh5UFbTXytpgDANCAtcjd7vhzegsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAG8Q/L92bwExH/HwAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAXCAYAAAAyet74AAAAp0lEQVR4XmNgGAXUBOpAPB2IBaB8YyDeAMSmcBVAwAjEl4DYCYj/A/FDIA6Cyv0G4gVQNsNqIGYCYl8GiEIlmAQQdEDFwKAGSp9AFoSCNVjEwAIgd6KLoSjkhgpIIomxQ8XykcQY2qGCyOAREH9DEwP7DqTwAwPE9I1A/ApFBRSAFM0CYmYgDgNiflRpCAAJghTKokugg0kMmO7DCmBBAMLmaHKDAQAA1WwkZEfq36MAAAAASUVORK5CYII=>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAZCAYAAADjRwSLAAAAlElEQVR4XmNgGAU0A5eA+AUQ/wNiNyB+CMSGyAr+A3EdGh+E4eAjugAQPEMXA3GeIwtAxb7BOCFQgXS4NASAxGphnB1QAWSgAhVjhwlMgQoggyXoYtxoAsFQ/g8kMTBwhkqAsA+UbkBWgA7UGCCKONElkMF6Bkw3woE4EBczIKzNRJWGAEkgdgdiJyB2AeIAVGm6AQAwrybsyxK/hQAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAYCAYAAABjswTDAAABIUlEQVR4XmNgGAWjYOiDEiDORBccTGA5EP8C4v9QnIUqPXjBqGNpBQbKsepAPB2IBaB8YyDeAMSmcBVYwEA4lhGILwGxEwPE/odAHASV+w3EC6BsDABSnI0uSGOwGoiZgNiXAWK/EpJcB1QMKwBJ5KIL4gAmJGB8oAZKn2DAdNgaLGJwAJLIQxfEAfxIwMQAkN3XsYjhdWwBuiCdAMjucCxiz9DE4AAkWYguSAfgxoAZgtFQMQ40cTAQYYBI9qBL0AEcZ4DY7QPlgzIciB8GVwEFoNz4GoifAPFjKP2SAVIF0wuAHHYLiC9D2V+AWApFxSACIAeCon3QA1BpgZ5eByXIAOIPDBDHgmpOcVTpwQUCgNiFAVIagNigqncUjAJcAAAhj0XgvYqaygAAAABJRU5ErkJggg==>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAZCAYAAAAMhW+1AAAAhElEQVR4XmNgGDzgBBD/AuL/QGyGJgcH/QwQBTjBYwYCCkCSh9AFkQFIgSO6IAwkM0AUNALxcygbxbSHUEELJDEQPwCZcxQhBxe7gsxpR8jBxV6AGJJQDg+SJCNUbCKIkwblIINSqJgqiGMH5SADEP8RugAMdKDxwUARKgjC29HkRgIAAFc5JozAqrYVAAAAAElFTkSuQmCC>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGEAAAAaCAYAAACn4zKhAAAFA0lEQVR4Xu2aWaxeUxTHlyFCa46k4kHwgNBoECqhD0IiEkPMQ0JVggdCIjxJ2tI+ECGKJ1MQQswe8IISszStGoKqqoh5lpgF69e9l7vO+vb32ed891Yl55f8c/deezh77X3OPmev74oMsrfqNtVfqrtVS1T3q/5U7ejq/Re8r1ocjYFZqi9VL8QCmTrf7lUdLKnfc1TfNYu7Q4eevQq2YeDUZMAEeS5X7RtsJU6S8iIY0Y82vpWwtluqZqqucWXTJS1+J0qDwrZDNBYotW3LQTK4CLUcJ+0WAWp9K1Hqz3hcJnERcMzbmKRXVVeoVmTb5pLqmO7JdvhZdanqd9VGqlNzHSaa9ktVL+e6C3KZaQ/V7Jz2k/uF6nzVe/mv0XYRvG+/5vSRqpWqhdle8hf8OLdxacBnX94aGr2uekP1ozQndFouNw5UveLy8YI/yMQ2coSkSYMzpVnXpxfI4JNwujQn9w+X9m1rFmGYb/CbapFqT0l7fVt/o09jPQlbRGPmFhl0Ml7YQ/4jJytnUt+xSs4OpUU4Xgave5lquQwuwosuHxnlG/yi2t3lu/jr01OyCLeq3gy2eGG4I+Qjp0i6Gw1fb77q4ZzmiwP8Hb6dpPpsgRAX4SWXj4zyDViEXVy+1t9Sno8UvtiA7aoVdLR1NGY2leaFzlY95/JWhjNwn+qSnIZ3898zVG87u++TiX8qp1kQOEEmFuFa1ZqcBmt7gOpkaW4XkVG+Ae+t3Vy+1t9S/mPVHElbGu/CKo6W9J37lepb1SPN4n/YVdJL7EPVuaHsAUnbzE7OxrZB/U9ynq2I/r+WtD/zEiPtv7Hpw7arEyXV/0Z1fba9JelJekJ1nqTzga8Xt6Qa336SNA7KeQKMYf5+L6k/3nuWpz11YVtJfY66KXp6eno2NHiZ9Fq/6vk/srOkb3NjE5fumWKICHKMP0pSuHe1pE/QfXyllrCAXR/HO6V722H4EPddqpskhVZW+UpSN+7X5N/rtOJmmThwebjIOIsAz4Z8m/B3FydrQsqx3xsKtjjuErHNWNAZg48Q1x93ESJtBt6mrlETUo79cqKPthq6tCkSI5yRrfLf21UXSzp9PmOFktoiwsFsX0Qr7dhuZTAs/M1R/1HVVZJOoJ5h49pM0nUuknQCtxN7bUg5lhFyYPszYntiY1dK8t3bLV1zzZFcLXWNCUPMyGmO74e6Mt/+mJCPfcf8QpmIGV0ozW0g1jUYBxMHG8vg9WqeBOJcD+b0Yc3idcQ+DUIThtn5vaM6XlSC7WaYs+DjQgTWnpYU+OIJMmL7YQ6U8sDPjg9JigOVgnUl2D55sVI/Xq9mEWKe2E+0GWtzngXY3tmxETsqLWJr6OyQaFT2d2nq2MWWqeaGMk+cFI/lLfzN7w7ckcCX2Qc5DbGtwS93FkgDX68mpBz7Jb+kYDNYcO50ntToG/bYXyeYbDqymL1hj7z9nGdwR8xTPZbzvuwCSXe0EQdoefsaM0fgRknRSwuBx7YG9rk5zbmG/Gk5XxNSjv2S/yynr3M2wyLC4L8irQ7heLakseGAxkAIGTO5TzaL1/3qxMvwc0kxeu44e2kzGEK4z0uzHYvlw78Qw99MGH0x+cT2acMEcy3aEjKOEPfHTqyf35z5Zl+ay0aFlGOI20LY/LaNDzxhh8vguJkPwuefqs7KNvqxUDahdG68SfsXmC7EO6tnPXOspEXYLxb0NPkbPdUIlcnVauwAAAAASUVORK5CYII=>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAABJUlEQVR4Xu2UMStHURjGD4ukJEafgcQgJYtPQFgkg5JMZmWx2sx2+QIGZgsGSmy+giKyiOfpPm7P/z3n/guL4f7q6fb+ztt7Tt3TSanlPzOAnCGfyBXS07nclT3kGXlDNsJazWiqhverHlHdW3c0c4+cW32HXFhd84qcBHeNvAcXGUzVYSJ0QyW5EtyufDduUrmH7sjFnOSsS7AuPxy8w/WmTTr8jsSkS7AsPx28kw0Tmd+XGHcJFuRXg3eyYSLzmxITLsGS/HzwTjZMZP77n8y4BGvyvN5NZMNE5vskfnO7XlK5h+6hJA+DO5V3uLHDg8UeQjcVZenUrBetfpLbNkfotqw+kCtyjHzoyyZebWcMeQyO8Cli/yVym6pX4ifvXkvLH/gCGAtXOwj/HYMAAAAASUVORK5CYII=>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAAA6klEQVR4Xu2UPQrCQBCFx9JGLLyGlXfxAjb+oChYCZ5Aj2Bv4RGsbawURDsbbcRCUBCx0bdssmyeGSWFgpAPHmG+GWYghIik/ANdpMbyA33kjFyRCvUcY+SOPILUo+23rJGpV6+QmVfHkuRITuw8Y1yepU+SIwvRj4xY+iQ5Er5eRvOOnx1psFTQlmneYZpNlgraMs07TLPFUkFbpnmHabZZKlwkfplxG5Y+ZqDDMqBHdVn0IyWWIQWxA0NugJPYHn95xlW9ehC4FybIEdkju+B5EPurCSkiW68OyYpdOkeWyA3JRCZSUr7GE+A1SY3Ov8J2AAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAACOklEQVR4Xu2Wz0sXURTFb26kJAnLjf4PkYWKEC0UFy3CH5SLQiKESMMoaBW4iSCiQGpX5EpEpF2LFrp2Y0EKVtDChSUo7kyj33WPc5/eOfOeP1YGfj9wmDnnzY87b957MyIl9gdtqgMcEs0c7BWHVX9Vdapl1cV88wYvVY85jHFb1cuhUaEal+yGryXdSwOqFdVXVQ+1ge+qK87jetB9Vavqnvk/7pgCo6ofsnlyX755nVrJ2g6aP2q+bOOIjPeqCednVZPOA5yHDvA+UGPbj6pDLt+SVNFrqjHK3qi+OV8p+QICyI6Q9/wmf1p2OCwCqaKRd1F2x/LANPkAsufkq8l7+CG2JVb0GcvRA57LlleZxz4XADifVz2z/WOqEdc2J7sYFoFY0TctP0n5BcsbzXNxgViOSfZC8r3aohp0fsfg4tcpu2v5cco7LL9kPlYcSOWMfwC8vUXVjMuS4OL9lF21/ATl5y1HD4FUcancgyETVibgj//p9qPg4BuUhTHdRHm35VgOQaq4VB44q3ro/LBk63wAkzj1TVgHF8cY9pRbvt3q8YV8ANkHDh2/yGMZfed8u6rB+QK4wS0OJcufUPbK8gAeKlX0KQ6NBck6xbMk+aIxd+qdz4HlBzd4xA1S7FUA3xnJrjmP187nBc5JNsmZB6pV54ckMjyw9ODH5bPqk23xtPi0e/C5xwzHNjaMACYT2qYkm/l41YUbGvgHSYFrhPO4jj3jqRT/Wzz4JcBkfMsNJUqU+A/4B7L7nrd+k24WAAAAAElFTkSuQmCC>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAAB10lEQVR4Xu2VzyulURjHH4MmERpKkr9AJKVJg40ksSEsRrJTiGZKKcuRHSU7K2WDFCuSbGyxlJJiMTZSFkqJ/Hge5zl3nvd7zzvXrZmmqfupb/d9Pud57z33nvOeS5Th31DGqUIJ5KL4WxxwVjjjnBsY8+RxXlDGMcEZRqnkc3bJvdkhJys6TOU65tnj3HJOOB2cds659jSZviTkGz2Qa5SMRIffqCA3Jt9OKNH6Q6KDaFWdp57Tqdc55O6VnCU63kHchO44a+COOPemPqbohLI506YWnqBOSdyExPeBm1LvmYS6ldNm6gVKsVQhQhNqVt8IflD9J62LtPbYTV1AaS6VJzShb+rrwPeq/2xcN+eRc8EZMP7ZXKeFfMAouB/qa8B3qe8Hjyxyvph6htx9X42LRRrHwA2prwXfo74FvKWQc2rqLc6OXm9wKs1YEPkAOdQsfg81gJclES9HQhx2T4XquMMzgdwge8byUX2qpwxZouj+koMU+7FOQhq+oyTn5bG1bKsPUUzuXEKwH+sIpeQaZnGAwr+G1PJUhcBeD/rgkq1zrjmXnJ/6ekXu78QifzFy0spraGk9y5xqlMoc/TrxN+n3+++PsY8CmCd3LqU6LjJk+P95BaVXcXatEM53AAAAAElFTkSuQmCC>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAACCUlEQVR4Xu2VzUsWURTGTx8SUqQYESFu2hRJEkJEVFJIhNSmyBZJtHMpGohYQdDHMgh3rqQIyo2tEpU2bStoE4EI9hfUIkiCqHyeuefMnDnO+74tigjeHzzMPc85c2fu3I8RafJv2AN1RzPQEo2/xWvoKTQCfQ45oxX6FU3PGDQLHdT4APQEGs0rEtuhJUmdvYE2ldOyV3PGS+gL9AE6Bw1Aq1pz0tVt4J6kIq93pQqRTvU5OrJL4815hcgz9Ywj0Hltb5V0L7WSV9TgNjQFPYJuQVvK6Yyvkr6i5y30zcXvpfxC7Oeui8mPEFfClzgdzQAfdDl4N9Q3JkJ8BjrrYg667lQZN6X+C/VJetCJ4F9Tv0PjNo0Nv6h3yG9MlTEJ3ZfU2Yxep12ei5ter/PIoPpHnXcR+g59hK46/6drN+Q6tBg8Psjm/47GPUU644L6Q8GPcHDHXWyDv+K8hvAG+/zD2j5cpDMuqd8ffM9OaNnFL6AFbc9BXS6XE88Twt1gL2Rr6FiRzuCU0OeRUAvro1ZceXiy6FOFZzdv03ajXRaZkfL64sBjfYwzaI5XeL6YbW5bz7z6VbRLOpcisT7GGWvQbhefklS433lVX4Mxd1UVsdaIfuWUEU6ZfRVqXzmdwZ8m1xavrIn/OuMxdCiaygMpTvznUn/9/TFeRSPwUNK51Oi4aNLk/2cdqGp8NQKYqJ4AAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAXCAYAAAAV1F8QAAABUUlEQVR4Xu2UPS8FQRSGD40gV+GjEXJbrYJKRRQKQau7f0UkIgpREipRiUQ0EoVGKSEKjUJBJIRKSHzzHjtz884xO+72+yRP7rxnduZs5m5GpERkCjbZomHUFopQgd9wEN7D2XC6zh5cscU8qpJtyrzCGmWdVxfgOJx3+Yue+Re/ia21m+zpdb8XsI3qSQ7gs8QbMZ8mj0iBI+uDu/BB/m6sucdkxjZO4hfHGl3BNTfuhls0dykFjmwH9rtxrJGif/S2hG8/BpcpJ+mCh5TzGsXgpp3wFp5RLcBu2mgjPc5Wyrzmnca/rMIBU2uk0QRcorwJHymvi7lB9uGRUZuoOtYFMT5MfoHnlKfhMOUovlEeN7DF1O4kbDQDhyhHSTWahHO2CBbhE+UNSVy+J5J9NddOHR8HT2R3Xh76cn7zN54oin44zbZIdEj2QZzaiZKSOj9A0lionp9a3QAAAABJRU5ErkJggg==>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAABxklEQVR4Xu2VzytEURTHj7BQwoIk2dgQWcpCioUkVpbkD0CESKIssKNkZzWRQoqVomxsbWykpFiwkVhYWJAf3zP3vufcM+96ZjEpzac+zTs/Zu55c9/cIcryN5TDep1U5OtEpjiFW3AEPqlaQAH81EkfE3BAJ8EY3IF1Nq6Fm3A07CCqIHehY/gML2AX7ITXtqdF9KXAd/RKppEddMtJFui7HnjmdBBt23xAI+y213lkvhn2Kuz4Bb6B5uAqXIezMNctJzkndyDumRcx867iWHwD8RBtOqmYInegdtghYr6hH7cqCt9AMxQ/UDG5A8mHupDS3KoA30DTcJFMPWFf15wOQw98gzewX+Q/xHVa8EJDOgnG4ZHKca9+RqLgwZtFHNxYr8h54cZhnfTAvXKLoiiClyI+gIf2eg9WiVokvAAfapocnSDzi4kbSNd17Ds8Q/gN8rAL4PxjRE4vIEnAJhHzTel+HafADXwqazg/GZHzfWAJmXNJo/t17FBKpmFJF8ALLBNxK5neGpGT+BbS+cgt24UP8A7e2td7Mn8nEt6y4Fthq91yyAZs0EnLMpn/RGYfVopaxjjRCcUKmXOpTxeyZPl3fAGC326HVAPLggAAAABJRU5ErkJggg==>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAXCAYAAAD+4+QTAAAA90lEQVR4Xu2SOwrCYBCEF58gKmInlvYK1nZWWgnW9p7BM9goWNlaWYtn8CCWegHFxy6bHzeTP0QIgkU+GEhmwk7+B1HGP9NjXVkv1onVCMfpmbPW5n1HWtY3XmpkoCjJS8WZogN9JS1WDjxkhEYcC9KCMQakfgHNgBurgqaPCemgFQYGyYvg3VlV8LwsWXvWgzWEDLFFUlAz2Ve0SYccMADkGymoY/AtvoNHnoHKGPiQ7dmC50oG4DtkuDsDeS6ZLMKU/H/tvDz4gi2wHl6GEDLMLrkbeEfjOWTVcddUiuKuNzXps78X0oJN6AulQwnbwszQyMj4HW8vEDhXyW73GQAAAABJRU5ErkJggg==>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEIAAAAXCAYAAAC/F5msAAACG0lEQVR4Xu2XTStuURTHl9cob6WbJPkANymRgWQgSaQoKZJvYEQ+gAyVzJjQnVwmmKibpBiKgbdbN0UyNzAwuXlZq70Py3r2fs7aj0c9dH71z1n/vdY+2zr2PgdAQkKuU4P6KU1BkTS+G4eo36hJ1J0YiyhFPUszmxSjDsDcZEeMRWhyfMTV1sL7X3AXdY/6i+pD9aKubE4Hy8sqzWBuUGnjVhtzNDk+NLVrwqOcfntdCOYvgXT5mvEJ0AJOHN6ZiONyfGhqz60XUYCaZTHxKOI46CyZlqaPH2AWsCz8Y+sTmhwf2toZEXejeli8COFbogQCGjEBZgELwt+zPqHJ8aGtpW3DY35YlkFmW4Lq1I1oAPcTu7F+NehyfITUDqH+o65R48x/YtchlENAIwha0KnDI9GhFcVxOT4+UruEamfxHJi6Ueb5CG5EF5jJ6RVH0H6lg4y8/IAcH5nWVqD+sXgb9cdeb6Dq2ViLQ51gzhbpk7zQFx293y9QjfD2zuZocnxkUivHZczPkQGHRlCrDp+khm4atzc1OT7ialdQbSzOg9RGyFgSvDVoQjkpxYMijsshhsE8fY62NqIKzHeFxDVHOjJqxAOLjyD1W1+TEz01uUBNLUfWR0g/3RxEcCOawNzk1v6k/wkkmhxiCzUlPG0t8QvMGeJiHrVurzdRdWzMRXAjcol9aQjow4zOljE54OBLNyIhISEh53gBCtfCyZUGgVMAAAAASUVORK5CYII=>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAACAUlEQVR4Xu2WMUgdQRCGx4hIECQkRgU7IakkiBYihDR2dooaRMSAINGgRLASbIRUCSFYWytioZVFUttoCgXRWmIjplLUYCJxfnfmmBt23zMgQfB98LMz/8w75613t4+oxP+n3xt3mU7WX9ZrX7hrPKAw6GdZP8j61DYxVayvUttkleXLN2KKNepNwwzrmHXGGna1jD+sVokxjGLjBskfSv5EcnzZYiyyLij0Q2P5csYu65vJd1jrJs+IDfnT+aesJZOD76xfzitGauBqyv89Bd6jmIkd1BisUNh5BX6fycG0+P9CauAtil8L3nzMhN7K6nlFwX/p/CHxHzu/EKmBdQZP1K83Beic9czU34vfYjzQK36b8wtxKwODctY25QfHfQVmJX8hudIl/oDzC4H+d96k9GApPwNFu+NgROJmbRJ6xO9wfiHQP+5NSg8W9fdZbyTWYpOJ9R5ul1wZFF8f2JuA/glvUmIwSvgwfpjY+qBS4tt6S+CZ8JxQ/Frw9rz528T6oUYTqz9ncrAmvgUPYp3zLOif9CaFzfDXAvD0UMv4wlqQGA0Vsj7POuK7ibzb5Diq4fk+pYZC7ZMvCKjh1ap8FC8KfqXhoEADdrw2X74GR+ylrOiL/WtXKfxesCyzjlgHFG49rIcUjmsLjn1cd4PCGwunaNHfK8lvVKJEiXvIFYU7ognPNDnVAAAAAElFTkSuQmCC>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAACEklEQVR4Xu2VT0iVURDFR1M0KxMlIiLaCZJKBCJithGRqE1igUrYyl3iTnATJuJKEHHjSkik3CgISYQEblVCUYJIc+dSKAiFKJvzzdz35o3XPwsjgveDw7vnzHz38b775xFl+TdcZd3yoSPfB3+LJdZrVjdr19UC51kHPoxxibVF0vzR1cAF1nuS+jIrJ7NM17QWWGB9Z31iPWDdZ33VngbTF+UZSWN4lS9Y31JVouskdfw6UKY+N9VB9EazQA3roY7zSJ6FvqQ6juAKyUSFJoO3k/9gTRsPVlj7xm9Q5jPnWAPGg1/OR/FfDoqcR/2Jy/o0D/Q638RqNn6UTrFUAJOs67iOZC9Z7pH03HV5p+al6i+rD9hNfZFOsVSggmSSKdYaycYd0yzQo/6OycBjzWtN1sL6ydpmPTX5bzM+ljaKLxkm2NPxS5J6dbqc8EjzDpd7xln1xg+SPNdushQ4jijuuPyD5qBLx7fT5YRWzRtdbilmfTb+LeudjmdYN0wt4SbJpJMun9McRzfsIewvC5YEOa6Eo/Bv3vvo5Ykmf6TxS5CXswp0fNIp80xQ5v7CRer7vU9AuOmyVc0DGOPYWuY1j1FCci95fL/3CZV0uADfb3zsbcDjVMXwvQGfR5cMPCdpDv9lQ5nlBPxp4qbFJ3pwHcR4xaryoTJM6e0xS8fvvzNj0QeOEZJr5aTrIkuW/58/51WCjgFY5MwAAAAASUVORK5CYII=>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAXCAYAAABwOa1vAAACJUlEQVR4Xu2WTUhVURDHp0QkAhHFD3An+EGEiC4kEFHcuVNSERGDIFpW1MKPCLJWgog7QQghila2EtS1GxVUEF2L29ooWlCR839n5jp3OJcXBSH4fvDnzPzP3PfmnnfuPY+owP9n2BtXmV7Wb9aQn7hq3KTQ6KyMb2WstEXMbdaazG2xbqSnM3nK+sS6I3kT6z3rSVJxyUvWCeuc9dDNJfxktUmMZhQb10p+S/IKyXGz+XhDodZqJ1UROGCtm3yftWHyhFiTX5x/RmGVLNus786L8Yo1z1piTbGK0tM5Sin9fQq8spiJFdQYLFNYeQX+oMnBhPj5QJPd3nTsUvyz4C3GTOixjJ5OCn6H88fEL3e+Z5LyN6w9eKJ+jZmAvrHqzTweDvitxgMD4rc73zNOlw/yOxkXUhUZjVG2n9tXe5RuHPsKvJa8WXKlT/wR53uesVadh+umXR5rLMtPwKRdcfBI4hYtEu6L3+P8P8E34nMl6h+xHkisk3dNrHv4nuTKqPj6wGYRe1//on9oGMaxia0PSiT+27cEar5GPHvtqcsVeIfe/GFivajOxOrjXWpZEd+CB7Haeah5EfHstVgM/1kAnh5qCXOsDxKjoFjGhqQivprI+02On943AnDM2mO+i0JNo/EAPLxalRnxouBfGg4KFGDFq9LTOT5S2HsYURf7L/CZ9dybFLaE3gyEX9CDYx9zmxTeWDhFY/s/ReYdFShQ4BpyATjvrMgJxf0CAAAAAElFTkSuQmCC>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAAA9ElEQVR4XmNgGAXUACVAnIkuCAXcQLwLiP8D8WkgZkSVhoDlQPyLAaIIhLNQpcFAmgEixwnlC0P5THAVWAAuw74C8Uo0sTNA/ANNDAXgMgwkHoYmVgUVxwmwGWYHFbdBE4+HiguhicMBNsMKoOJGaOKhUHFzNHE4AElmo4k1QcX10MQDoeLRaOJwAJLMRRNLg4oboImHQMWd0cThACSZhyYGCzNLNPFYqDgo2WAFIElQGCEDdqg4WbFZiC7IABGfhCa2DSqOFYgwQCR70CUYsLsCxA9CE2NYDcSvgfgJED+G0i8ZIFkMGYCy3V8ojS04RsGwAQAdIkCNXu6jYAAAAABJRU5ErkJggg==>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACIAAAAXCAYAAABu8J3cAAABmklEQVR4Xu2VTStFURSGFwaSksjIzIQUiYGURH4BYSIZKMkIZeAr5WNkZqaUlJI/oDA2QaHEzD+QIjIR67XXvr1n3XNvGJ+n3k7r2Wufve+550MkI+P3VGpONV+aS01JcrgoK5oXzbtmwo2BWc2RptnqJs2BZibXYdRL2ECF1bVWl+Y6CnOvOaP6TnNONdiQcD7OdaLDeJOwY+ZK8+Gcp0rCST1w1VSvarY1+5plTRmNJcDEEecWzRfjRtJ74HapxuJ9VKfSI2Fit/Pj5mucZ+Jl9ni/JL/YCG4YTGp3fth8p/OMXzDi/YJm09yeHXdo/Ic1G2h1fsD8qPOMXzDi/ZzmhGqA8XUWkybbWCpD5vudZ/yCkUKeyeuJ90gXS2XMPB7tQuSdzPA+7Z30KW5uuYn/PDWvkt4D9+DqJ6qjy5sLgeecOTbPYHMMNu97AFyHq+epji5vbtqvRz1I9bO5aXIAborqLXMMXv11VPdK6Gkkl+NQwv+GI5r8d6BF8+gcwGcB/ReaWwlv47R7An9NvApIQ3I4IyPjb3wDqsB7aeGHjYIAAAAASUVORK5CYII=>