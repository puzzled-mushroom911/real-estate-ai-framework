---
name: cma-generator
description: Generate a Comparative Market Analysis summary for any property address. Use when asked to create a CMA, analyze comps, evaluate a property's market position, or produce a market comparison.
---

# CMA Generator

Generate a Comparative Market Analysis summary that can be used in YouTube content, client presentations, or lead nurture emails.

## Process

1. **Gather property data:**
   - Subject property details (address, beds, baths, sqft, lot size, year built, features)
   - Pull comparable sales from available data sources
   - Identify active listings in the same area for competitive context

2. **Analyze comparables:**
   - Select 3-5 best comps based on: proximity, recency, similarity (sqft, beds/baths, condition)
   - Calculate: price per sqft range, median sale price, days on market average
   - Note adjustments needed (pool, garage, renovation, lot size differences)

3. **Market context:**
   - Current market conditions for the specific neighborhood/ZIP
   - Inventory levels and trend direction (increasing/decreasing)
   - Buyer demand indicators
   - Seasonal factors affecting pricing

4. **Generate summary:**
   - Professional but accessible language
   - Price range recommendation with confidence level
   - Strategic recommendations (pricing strategy for sellers, offer strategy for buyers)
   - Key talking points for on-camera delivery (if for YouTube content)

## Output Format

```
## CMA Summary: [Property Address]
### Date: [YYYY-MM-DD]

### Subject Property
[Key details]

### Comparable Sales (3-5)
| # | Address | Sale Price | $/SqFt | Beds/Baths | SqFt | DOM | Date |
|---|---------|-----------|--------|------------|------|-----|------|

### Market Analysis
- Suggested price range: $XXX,XXX - $XXX,XXX
- Average $/sqft in area: $XXX
- Average DOM: XX days
- Market trend: [Buyer's / Seller's / Balanced]

### Analysis & Recommendation
[Personal analysis and recommendation]
```
