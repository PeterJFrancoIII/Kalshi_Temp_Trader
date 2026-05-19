# **Analysis of Forecast Accuracy and Verification Statistics for Miami International Airport and WFO Miami Temperature Predictions**

## **Executive Summary**

The National Weather Service (NWS) Weather Forecast Office (WFO) in Miami (MFL) demonstrates its highest skill within the 0–48 hour short-range window. The transition to the National Blend of Models (NBM) v5.0 in April 2026 has significantly enhanced this capability, extending high-resolution hourly guidance from the previous 36-hour limit to a full 48-hour window. Temperature forecasts for Miami International Airport (KMIA) are characterized by exceptional stability compared to continental U.S. stations, with a one-day Mean Absolute Error (MAE) typically residing between ![][image1] and ![][image2].  
The "felt" heat index remains a critical verification challenge; while KMIA station readings are highly accurate, hyperlocal data from urban neighborhoods often record temperatures ![][image3] higher due to the urban heat island (UHI) effect. For prediction market participants, the 48-hour window represents the primary arena for capturing informational edges, particularly regarding the timing of sea breeze fronts and convective cooling, which frequently cause transient temperature plateaus.

## **Quantitative Verification Metrics for the 0–48 Hour Window**

As of 2026, the NWS Meteorological Development Laboratory (MDL) verifies KMIA temperature forecasts using the Analysis of Record (URMA) as the ground truth.1 The following metrics reflect performance for deterministic surface temperature (![][image4]\-meter air temperature).

### **Deterministic Accuracy: Hourly Mean Absolute Error (MAE)**

The MAE at KMIA typically starts at a baseline of approximately ![][image5] for the current-hour "nowcast" and scales linearly as lead time increases. Performance is optimized by NBM v5.0, which uses quantile mapping to calibrate the meta-ensemble of 31 model systems.

| Lead Time (Hours) | MAE (∘F) | Primary Error Source |
| :---- | :---- | :---- |
| 1–6 Hours | ![][image6] | Instrument noise / Tarmac micro-spikes |
| 7–12 Hours | ![][image7] | Boundary layer depth / Cloud cover timing |
| 13–18 Hours | ![][image8] | Nocturnal decoupling / Everglades muck cooling 2 |
| 19–24 Hours | ![][image9] | Sea breeze onset variability 3 |
| 25–36 Hours | ![][image10] | Synoptic frontal positioning |
| 37–48 Hours | ![][image11] | Moisture advection / Convective initiation 4 |

### **Error Distribution: Accuracy Probability Buckets**

Industry "guarantees" are measured by the frequency of forecasts falling within specific temperature bands. At KMIA, the stability of the subtropical maritime air mass results in a high concentration of errors within the ![][image12] range.

| Accuracy Bucket | Probability (0–24h) | Probability (25–48h) | Market Utility |
| :---- | :---- | :---- | :---- |
| Within ![][image13] | ![][image14] | ![][image15] | High (Tight Straddles) |
| Within ![][image16] | ![][image17] | ![][image18] | Moderate |
| Within ![][image12] | ![][image19] | ![][image20] | The "Standard" 5 |
| Within ![][image21] | ![][image22] | ![][image23] | Safety Margin 3 |
| Within ![][image24] | ![][image25] | ![][image26] | Low Risk Bracket |
| Within ![][image27] | ![][image28] | ![][image22] | Tail Risk Only 6 |

## **Historical Trends and Foundational Studies of Miami Forecast Skill**

### **The Strassberg Grid-Based Verification Project (2009)**

Gordon Strassberg's research at WFO Miami shifted verification from point-based METAR checks to 5km grid-to-grid comparisons.2 A key finding for the 48-hour window was the **Cold Front Overshoot**: human forecasters often outperform models (GMOS) two days prior to a front, but on the day of the event, they tend to overcompensate for model warmth, trending ![][image29] to ![][image3] too cool.2

### **The Rosenstiel School Heat Burden Study (2023)**

Research from the University of Miami published in the *Journal of Applied Meteorology and Climatology* established that NWS reports for KMIA systematically underestimate the heat burden in the broader metro area. While accurate for the airport station, the 48-hour forecast often fails to capture the ![][image30] higher heat index values experienced in urban canyons like Brickell.

## **The National Blend of Models (NBM) v5.0 Framework**

Implemented effective April 15, 2026, NBM v5.0 is the foundational guidance for the 0–48 hour window.

* **Extension of Hourly Guidance:** Most weather elements, including instantaneous ![][image4]\-meter temperature, are now provided in 1-hourly steps through 48 hours (previously 36 hours).  
* **Methodological Shift:** The system has moved from decaying-average logic to **Quantile Mapping (QMD)** for surface temperature. This improves the calibration of probabilistic outputs, particularly for extreme high-end temperature percentiles.  
* **Meta-Ensemble Inputs:** For the 48-hour period, NBM v5.0 integrates higher-resolution ECMWF and HRRR (High-Resolution Rapid Refresh) guidance, weighting them based on the previous 30 days of performance.

## **Hyperlocal Influences and Systematic Biases in Miami**

### **The Sea Breeze Capping Effect**

The most significant determinant of temperature accuracy in the 0–48 hour window is the Atlantic sea breeze front (SBF).

* **Easterly Capping:** Persistent 10–15 mph easterly winds act as a natural air conditioner, preventing KMIA from reaching upper-80s thresholds.  
* **Frontal Stalling:** If the SBF fails to develop or remains pinned at the coastline, KMIA can experience a ![][image29] to ![][image31] spike above the forecast high due to unchecked solar radiation on the airport tarmac.

### **instrument Nuances and Settlement Risks**

Prediction markets like Kalshi settle based on the NWS Daily Climatological Report (CLI).

* **Precision and Rounding:** ASOS stations transmit 1-minute and 5-minute reports with precision to the nearest whole degree Celsius, which can lead to ![][image32] rounding discrepancies when converted to Fahrenheit for the final CLI report.  
* **Tarmac Spikes:** A 30-minute break in cloud cover over dark airport surfaces can trigger a YES resolution for a temperature bracket even if the broader city remains cooler.3

## **Implications for Prediction Markets (Kalshi KXHIGHMIA)**

For traders focusing on the KXHIGHMIA series, the 0–48 hour window provides a clear statistical edge:

1. **Market Overconfidence in Extremes:** Markets often overprice low-probability events (e.g., a ![][image33] high in April) while NBM v5.0 percentiles show an 80% chance of staying below ![][image34].  
2. **Ensemble Spread Filter:** When the NBM 171-member ensemble shows tight agreement (low standard deviation), the NWS "Expected" value is highly reliable. Diversion between HRRR and GFS within the 18-hour lead time signals a potential "bust" pattern.  
3. **The "Morning Ramp" Signal:** Observational trends between 8:00 AM and 11:00 AM local time are the strongest predictors of the daily MaxT. If the rate of increase exceeds ![][image35] per hour, the upper temperature brackets (![][image36] over forecast) become significantly more likely.7

## **Best Sources for Hourly Verification**

* **NWS NBM Station Card v5.0:** Detailed hourly data for KMIA through 48 hours. [https://vlab.noaa.gov/web/mdl/nbm-textcard-v5.0](https://vlab.noaa.gov/web/mdl/nbm-textcard-v5.0)  
* **KMIA 3-Day History:** Interactive timeseries with 5-minute observational data. [https://www.weather.gov/wrh/timeseries?site=KMIA\&hourly=true](https://www.weather.gov/wrh/timeseries?site=KMIA&hourly=true)  
* **MDL LAMP Verification:** Official statistics for Localized Aviation MOS Program accuracy. [https://vlab.noaa.gov/web/mdl/lamp](https://vlab.noaa.gov/web/mdl/lamp)  
* **Rosenstiel School "Shading Dade" Study:** Analysis of urban heat discrepancy. [https://news.miami.edu/rosenstiel/stories/2023/06/officially-reported-temperatures-underestimate-miamis-heat-burden-new-study-finds.html](https://news.miami.edu/rosenstiel/stories/2023/06/officially-reported-temperatures-underestimate-miamis-heat-burden-new-study-finds.html)

#### **Works cited**

1. National Blend of Models (NBM) — CONUS core grid \- GribStream, accessed May 8, 2026, [https://gribstream.com/models/nbm](https://gribstream.com/models/nbm)  
2. 7A.6 Verification of Gridded Morning Temperatures at NWS Miami, FL Gordon Strassberg\* NOAA/National Weather Service (NWS),, accessed May 8, 2026, [https://ams.confex.com/ams/pdfpapers/160386.pdf](https://ams.confex.com/ams/pdfpapers/160386.pdf)  
3. KMIA Station Info (Miami Intl) \- National Weather Service, accessed May 8, 2026, [https://www.weather.gov/zse/ZSEStationInfo?id=KMIA](https://www.weather.gov/zse/ZSEStationInfo?id=KMIA)  
4. Area Forecast Discussion \- Miami \- National Weather Service, accessed May 8, 2026, [https://forecast.weather.gov/product.php?site=NWS\&issuedby=MFL\&product=AFD\&format=ci\&version=1\&glossary=1](https://forecast.weather.gov/product.php?site=NWS&issuedby=MFL&product=AFD&format=ci&version=1&glossary=1)  
5. \[OC\] How reliable is the weather forecast across the US? (to within 3°F) \- Reddit, accessed May 8, 2026, [https://www.reddit.com/r/dataisbeautiful/comments/1dtk3j5/oc\_how\_reliable\_is\_the\_weather\_forecast\_across/](https://www.reddit.com/r/dataisbeautiful/comments/1dtk3j5/oc_how_reliable_is_the_weather_forecast_across/)  
6. Miami may be hotter than what officially reported temperatures suggest, study finds, accessed May 8, 2026, [https://www.cbsnews.com/miami/news/miami-may-be-hotter-than-what-officially-reported-temperatures-suggest-study-finds/](https://www.cbsnews.com/miami/news/miami-may-be-hotter-than-what-officially-reported-temperatures-suggest-study-finds/)  
7. Miami Lowest Temp on May 8: Will It Hit 72-73°F? \- Lines.com, accessed May 8, 2026, [https://www.lines.com/prediction-markets/science/lowest-temperature-in-miami-on-may-8-2026](https://www.lines.com/prediction-markets/science/lowest-temperature-in-miami-on-may-8-2026)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAYCAYAAAC8/X7cAAABxklEQVR4Xu2WOy9FQRDHJ4gGjagoSDQkfAISiZJEJB69ROERQoLCI1EoFD6GRKHgCygkGhIqGkRDI14hNOI1f7vrzJl73LMryv0l/9zd/+zM3rnZs+cSRSIRzQxrVJs5LLM+We+sxXTomwnWGeuW1aNiEtTwUZtLcGywXilZMJYOF2WH1SnmC6xHMW9kNYt5B6tKzDVzZL5DVqNlZGKlOiAJaaCEda1NMjXq7HhVBiwj2hCgeeT/xoc2NCEN9FL2ZvAa7LiJVZuEqIVVLeYadwok9WKsYwWENFBByYY4KgDHRW+ywtplHbAmVUyCo4HcfeXLen1inElIA2CLkiaOWM/pcBCzZOp0CW+bzDPqDQqMazOHY0qagFrTYW+eKF3HSV4CuSAB154vL6wBOz6lZNPKnxX+uFztBYGEYudUss7aU147mRonys/DXZGHyv9TA1Pa/AWsdQ+vZInCN54nk9OtA6GgyLQ2LdhEgrX9ygPDrHNt5oCjGNp0ATVkiqzpAPNAJiZvqEHraeCVazMH5GTV8mKTdcO6Yl3aT7xh8ffCgZvlQswdQ2Q2xvX5Zsf4IXzBL4+37x3rnsxNlPu2jUQikci/8AWI5X3+h2bnpwAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAYCAYAAAC8/X7cAAABxElEQVR4Xu2WzSsHQRjHn7ykyIGS4qC4EM4OFOWgKBcurk4obhxcUe7iD+Cg5OAicXP7IRflpFycyEsUSt6ex+y0z353frvzK8f51Lf2+T7zzOzOzswuUSAQsPSx7lk/rAKrLJnO5IhM3RNrEnLCLOuKTP+jkNNIHz7qtQWWNdaGit/INGxVXjGkXWV0PRHFd3Ga2lgdKu5n1aoYWSDTh+tBK8jkyjEhZo/DE2VxwNoDb5+SN7CqcpYpNBTPlD3uNxo15L5Zl4d8kmkzrrzOyLuN4nZWU5ymLla9ihHXuC3qGnN/LFF6Xbk6QppZm+ANkKk7V94y65h1yppTPiJLQ2pPwNf3MaauM5Gi1Ovy4JBMrcx0qcyTqR1WnizRbRV7cUGmo2pM5GBn8AwTnrxQ/Oa19CGQi2xmKWrAhAfvlFw6peJathhnUkemoAoTHlyydtAsAXtE4gR4P4B8uLDxFsTF2GWtgHcDcR6LZMYfwYQvrg37BbEMgsiHZxq8RtY6eHm8UnoCvfmg9MbB9Si/CRLPKG8w8lwaUu18wPG8kbMcB7eSTWnpZl2rWMD2Wr7/UjLz8vV9YD2SOYlcqyEQCAQC/88vSt2MW1ht+v0AAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABX0lEQVR4Xu2VvyuHURTGnxL5kUxmJSklWQz+A6WsslmMNn2VRZRkMyiTCfm1KYtBsaFEVlZZhAyUwjmd++p43t/fTb2feuqe53nPvfe99/32BSoqsmkX3Yu+RVeUdYveRZeiXco8x7D+IooxCQsaQz0vev1NgQ03bhDVXJ1E6kLCvuiTzU5YQ7Pz/CQtQZ5Hqj26Se294CCgJ37KZtKuW6leoXqJas8MbL4R8qOX7BAt+kDRhtswHobtlBkUPYi2RGeUMXqN/FJzop4w1itvcxn6YA3bopsQrgWvXvhkozVSmUC8SfmC/RrKEn0PSUplFPaAHrXnJPhlmYX1jTlvQHTg6hhdsKZN8g+DP0R+Hm+Ib34KdiWZaNMeeUfB7yU/j9yjT0Ob7si7Dn4ZmmA95xwUoR/xBbVeIC+PVVjfOAdFmYZNEP13LP+NM9mBfQvPoifRi+hDtO4fqqio+Jf8AFpcYnRrxyFyAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAWCAYAAAD5Jg1dAAAAg0lEQVR4XmNgGFrABojfAPF/ID4BxEyo0hAwGYinIfG/MUA0KCGJgQFI0ByLGAjDATc2QRxiDM1AbI0mhlUhNgBS9A9dEB1cYoAo5EKXQAYvgHg/uiA6OATEU5H4wkhsOJgExGVoYlfQ+AzRQHwBiGuAuBqIG4C4nwHN15xQAVx4BAMAGwYkIC2BLqgAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAYCAYAAAC8/X7cAAABjElEQVR4Xu2Wu0oEQRBFSzQ1ESMTA0EU9AsMzBVMzMXIJ8oKuxtsbGDgfxiY+AtipGhsIJiogfgWRDBQq6hutrzz2J4ewz5wmamqqd65Mz3dS5RIJJAmax2TFXhnLUJui3XFemQtQM3yE6gZ3+A5YH1R94KNv+VgVkn7rYEx1qSJZ1mDJkbapGPkGR0grfVjwVLHwANlDeyZc88aJgxvpGMU8Y0JJNbAqzuigQnWiImnWEMmRvwssIyac6xliDGwxFp252hA2GUds85Y21CzyNSQ/lPI25vGsTPEGJAP15NnIJQWaf+cyR2RfqPByACbmCzhntVn4joG5EH4KWRlF4GeSIMseyHMU3ZK1DHgbxhzlZAGvKkiPjFB8Qb8EnkB+SgDDUwWcAI6J+2/dHEVOqS98lZrIYPsYNIhP1LGOMW/gQ+KeNrIMOkg+1hgXkhrZSuUbPFyzQoWAsib/8Ecku6it6wbd5TVRf5eeKZZ1yZGxOAddfslDkGevOy+T6xn0pWo526bSCQSiX/hF18fdUd3ZY1kAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAAA9UlEQVR4XmNgGAWjYBSMAlRQAsSZ6IIkgE9AHIwuONjBciD+BcT/oTgLVZpokM4A0T/kAgAZUBIArxlGcAB8gNIjMgDigDgByh6RAQAq+GBgWARANrogHvASiBmR+MMiAHLRBXEAbyDOQxMjJgCEgdiESKwO1UM3APIAuqdwge/oAgzEBYA8EPsRiW2heugGQB4oQBfEAQ6j4TMMEP3XofwhCUAeKEQXhIIqdAE0oMZAXAoYtECEAeKBHnQJIHjPQLiGsGaAqElDlxjsYDUDpBX3BIgfQ2lQ6Q5qHsOALhDfQ+KjA1AAPWVA6AfxR8EoGAWDGwAA9dpDa5pNN8oAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAABGElEQVR4Xu2WsWoCQRCGp8gbmDYKBrSyUGx9BS0sDNjZmWCiIAh2YmMhlqJPkMIn8BV8CBttJIVdChH0H3ZD7gZP9hIQB/aDj+P+uSlmYLkl8ng8njBd2JThFU5wCBuwDl9gzfoU+O6u+YQHMsOwr+FyJEn67bkk19URZwFvcALzMAOfYRr24DzwnSriLGApA/AAv2WoiTgLuMRRBtr4zwKmcCBDbfAC+Gz/Be5VDw/RkqEDY3JfQAIWHc3anpvBQ7zL0AHuW8kwghQsO1qyPTeDB2nL0AHuG8lQIzxIR4aWvgwsFTJ9H7KgjUcyg/B5luwp+g8xI1Pj67BKFvALbuHGPndkrsc/5OA68B6kSmYBBVnweDx3zRlQID8NWSF8RQAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAABAUlEQVR4Xu2WPQoCMRBGBxEErUSsLAQtrOwEC/UKHsQj2HoEwQt4GWsrK5tFbERBQUHwZ0ISGMeY3RTKZs2DV8wkgZ2vyAYgEAgEJH10hz7QBZp7XY4lj1550xem6IzUZ5BBNEjvEyuQe7VeIj68a+i5DHQEt/2poQTmYU09G94GIJigPdb7qwBMiGHuvGkhUwEsQQ5T5AsWMhOAuAzFIFW+EINLABW0k9CWOvMTyiCHKPCFBLgEUEeHCR2oM19HPHz4AHNW23AJIJWYLrwbq8espngdgHjC6t8eV3NQ9Yj0KPr16B01eB9aeyH72uia1JoTukUj5Qbdo026KRAIpJInOi9PYMsOXJQAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAABTElEQVR4XmNgGAWjYBSMAgiwAeI3QPwfiE8AMROqNF6wigGi7ycQl6PJDQkwGYinIfG/MUA8pIQkhguA1PGh8X8h8YcEADnaHIsYCOMDdgwQNXuRxN5DxdSRxAY14GbA7llsYuiAhQGipgtJDJZ6kFPFoAfNQGyNJkZMAGAD5OobdADkiX/ogngAKDVcYYDoYUSTG3LgEgMkALjQJXCAKCCeDsQvgXgTmtyQA6DCEOR5UXQJIsELBoh+fKlAGIhNiMR0LUwFGSCOZ0eXIAEUM0DMeI4ugQTkgdiPSGwL1UNzAGr4oBdei9H46GAREP9BEwM1qIZkQYitwPuLxq9C48M86oAklgIVe4okNugBqOUG8ww6hgFYAycLSWw9EB9C4oPAFwbKsxFdgTQDpqdh+DuSOl0gvofEh4F1DBC1D6A0SM+Q8fwoGAUjHAAAvbRaPMZeYSwAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAABU0lEQVR4Xu2Xvy4FQRTGTxQI1Y2oCKEhESqhQFSi8yAegUruE4hEo1Dc4r7CfYNL6wE0Eg2iIyH+fF9mJnucO3ZXgdlkfsmX7PnOTLLn7M7srEgmk8k4NqF76AO6gIa+pis5hN68dk0ueU6gUxU/iWvEvPLKeIXO/PUI9A6NFun0YbHrEY+q4gG6U/GxuHlrykuacYkXG/Msc+LGzBh/xcTJ04Y2jFenAX0pxgxDOyrXeFgY13IZoUldaBta8jGXQaO5ElfImE0YQgOOlMeNk9608hoFN0MWMGkTEb5bJvRuramYgFZrasHP+RNa4m6en7I6lDUg5gdmob2a2vJzfh0efOxNd0xsuZTBOaSqAUkS2/B4qtMcmHhR4oXSO7dmyrxI8dSsAo8+3lce4amxp2IeiWNNSZYpGSw66FmNW4auVay5ETeejeSb9NP/iEwm8z98Al+PW8y8ukiKAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAUCAYAAAA9djs/AAABQ0lEQVR4Xu2WsUoDQRCGRyyCjYgpU1haqaCWSZXOQgTBF7ARH0HwCbRRsNLSKnWwsQ4EKwXRzspSERTEJuo/7C7MTXbMWRhvYT/4iv12D27uDhKiTCaTcSzBZ/gF+3CmuP0j+/AVvsNttZcEO/BYrM/JPYhl0Szu4KVY38KeWCcBD8uOapppip/h9psv6N95pOFByjyAa4qf4XamY0rskRtiTW8orIdk9STYIHfzR3ojgjWo1SvPIezAAWyrvRjWoFZPhga5Abp6Q2ENavVAHa6WdN5fM3ZGDcFYZ6wemIPrJW35a/4U/uRPVQtDNFWXvFF8UG73OlaVTYq/sdAmReNfB8kWDV/HcFvRscrwDdfEetG3C9FefNsVjeHG/yQDB74lxSz89D6RG+CkcIJoAT6oxkyRO38Fb+AHnCicyGQyVeUbxSRc5+MtLiQAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABe0lEQVR4Xu2VPS8FURCGR0hEgkJJRKFA4icIahKdRq3Q0PhK1ArxB/QaiQLRK+hIdDqNRpD4CPERInjnzjnMzt295+xGc5N9kjebeWfPnDmzOfcSlZTULw3QpDUz2Ia+oXdo2eSYWegcuoUmTE7DNbKUSQu0YM0UuEi7iT9U3AsNqHgEalOxZYmkRq0DJWiFFq1pGCYpeqC8B+f1uXhN5Twz1lA8UmCCFj51qNEmkqLrynt1np9yP9T5l6ZBqEPFlrRP3WPiBDGNppG20Sp0CJ1AcyanaSRZe2x8Wy9B3kZ5umfQF8lFLALvx02NKW8P2vKBn0KsumXZL1PQBnQD7ZtcHp6oei+WvoxV5J2o55qkeJGp+sasV5Oijc6TFL+yiQD+Yp4a/18a3YQ+jTdE6ZMJsUKyZtwmQsQ06hsaVd608y6VF8ML5T9chZhGd6Ej4z2TbNhs/BBRX8G/FKsuWVZhx3kX7vlG+ZrkSfK/0R10T3Lz+SeupKSu+AGgTHcwd/XBowAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABJ0lEQVR4XmNgGAWjYOgCRiAORRfEA1iA+Be6IBTkAvFtIH4DxH5ocsjgPx6ME3ACcQm6IBZwgwG/gcpArInEtwdiXiQ+OihjgJiDz0MogAeIS9EF8YBPDNgd2oEuAAQZ6AJI4CMDdnNwApCvqeFQDSCWQuLrALEQEh8dYIsZeTQ+CqCWQ0GgBYgPAvEpIM5Dk0MGzAwQM06iieMyFwyo6VBiAcg+kBleSGIbgHg5jIOcGYjBshBtKIAaDoWZgY6RMyMGGIgQhTkMXQwvoLdDQeUwSP9ZNHGCZtLboVUMEP3e6BKEAL0d+pWBTP2kOvQbA5kWQQG29IkBYIqIxdIQbWDwGYifA/FjKH4KxO8YIFUnMQAUkqDa6C0DRB8oZv6hqBgFo2AIAACvLGxUX7ScqAAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABkElEQVR4Xu2USytFURiGP7fkkkuShJSRkqEMMJTEyNxfMPUDZKhEKaUUAwyUiUhSMhFlICkpBiYGMlAocnnX2Wud/a13r3MOtWc89dT6Lnt9e6+z9xH5J12aYBcniTJOpMEJXIMT8JFqjgr4xUlHu4SL/fBBotoxLPbL0mxrjn34BC/hCByGN7ZnQPV5mCIPn4cLKn6RqKdD5dZtztEDR+26VKInNl5nO4g9+CzJ4SbuDeR03wXFJXBKxYYPirO0wi2Jj9ZRZePQDencJMWDcEjFc1LguA083GCeoI9yPLyWYv3CVUue496EbXYdGh7C9HxSbgy+w1s4rvLcl6UBHqj4J8PPJeqp5EKARfFPbVrU/jyo0HDz4pl6IxcC1MArFW/DXReYu+qMaxnyDa+XqFbOhRzwPl68A49I9yKZ9VLcmvlT4c1WKdYsi/95Fkny+gRuOBN6aXJ9t3USffdMaF+P0PA3lWdD/DYvZ/Ae3lnN+hS2SHKg8zVzpc8K7OakZQZucDJNDjlBzEr4J/wjfAP7aHmE2OsdqwAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABtklEQVR4Xu2USytGURSGX/dccisJM1MkA1HISBIjZegHmJiak6ESpYwUCj9AGZiYyQghUpSBkdwGFLmsZa91rLPO+b7RN+Opt7PXu9a+nL33OcA/uaWe1OJNR5E3csEBaYM0Sbp3OaWU9GWNXtKdmPukfJsUakm3CDVXpKp4Gg2SU3ZJz6Qz0jBpCKEf1/Rp0SJpSQPiBaGg2XjFCBMreQg1HcbbFE/pJI1IuxDhjVmXUQVChy5riGcHejRtpZX0YeITxPsUkGZMzNh6lCM5EeM9bk+YmGkXX5ly8QBp0MQLMNut8Op6nOcnf5CYz1Hh3bCD8R2wfeyFq4Db7mzwIJ8m5i3UBbF4Yj1PyyjpnXRNGje+HSsrxwgTlDm/UXzVaTydkWXEd3YW8R2K4IvHiTrn89m9Srsfvws4iirSqSRdmHibtGPiiBqEAUt8AukrvUG6b/F5H//APxWfWJPnGJI5hf1ubworiH/C+m9IkHYh9JvkH0lqJ2T2qxG+e0+i/k3MNCncnjYxw/Gh85TEJELMbxIjTXrBlCfxz+W5Hk9HrJLavCnMkba8mUv2vOGYR/ox/xG+Adk/e5qIolq0AAAAAElFTkSuQmCC>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABdklEQVR4Xu2VPS8FQRSGj69CQqOREFFoCP+BRCEhUVFoVVdBhUJN4g/4AxqJKDQidEpEqVKqiI+QiEbwnsxO7pl3996ZFc1N9kme5J53dmfOzn5ckYqK1qUNLnLYgHP4A1/hMo0pq/AOPsF5GrPoHI1sSDdc57AAnaQr+72U1Y/1YRmBY6aehL2mZjbFzdHsggJ64AaHxCk8puxEwoV2zZinxoHhTSI7yOhVxxr9EjfpgsnGs+whq0fhQH1YJmCfqZmiWz1MdUBKo4Nwn7IpcQvdmGwbXsAruGZypkPcuZeUc+MBKY0WcSZuYt25suh6eu6syfTROvCF3+5Uh9xpOfyOXPNAIu+SX0u1L2OOv+zop4S3vCy+Mc6aUrbRW3jIYQk6xTXFF/qvjR7BHcruqY6xJa6pOR6IkdqofqBXKOuHe5TF+JCE3SsipdFpyT/43hlzXApFz2cOXiSmfj8Vzq3t2TExdCf13+gZvoh787+DIyoqWoBfzpV3c2zzwI4AAAAASUVORK5CYII=>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABgUlEQVR4Xu2TvytGURjHH2FQQhmkiGRQGKXIKInJgsFmU1Z/gIxKNqXEgqQsIknJQEQpKRSDxSBKmfz8nvc9577P+73n9N7hTvKpT53ne577nPve916Rf9KlBrZySJRykAancBVOwhfac5TBH1dcwhM4AcfgKByBw1YfDaIGWGop24dv8BoOwH54b3t6XJMpQr66JsLta9Yo64CDdl0i2V9svIs6JHcn5n9qhk1WHu7Yg+8S37+irBhOq9rwRbWccwCOYRuHoA5uwWeJHz5FWS/sU/W8qMcdogtucGhxw32HV1KmX7hyoccdgoc6NmG9XfsONwzBD/gg2ZfX8a3WQZatTDU8UHXocB8LsFvVMxK41oSNHEq8OenhFfBG1dtwV9UR4+IfaO68hbKkh3MP1xG34t/cgUek6TOa9WKuNY8l2KnqIvHPz+AGJqFQb5Vkv3smeE2hgZpCvaG9UJ7Z+OSQuIBP8NFq1md5HSIrsJ0yxyxc5zBNDjkg5iThd/83+QWGr28xmVbQzgAAAABJRU5ErkJggg==>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAAB00lEQVR4Xu2UzytmYRTHj4Yyxq/NJCs1Cz/HcpKkWEhiZWeh/AMjlCRTkpGVkmys5Mc0bJWipGwtmImUxo+dHcWChfz4nvuc8zr3uGTxrjSf+vQ+53ue93ne5973XqL/pJciWOVDR5YP0sE2/A274YXrKR/hgxa9cBlWSl0OF2GPTjDkwWMKX95xvWLJlQ14BQ9gK2yBJzKnXif9lMC6q01DF4WeXrJheJnqEi1RfPNvsE3GmRROzP5LzaCwyBScgz/gB9sUPlNYONtk+kOVfVfzOqOmZu5cHW3Y6EOH34jJcfUAxec0wWZT8wFTl1sZordtvifjWgr33lNA8c3tHy6X3OVWBuEYhS/OyueM6VdI9gv+hZ/gtGSedngLT2Gnye/NOEYfXHcZL6z3q0NqvxkveOOyJPggdabWg76I3YwfEx6fPbUjNiV/jXx4aOpVuGZqyrCFwP9KXbhExgtP7YgVyfmRegn/43wdBecJmZ3IY34RWfgUnJe6XJmFNabmQyZu3p+Q+c2PTM38kTyJQgrPvefZ/GsKLxGlgcKkMpN9lczC9YjLFD9XScz5sutp2S/xdsR3Cj19t4/H2ynmYbUPhQl6fvvSypYPHJP0ynP//nkEKal5e00T7OcAAAAASUVORK5CYII=>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABsUlEQVR4Xu2UyyuFURTFt3ceeSRJBspUUkoGGEkSE+byH5j6A2SoRCkmigH+ACVJMZIYeJYUyVQGBhR57HXP/u7ddzlicGf8avV9a+1zvsd5ifyTW+pVLRwSRRzkggPVqmpc9UC1hFLVhw+KVXsWbvmCo1t1L6HNvio/uywNVkvYVj2qLlSDqgHVtbXpSRq1W1BlvsO8Z0417/yThDbNLluzLAHPGbL7Qgl/DF2lW0jocOwDy07JdzqfZP5lZ+QLVJPOgzdv6iR0WPShcmQ5KLd7Hg3OJsj3qfqdnxU33GBMQocZHyo7lifgD7qcB/xyTJv3fsFVCA03aJL4n99aXku5B/V3ykZUr6ob1ajLuV0aPOQkkkFYNDHQHvUyLkRYkOxRmxI3Qr1msN0A5g6LDRlvJ4CFhxrWy09Uqi6d31BtOp8CpxL297mqVTL7kamRkJdw4Rv4GeyjxOYTo8CdV8h7liR7e+bJ1/7p+eVsmDL+GJC1bx3VEvY9w+9JBTixEg7l67n8IpmPZMX4dd5m4Z1dccZ7Gi2P6dm1S1iWsG5iTKvWOcwluxwQONBiU/hH+AQIk35B4rOUBgAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABqklEQVR4Xu2UPShGURjHH/koJWQRk2RDMohIJklMShhsFimrnYxKNpNIIbMyWEykFIV8FGUw+loMPv/Pe85z3+c+nfNmeCf51a/3Pv/n3HPve+65l+if/FING21oKLZBPjiCG3AaPpqeUAq/pTiFh3AKjsMxOApHvEIVfCB34i2sUD2mxveEPfgKL+AA7Cd3Ho/plkFcxHzyY0rIXVgoINdvVdmmz4Q2OOiPi8j9Y/YmGUHZO+Hn1ADrvXqiZ3UsNMFPVZ9R+pxCOKdqRo/PcGwDcEBucoEnnVQ10+JzYcbUvbBP1UukljtGJ9w2GS8/T8zPUeDV0JPxHtAX1xuujMxyx9ATCLyEei/wheV5aobgO7wjt3mFL3UcZdUbopbSN3CebkdZhl2qnqfwH8yEdTYk9+ze/HEPZW+AX9NclMMrVe/AXVUnTFDkjiic31M419i+rROuKdwcpnDOcN5hQ88KbFe1fBuCyFJa+EMSyplYXknuvbfExkcvznA+azKuT0wm5JonCDc+bKh4ITfm0v+up9sJa7DZhp4FuGXDfLJvA8Mi/fK9/5v8ADb2cUf8vrK7AAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABVklEQVR4Xu2VPS8EURSGj9BIaLYkopAIiX+g0JNoRCsqNFQo1Fv4J1p/QVSEWqFEIb4losN7nLnJmXfGzL2zmk3mSZ7snDNz5773zs6uSEtL/zIAV7kZwTtcod42vIaPcJnOeb4r/JNhuMvNGjbFbuqDTsFZVy/AUVcz+2L3qFpQjhG4x80aHqQY9NAdB7a44XiTmh1kdNUpQV+zTw46A8dcPQc7rmbKHvUk1TlSgq7B9eyYgypdeALP4Q6d8wyKjT+jPgfPkRJUX6BAWdBYdD4dv+h6x/AoFGG7Y52wYb/ci/1CBHoJqgvmuVT/MhaI2dElKT7KXoKGYNyrJCboJzekedAhsbGX1P+XoKfkhdiNr7I6hQOxsfqUkogJykxL8x39kIjdK6NJ0HmxyTb4RARl388C4aJYx21Yjhd4B2/gbVbHoDup/0ZP8Fnszf/KXdHS0gf8AHFxbvHY6miQAAAAAElFTkSuQmCC>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABpUlEQVR4Xu2UvytGURjHHz9LCSXJRLIhpaTIJEksLBhksSmrP0BGJRuLWJBZSVIsJAY/C0WyUwaLn9/HeQ7Pfd5z6g7vxqc+ve/3e8+5773vOfcS/ZNdKmG9LQ0FtsgGh3AFTsBHc8xTBD91UQj3pNzSB4QTeADH4QgchkNwUGSqKHnSbfgML2Ev7IG3MqbDD2qWolRyi2QN55hPMmZVsofP0yff88ndMXvzM4LcBL4z252ZzFfLa1kHa0X9Y+cm58EplZl3HSrITVjQJTiWXmfLPmxQeZKSc7pgt8pzpP5uZpTchFldgh3pY7TBddPxsuk5esMVk/m7mWoK3/m99OWm98QubAC+wjtyG9Pzob4n4BOdBjqWN41lSUzLPGxXeZrUxXdK4MeN4bXjzcZdrh+k4L7GlhFK4JXKG3BT5W/4rcTP9wVspN/n0TJG4T6GHWtzEB4UWqdrSnkCsAhbVc6hwFy/vrbrNx0TGhuijNxzb8mYy8WLykcUfy+n/fHYmIy+ScoH+eR3fAw+/mZLwzK5fRNiBq7ZMpvs2sLAL7TQfvojfAHZ9nPup9e50AAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAAB0UlEQVR4Xu2UzSttYRTGl89SQnQTE38AEnVzS7oDSWJCGcrYxNScDNXtzpjcknL9AUqSYijKd6QIZehrwEA+1rPftc5ee51z9uiM5FdPZz/PWvvd+7zvu1+ibwpLPavZh44yHxSCbdYSa4J152pKBevDBrWsWwkvWNW2KJSztij0rLkaaKDkoOusJ9YJa4DVT2Fs9HRrEwbFg5UiCg3tJuuQTF/qp3jLf5ehZ1CuSyn8Y+g808E8WCO0sN6Mx6D7xmt2aPyRZEoJa9p4YMeMwA3jLmuTHPyQ6/m4HLEruTLpfC+rz/i/ZKZbuadwE9ZIwWxo4xiF+p+4HLEhuYIlsd5uuEpy061genCTCg/WtQJNkvt/fiV5ncmGWa+sS9aoyd/NdRaNlHyB42Q5yg5yZBA2VhpzrC7jZ8jMENblRa5/SwGyG6xHMnwZAOuLzYasWJtyUMU6M36FtWp8/BaGa8rOcXLh+8astFL8zabh6wk/4gMD8l8+NKCetpb/WJ3G6/mRAQdJ2sPtte+DH3KZUkPhu/f4MaJgymXwe8aj59n4Hcp/doOshwg580cKhVP5XUyWM4fOjfzijM/HAoU9kYtZ1rIPC8mmDxw4rNL2yhfnE46YfxOd7gUqAAAAAElFTkSuQmCC>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABeUlEQVR4Xu2Vu0oEQRBFyweooIiGPjAwUfAfDExEwUgTYY1NNFIDwUzQL/AXTI3MBRUUDEXwkQhmvkE0EPXW9gzU3G1nStlkYQ4clr7dXd3TO70rUlLSuDTBOQ4jPMMK7IHdcBY+ZUaILMEreA9nqM/yneOvdMAVDiNwQXXA9A/DUdMeh12mzaxJqJH3QBk64SqHEbToFtyBE9SnbHMAFjkwvEjBCTL61N6N5jEC+0x7DPaaNhP7qoeonaFeG1U24QE8hcvUZ2mRUO+E8tw1/rLRS3gOj+EnbM2M8KPrab0pk+3B3bRhL4LHwTCtirbbTHs/yf7Dq9SupdrLWIP3RBl9J7X4Bnc4SDfGWS7ejep7ZWmWUPyC8iL0ddF5Z5TXZaPXEgq1m0x/1jQ7NJmHdQnzprmjCM9Gb+EbZZMSFpynvAitU3h6MTwb1Ut1Q9kHfKfMQ+z9rCEd5LU/TKuykGR3yeeR6fOgJ6n/Rg/wUcLN/8qMKClpAH4AWJlzaNhdqpAAAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAUCAYAAAD2rd/BAAACRklEQVR4Xu2WTYiOURTHj4+UEiLJbJTNyEeiRElmkqSZDWUpaxshkijlYzklOzYTqWFnY0FSLGXyLVKEsvO5YCEf//9zznk798x957HSlPnVv+ee/zn3Pvd53nvv84pM8v+xEFqezYnKXWgE2gt9TLkxzIDuQL+hGynnzIPei9a8guaU6a7sh65AyyxeCl2C9nUqRBaJjuvchL5Cz6ABaJvoPRvWiBb7BNZaHOEDcbLOFNGa1cHrxinR2qj7RYXIZfMdzmHQ2tOhmaYGFj70IHiPQ/w5tJ0V0M9sVjgOnYUuQMegaWW64YmUE2bNyRCT5l4LRAvPlzkZNd9he0+IySrz2+Ak+7OZOCzlWFugrSHmA29kY7do4ZmQJLfMdz5ZzLXl8K03g7RwVNonzOUY7xc33SzopQeLpf6G35g/32L+RIxdnKyvsTaOQKdF+w3b9VxRoeyAfkCvoV3B/xXaDRzgUcWjuPidnuBTT0NuPA5A15PH/nmN1uCDbcjmZtEBeBIQriduOHpTzeN6+m7tTZaj8mb9W7z/eMyGXoT4Wmg3Xxiev3xrK0XPvDhgbfC3UvczPAIz3PFtfXM+xwVM+trZaXEN+uuzmWDNh4rXbUwyDK0LsZ/7DbXOjLdbmx+HnHeyz4fjrxVhzaGKl/s6c0XP5Uwx4W8hcU/GfstZcyJ5jB+E2N9CngjH5nnv9InW9AYvkvs7Hd8/AO/syv8UNb6I5p/blf8HMlehg9kUXRL+MNSSMt3hougeqjGUjYnA7WxM8i/5A6VFnzkmljmzAAAAAElFTkSuQmCC>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAUCAYAAAB1aeb6AAABqklEQVR4Xu2UyyuFURTFt2cpoSQpMlWSUjKQkSQxYS7/gak/QIZKZqSUCQbKRCQpzLzKs6RIJgYyUEzksZZvH7Z9z4fBHcmvVvfsdfY5+7vnJfJPdqmE6r3pKPBGNtiGZqFB6M71BYqgV2sUQptqrtqOFGrFTQCqnLcG3UOnUDfUBV1oTltIalKjVONmjb+D/T5nznmcp0fb+ZL8Y+r8I0OSAQfWUO/IeQGuzINkFj92Xh40bGLybIMKSQZMWhPsqe+phhahW8nsH3JeB9Rp4nExy00GJBkwZk2wrr4neLHi3Dbr2QNXLG65Sa3E//mV+uXGW4BqtB0rTvqgJ+gS6jf+i2l/gZMcRjyKh4bwI7gagbTiMSagVhOPiBnbrgGvG+He8bDRy1XPF/pt8RLozMRL0IqJ3+GrxFN8AjXI530k/PI6bQd+W9zn+DgKk8I+LUNbTmFb2J7SPM801GLiHIkUDxN5r9d5ltgYS5kk996TMYbGo4l3Jf1dDvxUPK0vw29U81p/+cansQ/dSJJLsb3zJUNkRpJzE2MUmvdmNtnwhoMPWuq9//u8AT3cfP0s2TQhAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAVCAYAAAAw73wjAAABeklEQVR4Xu2Vuy9FQRDGxyMeCY2Si6AhRKlVieRKdP4HDRUKKolCq1YotUqtSkj8BUqJxiMhoSAe35g915w5e3fXUd3k/JIvOfPN3dnZ3XPuElVUtC5t0Io1A+xAH06LJrcGXUP30LLJab4CakovtGHNJrxDh+65G/qEelw8AU25Z2Ye6lexZYuksdCCcvRBm9b08ADdqfiAZKI5F++rXMaqNRRPFNlBC6861ugYSdER48+q50loUMUz0ICKLb6jHjVxjpRGz+m3aBe0oHKaPegMuoTWTU7TQVLvwvi28RwpjWarPyZ596ZdzMdfBp6Px9eVd0JS/4dswlQNy7BGvOtiZtx5NeWl8kzFuVj6Yyzwlx21sHdrzQR89Wxc4L+N+vwQnSRjrowfrZPSKL/0vkJlGt0mGbNkEzFSGuW/Hl9D7B1ZM8IL+WtFSWmUeYVOVcxXaZkJk04h+1GqhmRYgxvnv5Fcn+35dBDeSb6N+IZ7JPnyuUZFRUvxDZwDeMDlrZy3AAAAAElFTkSuQmCC>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAUCAYAAAD2rd/BAAAB+klEQVR4Xu2WzyttURTHlx8pJUQvMfEHIFGi9HoDSWJCGcrYxEiZM1YyY6JerxiamEiKoSi/I0Uow/cwYCA/1vfsva511j3n3v0mUnzq2z3ru757333P2eecS/TN16OG1WDNz8oWa5E1xvprelmUsDZZr6xV0xNCMmlUsW7IjT1nVcTbVOt7whrrnnXM6mP1khsX0UouLJO0+VoTkkkDPxSLFQrIjW1R3pL3BMzf74+LWaVeEQjuSaG8A1Pny6Rxaw2mkfWs6kOKL7iINaVqEOV/kAvOx3u0430QkskFMqPGa/a+MGHqblaPqmdZP3EwQi44o5pg3fsgJJOLf+Ry2JcCznq0AA+2mp5L33RlrDMp6in57F16v5rCMrnA5UVOhMXK/tQMsp5YF6xh5b+o4whMsp/gQdj8UufL5KKO4os+irdTmWN1WrOL3CS4mwH2E24meIX/kUkDe/HRH/+i90Xbm9hSzjpV9Yo6jt4weLbilzeRe+ZhUk1IJomkzBUl+xrbt3UMNLP2jiEkM0TpXwS/w5qeBVa7quXZHSGXSIN6wNT5MgALxJUQ8HKw44Q0v5Lcc9kSW/CDamxT9rs8JCNnwS4E9aTxUO8aT7DjhYwvD/Fr/4n/C5aQDFhmjVuTuSM37sR//om3M/wmd38kMW2Nz8CGNb75SN4Abz2mhZwvO6sAAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABUklEQVR4Xu2VTStFURSG35KvbiJTM5mYXDI2M5GBlIFfoPwAXWWoDJQBSgYyU8RUBmaMfPwNyYCQASUf72rtU+ussx373pk6Tz3ds9511r77nn3qAhUVvzNCH+k3vaR9+TYG6Ru9oYeuZzmDrpFijgW6Zep96E1jJtsz1220YeoY0S8KHNEPH8YGbNYdtNy72iKblNlr3wj00HMf3qJ8E8KauRZWXW1ZhM5OurwrfPbSFduIsQxdZMpko/QOelQXJo/xguKPkjWHwnU7rZlegRnoApu+0QT+KQ67upR16EvzSSdcL5XsfYjZFAPQoRPfSGAJOjttsjo9NnUyLe2evKI4Nw89klLk8e+6LNvEuMv/oqXNzyI+mGVyxql0QGeufCMFGew0tZyhZKcmS2EDOjfnGyn006/gA3Sh7dwd5RxA34Un6P/PM32nO/amioqKf8kPUkRfDIYtM50AAAAASUVORK5CYII=>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAYCAYAAACMcW/9AAABQklEQVR4Xu2VMU5CQRCGJ9EDUNgTS87ADSCh4RRCMJgghWfgCLbGGBsrCjpKClouII0xkmBiY6HOZFgdf9zdeZ0k+yWT9/affyeTt/t2iQqFw2PEcYYikPLMOaYcHxw1yFk+ndEME4RbjneT7NnkDo/nGsYzGCNj0lodTDDHpLkjTARiTVhiHtEtDRgjW9qfY5FViRJrwhLz3MD4DsZIWB1L3bxj7hexJiwpz4p0C7xwnELOIksqdRag2+a65n2PVBMBjyfHJWmdltEeSP8FFzK5jyLg8eR4pZ+lt5Hb19+IeYAi4PHkCI2h5kbM5ygCHk+KcPQsQa/c6BBFwONJcUVao42JKkiBCxQBjyfFG1X8esgJaYEJJgweT46/9qeLe45njjXH4+75RHplVvHkkC8pt5GcsRvSPz95+xQKhcI/5wtUCGwv4IDWHAAAAABJRU5ErkJggg==>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABOUlEQVR4XmNgGAWjgDggD8T/0cSUgPg7EJ8G4hVocshgFwNELzEYL8CmaC4SmxmIy5D42AA2M2BgFRD/RhdEBiCffGVANYATipHBCzQ+MgA5EqT/FLoEFPAC8UF0QRiQAeINQPyGAdMXnWj8VjQ+MihhgOj3QBPngNL8QNyELIEMYBZjc4QBED8D4iVAfAhNDh18ZMDUXwXEKlA2KxBzI8nBwVogloWysTmCFICeHjTR+FiBMBDvQ+JT4ghYesCG8QJ0BZQ4opwBotcPSUwPiFcj8THATCDWQBOjxBGfGTD1pjJAogQn2A7Eh9EwLPhA7DkIpUQBooKeGECuQWwMEH0n0SXIAeQ6YgIDRF84ugQp4BwDpCR8DMUgNqiuIASWM0DSwnsgfgvEH4D4BxBPR1Y0CkbBKBiSAAB5HF6q+uADAQAAAABJRU5ErkJggg==>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABM0lEQVR4Xu2UsUoDQRCGB0QxSLDxCcQmjfgYVmnzBClUDAohgqWQQrCws7ILJMQ3sNNOfQyDKCKJWCha6D/uCpP/NtxuKewHH3czszc3yS4nksmU04ZbnASr8B3ewQHVLJfwO9Ip+vDTF9Tt6fIv5+Z+DnZMHCL4Is8QfnHSEhqi4rU8UmzRIbXPLRc8VXjFSUtoCOWY4i7FFt1S7bNJ+UV/XYZHtsDMGmIDPsAevKYa8yrFrTiEa/5+Hi6ZWoFZQ6TA56FGcSm6eIeTCfydh5DR6OJdTiZwIK5H3eTW4YWJS9EGLU4m8CbFX90UtyXRaIM9TiaQ/NeH0Ab7nIxkQdzzN1xIYUVckxMuRHIq7vkGF2LQQ/MMR/DeX5/Efcpj0M++noUxfIET+AHP7KJMJvMv+QHYYVFcAwJFwwAAAABJRU5ErkJggg==>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAYCAYAAACMcW/9AAAB1UlEQVR4Xu2VzytFURDHx49IFkSysJClhR8pSWRjRyk/N5KdtQ3K0l8gS9lKdlYWFordCwvEUsmaosjGj/neM+fdufPu886ze3U/Nb2Z75y5755zz5lDlJFROdSxnbP9sJ2YnKeRXA5jLtiqkumIM7Zjtm+2ZpPT4BkhNuILwICITRIPSqzpEK1B4laJq/MjiPaUD4pN2LNO7hlTNsHUksvVaBHCtRZEu1XxO9uhisEl26eK7eS6TWx5pcIaDb5KnjZyg3e1yFyJ7oG/oGKwKbpnX/nATsziP6+mU/mJ3LII21pkTkUHY+KPxukIX9uitHtyW+CZrUvpFnxS1OaMrl9uVvnRDJC0K/ooOvbiqvjYy5p50YeMHsIaudoJpR2xHai4ABTcpGgwHKwt8XsTI4imRV80eghvFP+Htj/39Ti5QWhRYIPcQYKGU70ifr/kPXOio75c/ItZrSTt5NrJHVsP2wPFhX6PDkvsWRIdrascfOvBgdUEvagFRb491Etc6tSH4usmbaIUxT4D9qCOd1QMcAPZuhDQk/9TFxV9qBiN/EXFIG31EM8YLYS0hQmij1zhk/zizk8DreNLfjEObascsJK4jdBjsRA4+YnbJyMjI6PC+AWh0ovoWT+7dgAAAABJRU5ErkJggg==>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAYCAYAAACMcW/9AAABnUlEQVR4Xu2Vuy8FQRTGjxAtUWo8ohES0QkRpQTRiFwKnUbUFEp/h0ZCRDQqhWhUKCQURBQKhc4zEY3X+e7M4czZ2c1dV3OT/SVfds535szM7uzOEhUU1A4trDvWF+uG1RSm6Zx1zFpkzbFmWTOskpdwyNpjfbKalW/BPJVoSApAI7lFCnXkOvUrzw6g9ej7rPmrsG9iyzK5+kmbYBrI5eq1+aQDTy/rQ8UoGmb1sLpYnV7wdR9Nt4ktz5Ss0WBXAtB5wXh93hdOVVs4IndDwqZqg20TW2RHNG2qbXPlrYN5oDw8ZTzBNAZZO9ZkLsm9AvesDpPTYEsx54nx9eKmVLuMFImwyImgR5LE3eZkidwYY8rbZW2pOEorhYu9CNMB617V8ELhfKLM93qU9ebbI/RbhCMpBnLt1syJzGG9TGIdbinuz1Pcz4McPfYDzRx3mtI7wB8w3rX3q2GF3BjjNpEFDvW0iWN+bMvy8kp/HANFq8ZDfGY88B8LrWoM+Utc+etGmP4BuXdrVgieJObBGftA7stP/H0KCgoKaohvXJp/0gSqQWkAAAAASUVORK5CYII=>

[image35]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABSUlEQVR4Xu2Vu0pDQRCGB8VLIiIWVnZiYxPsLPQBrGx9At9AFFIqFnYBQSsrBUXfwE4rL50PIRaKiqCiePmH2QOT/6yeTTphP/jIzszOnt1kORHJZH5nDt7Bb3gOe9rLMgFf4RU8pJrnRGyNFNvYgtsufhGbpA8u2HXjXrji4hjRBwWO4AcndfJMJFcsUgt6bin26Ca195ILgWF46hNDEt815zbdWNmg2LMs1jtP+cHwOQLXfEFZh7OU401Mwxu4D89cPsaTlA/VhJNh3Cd2+Ep0kS9OJsIHmKI4iWuxpjoXEijuQ8xk9IJqwxgXElkV619wuQY8dvGfjIotMMCFDniW8qmXxH6SSvTlxM17FKfQ8VfviV3CT05U0C+2gQsupPAu5UvUzYlaYj2LXKhiXMoPLtT/ihQOxO7CA7yHj/AN7vhJmUzmX/IDtAhf7hHHLI4AAAAASUVORK5CYII=>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAYCAYAAAC8/X7cAAABmElEQVR4Xu2VOywFURCGRxCKS6HUKBRIlDriqkk0ColaoaGRS6JWiFKjFY1EgegVdCQ6nUYjSDxCPEIE/+TsyZ1MZnfPbm7nfMmf3fkn5zE7J2eJIpFII9iFfqFPaFnlmHnoErqHJlVOwnOEaNgPaAQ8YaeKv0TcCw2IuAp1iFizRG4Oq9AWcrlmnbBohWraVIySm/BIeE+J15fEayLnmdOG4Jnc+DR+tJFGO+UX4L/IuvDeE893pR/qrqdpEOoSscYfE0mPeNe5VCqUX4CFtYFV6Bg6gxZUTsJHg8eeKl/ONyXeM+FzWqQA7sYFuRY3qVwovB5vdlx4B9COiIMpUsAMtAndQYcqV4QXqndQSl4CJkOGqtCG4bOyuCW3aJkuWMdPxyZ8ZWlNQ1uGb11vkkVyi97oRA7+QjhXflABFiFHaBv6Vt4I2V8yjxVyYyZ0oiwhBfiNjglvNvGuhRfCGxUvOpOQAvahE+W9kttIm/LzKNO1TEIKYPbILXyVPD+o2Ob5y/Pf9wF6JHcTBf9tswgtIBKJRP4xf2R6bBzQCSUEAAAAAElFTkSuQmCC>