# GME API Fixes and Improvements

## Overview
This document details the comprehensive fixes applied to the GME API client based on the official technical manual (20251015Manuale_tecnico_API.pdf).

## Critical Issues Fixed

### 1. MI Market Segment Names
**Problem**: The API was using incorrect segment names for intraday markets.
- **Before**: `MI1`, `MI2`, `MI3` were sent directly to the API
- **After**: Correctly mapped to `MI-A1`, `MI-A2`, `MI-A3` as per the technical manual
- **Affected Markets**: MI1, MI2, MI3 (first three intraday sessions)

### 2. MSD Market DataName
**Problem**: MSD (Ancillary Services Market) was using incorrect DataName.
- **Before**: `MSD_Prices` (which doesn't exist)
- **After**: `ME_MSDExAnteResults` for ex-ante data
- **New Method**: Added `get_msd_ex_post()` for `ME_MSDExPostResults`

### 3. MB (Balancing Market) Support
**Problem**: MB market was not properly implemented.
- **Solution**: Added dedicated `get_mb_results()` method using `ME_MBResults` DataName
- **Route Handler**: Special case handling for MB market requests

### 4. Gas Market Segment Handling
**Problem**: Gas intraday sessions needed better handling.
- **Before**: Each session sent separately
- **After**: MI-GAS1, MI-GAS2, MI-GAS3 all map to `MI-GAS` segment correctly

## Data Structure Improvements

### Response Parsing Enhancements

#### Date Format Conversion
The API returns dates as integers (e.g., 20241115). Added automatic conversion:
```python
if isinstance(flow_date, int):
    flow_date = str(flow_date)
    if len(flow_date) == 8:
        flow_date = f"{flow_date[0:4]}-{flow_date[4:6]}-{flow_date[6:8]}"
```

#### Multi-Source Price Extraction
Different endpoints return prices in different fields. Now supports:
- `Price` - Standard price field
- `AveragePurchasingPrice` - For MSD ex-ante/ex-post
- `AverageSellingPrice` - For MSD ex-ante/ex-post  
- `ReferencePrice` - For environmental markets
- `WeightedAveragePrice` - For environmental markets

#### Volume Aggregation
Properly handles different volume fields:
- `VolumesPurchased` and `VolumesSold` for MSD
- `Purchased` and `Sold` for XBID
- Takes the maximum of purchased/sold for display

### Frontend Data Handling

#### Enhanced Data Normalization
```javascript
{
    date: dateVal,
    interval: displayInterval,
    period: periodVal,
    price: parseFloat(priceVal) || 0,
    volume: parseFloat(volumeVal) || 0,
    zone: zoneVal,
    product: productVal,
    category: typeVal,
    type: 'actual'
}
```

#### Improved Table Display
- Shows period information when available
- Displays zone/product information
- Better formatting for different market types

## Technical Manual Key Findings

### Electricity Markets (ME_*)
| Market | Segment | DataName | Description |
|--------|---------|----------|-------------|
| MGP | MGP | ME_ZonalPrices | Day-Ahead Market |
| MI1-3 | MI-A1, MI-A2, MI-A3 | ME_ZonalPrices | Intraday Sessions 1-3 |
| MI4-7 | MI4, MI5, MI6, MI7 | ME_ZonalPrices | Intraday Sessions 4-7 |
| MSD | MSD | ME_MSDExAnteResults | Ancillary Services (Ex-Ante) |
| MSD | MSD | ME_MSDExPostResults | Ancillary Services (Ex-Post) |
| MB | MB | ME_MBResults | Balancing Market |

### Gas Markets (GAS_*)
| Market | Segment | DataName | Description |
|--------|---------|----------|-------------|
| MGP-GAS | MGP-GAS | GAS_ContinuousTrading | Day-Ahead Gas |
| MI-GAS | MI-GAS | GAS_ContinuousTrading | Intraday Gas |
| MGS | MGS | GAS_ContinuousTrading | Gas Storage |

### Environmental Markets (ENV_*)
| Market | Segment | DataName | Description |
|--------|---------|----------|-------------|
| TEE | TEE | ENV_Results | Energy Efficiency Certificates |
| GO | GO | ENV_Results | Guarantees of Origin |
| CV | CV | ENV_Results | Green Certificates |

## Response Structure Examples

### ME_ZonalPrices Response
```json
[
  {
    "FlowDate": 20241115,
    "Hour": 1,
    "Period": "1",
    "Market": "MGP",
    "Zone": "PUN",
    "Price": 125.50
  }
]
```

### ME_MSDExAnteResults Response
```json
[
  {
    "FlowDate": 20241115,
    "Hour": 1,
    "Period": "1",
    "Zone": "NORD",
    "VolumesPurchased": 150.5,
    "VolumesSold": 120.3,
    "AveragePurchasingPrice": 130.25,
    "AverageSellingPrice": 125.75
  }
]
```

### GAS_ContinuousTrading Response
```json
[
  {
    "FlowDate": 20241115,
    "Market": "MGP",
    "Product": "GAS-D+1",
    "AveragePrice": 45.30,
    "MWhVolumes": 15000.5
  }
]
```

## Files Modified

### 1. `/src/gme_api/client.py`
- Fixed `get_electricity_prices()` method with correct segment mapping
- Fixed `get_electricity_volumes()` with segment mapping
- Improved `get_gas_prices()` with session handling
- Added `get_msd_ex_post()` method
- Added `get_mb_results()` method

### 2. `/src/web/routes.py`
- Completely rewrote `parse_gme_response()` function
- Added date format conversion (integer to YYYY-MM-DD)
- Added multi-source price extraction
- Added better volume aggregation
- Added special handling for MB market
- Improved error logging

### 3. `/src/web/static/script.js`
- Enhanced `processAndRenderData()` with better field extraction
- Improved `renderTable()` to show period, zone, and product info
- Better handling of different data structures

## Testing Recommendations

### 1. Test Each Market Type
```bash
# Test MGP (Day-Ahead)
curl -X POST http://localhost:5005/api/price-data \
  -H "Content-Type: application/json" \
  -d '{"type":"electricity","market":"MGP","start_date":"2024-11-01","end_date":"2024-11-01"}'

# Test MI-A1 (Intraday Session 1)
curl -X POST http://localhost:5005/api/price-data \
  -H "Content-Type: application/json" \
  -d '{"type":"electricity","market":"MI1","start_date":"2024-11-01","end_date":"2024-11-01"}'

# Test MSD (Ancillary Services)
curl -X POST http://localhost:5005/api/price-data \
  -H "Content-Type: application/json" \
  -d '{"type":"electricity","market":"MSD","start_date":"2024-11-01","end_date":"2024-11-01"}'

# Test MB (Balancing Market)
curl -X POST http://localhost:5005/api/price-data \
  -H "Content-Type: application/json" \
  -d '{"type":"electricity","market":"MB","start_date":"2024-11-01","end_date":"2024-11-01"}'
```

### 2. Verify Data Fields
Check that the response contains:
- Properly formatted dates (YYYY-MM-DD)
- Hour/interval values (1-25)
- Price values (float)
- Volume values (float, can be 0)

### 3. Check Error Handling
- Invalid date ranges
- Non-existent markets
- Authentication failures
- Network errors

## Common Data Issues and Solutions

### Issue: No PUN data returned
**Cause**: Filtering was too strict, only showing zone='PUN'
**Solution**: Now shows all zones when PUN is not available, or any data with prices/volumes

### Issue: Integer dates in response
**Cause**: API returns dates as YYYYMMDD integers
**Solution**: Added automatic conversion to YYYY-MM-DD format

### Issue: Missing prices for MSD
**Cause**: MSD uses AveragePurchasingPrice instead of Price
**Solution**: Multi-source price extraction from multiple fields

### Issue: No data for certain date ranges
**Cause**: Markets may not have data for weekends/holidays
**Solution**: Better error logging and user feedback

## API Rate Limits
According to the technical manual:
- Maximum concurrent connections
- Maximum connections per minute
- Maximum connections per hour
- Maximum data downloads per minute/hour

Use `/api/v1/GetMyQuotas` endpoint to check your usage.

## Future Enhancements

### Recommended Additions
1. **Offers_PublicDomain**: Public offer data for all markets
2. **ME_Liquidity**: Liquidity statistics
3. **ME_MarketCoupling**: Cross-border market coupling data
4. **GAS_IGIndex**: Italian Gas Index
5. **Additional DataNames**: Support for all 52 DataName types in the manual

### Performance Optimizations
1. Implement response caching
2. Parallel date range requests
3. Database storage for historical data
4. Batch processing for large date ranges

## Support and Documentation

### Official GME Resources
- API Documentation: https://api.mercatoelettrico.org
- Market Results: https://www.mercatoelettrico.org
- Technical Manual: 20251015Manuale_tecnico_API.pdf

### Internal Resources
- README.md - Project overview
- plan.txt - Original requirements
- test_gme_api.py - API client tests

## Changelog

### 2024-12-14 - Major API Fixes
- ✅ Fixed MI market segment names (MI-A1, MI-A2, MI-A3)
- ✅ Fixed MSD market DataName (ME_MSDExAnteResults)
- ✅ Added MB market support (ME_MBResults)
- ✅ Improved response parsing with date conversion
- ✅ Enhanced multi-source price extraction
- ✅ Better volume aggregation
- ✅ Improved frontend data handling
- ✅ Enhanced table display with period/zone/product info
