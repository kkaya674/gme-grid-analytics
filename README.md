# GME Market Analytics Platform

A comprehensive Flask-based web application for analyzing Italian energy market (GME) data with advanced XGBoost forecasting capabilities.

## Features

- **Interactive Market Data Visualization**: Real-time price charts with Chart.js
- **Multi-Market Support**: Electricity (MGP, MI, MPEG), Gas (MGP-GAS, MI-GAS, MGS), and Environmental markets (TEE, GO)
- **XGBoost Forecasting**: Advanced machine learning predictions for 1-3 days ahead with weather integration
- **Weather Data Integration**: Open-Meteo API integration for enhanced forecasting accuracy
- **Excel Export**: Download market data and forecasts in Excel format
- **Modern UI**: Responsive glass-morphism design with dark theme
- **Docker Support**: Full containerization for easy deployment

## Quick Start

### Using Docker (Recommended)

1. Create `.env` file from example:
```bash
cp .env.example .env
```

2. Edit `.env` with your GME credentials:
```
GME_USERNAME=your_username
GME_PASSWORD=your_password
```

3. Start the application:
```bash
docker-compose up --build
```

4. Access the application at `http://localhost:5005`

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export GME_USERNAME=your_username
export GME_PASSWORD=your_password
```

3. Run the application:
```bash
python src/app.py
```

## API Endpoints

### GET `/api/markets`
Returns available markets categorized by type.

### POST `/api/price-data`
Fetch historical price data.
```json
{
  "type": "electricity",
  "market": "MGP",
  "start_date": "2024-01-01",
  "end_date": "2024-01-07"
}
```

### POST `/api/forecast`
Generate XGBoost forecast.
```json
{
  "history": [...],
  "days": 2
}
```

### POST `/api/export`
Export data to Excel format.

## Technology Stack

- **Backend**: Flask, Python 3.11
- **ML/Forecasting**: XGBoost, scikit-learn, pandas, numpy
- **Weather API**: Open-Meteo
- **Frontend**: Vanilla JavaScript, Chart.js
- **Styling**: Custom CSS with glass-morphism
- **Containerization**: Docker, Docker Compose

## Project Structure

```
gme_api/
├── src/
│   ├── app.py                 # Application entry point
│   ├── gme_api/
│   │   └── client.py          # GME API client
│   ├── services/
│   │   ├── forecasting.py     # XGBoost forecasting engine
│   │   └── weather.py         # Weather data integration
│   └── web/
│       ├── routes.py          # API routes
│       ├── templates/
│       │   └── index.html     # Main UI
│       └── static/
│           ├── script.js      # Frontend logic
│           └── style.css      # Styling
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Environment Variables

- `GME_USERNAME`: GME API username
- `GME_PASSWORD`: GME API password
- `FLASK_ENV`: Environment (production/development)
- `PORT`: Application port (default: 5000)
- `SECRET_KEY`: Flask secret key (auto-generated if not set)

## License

MIT

## Author

Built for GME Italian Energy Market Analysis
    today = date.today()
    prices = client.get_electricity_prices("MGP", today)
    print(prices)
```

## Features

- Authentication handling (JWT)
- Automatic decoding of API responses (Base64 + ZIP + JSON)
- Helper methods for Electricity and Gas markets

## License

MIT
