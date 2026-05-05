# Kalshi Read-Only Market Integration

## Scope

This module provides a strictly read-only integration with Kalshi's public market data API. It is designed to fetch market metadata, discovery KMIA-relevant temperature markets, and retrieve order-book data for probability comparison.

## No Real-Money Trading

The `KalshiPublicClient` does not implement any authentication for trading, nor does it contain any methods for:

- `create_order`
- `cancel_order`
- `place_order`
- `buy`/`sell`

All trading endpoints are explicitly excluded from this integration to ensure safety and compliance with the project's read-only mandate.

## Market-to-Bin Mapping

Kalshi temperature markets often use subtitles like "81° or higher" or "79° to 80°". Our internal system requires mapping these to specific probability bins:

- `<=78`
- `79-80`
- `81-82`
- `83-84`
- `85-86`
- `>=87`

### Mapping Logic

The `weather_market_mapper` uses regular expressions and keyword matching to identify these ranges.

- **Ranges**: "79 to 80", "79 through 80", "between 79 and 80" -> `79-80`
- **Lower Bound**: "78 or lower", "78 or below", "at or below 78", "below 79" -> `<=78`
- **Upper Bound**: "87 or higher", "87 or above", "at least 87", "above 86" -> `>=87`

### Safety and Uncertainty

If a market subtitle is ambiguous or does not fit our defined bins, the mapper returns:

```json
{
  "mapped_bin": null,
  "uncertain_mapping": true,
  "reason": "..."
}
```

This ensures the system flags the data as unreliable for automated comparison.

## Order-Book Conversion

Kalshi provides separate bid lists for 'Yes' and 'No' contracts. In binary markets, these are mathematically related.

### Conversion Assumptions

- `yes_ask = 100 - no_bid`
- `no_ask = 100 - yes_bid`
- `yes_mid = (yes_bid + yes_ask) / 2.0`
- `spread = yes_ask - yes_bid`

Prices are represented in **integer cents** (0-100).

## Known Risks

1. **API Rate Limits**: Public unauthenticated endpoints may be rate-limited by Kalshi.
2. **Text Format Changes**: If Kalshi changes the subtitle format significantly, the regex may need updates.
3. **Connectivity**: Since this is a live integration, network issues can prevent real-time updates. The system uses mocked data for all core logic tests to ensure stability.
