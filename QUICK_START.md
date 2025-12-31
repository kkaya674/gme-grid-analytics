# GME API - Quick Start Guide

## Recent Major Fixes (2024-12-14)

This application has been completely updated based on the official GME API technical manual. All market data endpoints have been fixed and tested.

### What Was Fixed
- ✅ MI market segment names (MI1-MI3 now correctly map to MI-A1, MI-A2, MI-A3)
- ✅ MSD market now uses correct DataName (ME_MSDExAnteResults)
- ✅ MB (Balancing Market) now fully supported
- ✅ Response parsing handles all data formats (dates, prices, volumes)
- ✅ GUI displays period, zone, and product information
- ✅ Gas market sessions properly handled
- ✅ Environmental markets improved

## Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
GME_USERNAME=your_gme_username
GME_PASSWORD=your_gme_password
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

#### Option A: Using Flask directly
```bash
python src/app.py
```

#### Option B: Using Docker
```bash
docker-compose up --build
```

### 4. Access the Application

Open your browser and navigate to:
```
http://localhost:5005
```

## Testing the Fixes

### Run Automated Tests

```bash
python test_api_fixes.py
```

This will test all major markets:
- MGP (Day-Ahead)
- MI1-MI3 (Intraday Sessions)
- MSD (Ancillary Services)
- MB (Balancing Market)
- MGP-GAS, MI-GAS (Gas markets)
- TEE (Environmental)

### Manual Testing via Web Interface

1. **Select Market Type**: Choose Electricity, Gas, or Environmental
2. **Select Market**: Pick from the dropdown (e.g., MGP, MI1, MSD, MB)
3. **Set Date Range**: Choose your dates (recommend starting with 1-2 days)
4. **Click "Fetch Data"**: Data will be displayed in chart and table
5. **Optional**: Generate forecast or export to Excel

### Expected Results

For successful data fetch:
- Chart displays price trends
- Table shows hourly/interval data
- Data statistics appear above the table
- Export and Forecast buttons become enabled

## Available Markets

### Electricity Markets (ME_*)
| ID | Name | Description |
|----|------|-------------|
| MGP | Day-Ahead Market | Main day-ahead electricity market |
| MI1 | Intraday Session 1 | First intraday session (now uses MI-A1) |
| MI2 | Intraday Session 2 | Second intraday session (now uses MI-A2) |
| MI3 | Intraday Session 3 | Third intraday session (now uses MI-A3) |
| MI4 | Intraday Session 4 | Fourth intraday session |
| MI5 | Intraday Session 5 | Fifth intraday session |
| MI6 | Intraday Session 6 | Sixth intraday session |
| MI7 | Intraday Session 7 | Seventh intraday session |
| MSD | Ancillary Services | Services for grid balancing (ex-ante) |
| MB | Balancing Market | Real-time balancing market |

### Gas Markets (GAS_*)
| ID | Name | Description |
|----|------|-------------|
| MGP-GAS | Day-Ahead Gas | Gas day-ahead market |
| MI-GAS | Intraday Gas | Gas intraday market |
| MI-GAS1 | Gas Intraday Session 1 | First gas intraday session |
| MI-GAS2 | Gas Intraday Session 2 | Second gas intraday session |
| MI-GAS3 | Gas Intraday Session 3 | Third gas intraday session |
| MGS | Gas Storage | Gas storage market |

### Environmental Markets (ENV_*)
| ID | Name | Description |
|----|------|-------------|
| TEE | Energy Efficiency | Energy efficiency certificates |
| GO | Guarantees of Origin | Renewable energy certificates |
| CV | Green Certificates | Green certificates (legacy) |

## API Endpoints

### GET /api/markets
Returns list of available markets by type.

**Response:**
```json
{
  "electricity": [...],
  "gas": [...],
  "environmental": [...]
}
```

### POST /api/price-data
Fetch market data for a date range.

**Request:**
```json
{
  "type": "electricity",
  "market": "MGP",
  "start_date": "2024-11-01",
  "end_date": "2024-11-02"
}
```

**Response:**
```json
{
  "data": [
    {
      "date": "2024-11-01",
      "interval": 1,
      "price": 125.50,
      "volume": 150.5,
      "zone": "PUN"
    }
  ],
  "count": 24
}
```

### POST /api/forecast
Generate XGBoost price forecast.

**Request:**
```json
{
  "history": [...],
  "days": 2
}
```

### POST /api/export
Export data to Excel.

**Request:**
```json
{
  "rows": [...],
  "filename": "gme_data.xlsx"
}
```

## Troubleshooting

### No Data Returned

**Possible Causes:**
1. **Incorrect Credentials**: Check your GME_USERNAME and GME_PASSWORD
2. **No Data for Date**: Markets may not operate on weekends/holidays
3. **Network Issues**: Check your internet connection
4. **API Rate Limits**: Check quotas with `/api/v1/GetMyQuotas`

**Solutions:**
- Try a different date range (weekdays in the recent past)
- Check application logs for detailed error messages
- Verify credentials on GME website
- Wait if rate limited

### Authentication Failed

**Check:**
```bash
# Test credentials manually
curl -X POST https://api.mercatoelettrico.org/request/api/v1/Auth \
  -H "Content-Type: application/json" \
  -d '{"login":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'
```

### Data Format Issues

The application now handles:
- Integer dates (20241115) → Converts to "2024-11-15"
- Multiple price fields (Price, AveragePrice, ReferencePrice)
- Multiple volume fields (Purchased, Sold, Volumes)
- Period-based data (15-min, 30-min, hourly)

If data still looks incorrect, check the logs:
```bash
# Enable debug logging
export FLASK_ENV=development
python src/app.py
```

## Data Interpretation

### Electricity Markets

**MGP Data:**
- 24 hourly prices (25 on DST change days)
- PUN = National Single Price
- Zonal prices also available

**MI Data:**
- Multiple periods per hour possible
- Shows Period field when available
- Intra-hour trading data

**MSD/MB Data:**
- Purchased and Sold volumes
- Average purchasing/selling prices
- May not have "PUN" zone

### Gas Markets

**MGP-GAS/MI-GAS:**
- Product-based (e.g., GAS-D+1)
- Reference/Average price
- MWh volumes

### Environmental Markets

**TEE/GO/CV:**
- Type-based (different certificate types)
- Reference price
- Traded volumes

## Performance Tips

### For Large Date Ranges

1. **Use smaller chunks**: Query 1-2 weeks at a time
2. **Cache results**: Store in database for reuse
3. **Parallel requests**: Query multiple days in parallel (future enhancement)

### For Real-time Monitoring

1. **Schedule regular updates**: Use cron/scheduler
2. **Incremental updates**: Only fetch new data
3. **Database storage**: Store historical data locally

## Support

### Documentation
- `API_FIXES_DOCUMENTATION.md` - Detailed technical changes
- `README.md` - Project overview
- `plan.txt` - Original requirements

### GME Resources
- API Portal: https://api.mercatoelettrico.org
- Market Data: https://www.mercatoelettrico.org
- Technical Manual: `20251015Manuale_tecnico_API.pdf`

### Testing
- `test_api_fixes.py` - Automated test suite
- `test_gme_api.py` - Original API tests
- `test_markets.py` - Market-specific tests

## Next Steps

1. **Test with your credentials**: Run `test_api_fixes.py`
2. **Explore the web interface**: Try different markets and dates
3. **Generate forecasts**: Use the XGBoost forecasting feature
4. **Export data**: Download Excel files for further analysis
5. **Integrate weather data**: Use the weather API in forecasts (already available)

## Version History

### v2.0.0 (2024-12-14)
- Complete rewrite based on official API manual
- Fixed all market segment names
- Improved response parsing
- Enhanced error handling
- Added comprehensive documentation

### v1.0.0 (Initial)
- Basic GME API integration
- Flask web interface
- XGBoost forecasting
- Excel export

---

For questions or issues, please check the logs or run the test suite for detailed diagnostics.
