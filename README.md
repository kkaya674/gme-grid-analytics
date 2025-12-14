# GME API Client

A Python client for the GME (Gestore dei Mercati Energetici) API.

## Installation

```bash
pip install gme-api
```

## Usage

```python
from gme_api.client import GMEClient
from datetime import date

username = "your_username"
password = "your_password"

with GMEClient(username, password) as client:
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
