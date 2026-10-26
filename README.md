# Trading System Backend

A REST API built with **FastAPI** and **Supabase PostgreSQL** that allows users to place simulated stock BUY and SELL orders, retrieve their order history, and view their portfolio holdings using stock market data from Twelve Data.

## Features

- **Market Data Integration:** Retrieves stock quote information from the Twelve Data API.
- **BUY Orders:** Places simulated buy orders and updates portfolio holdings.
- **SELL Orders:** Places simulated sell orders after validating available holdings.
- **Portfolio Management:** Retrieves a user's holdings and average purchase prices.
- **Order History:** Lists orders belonging to a specific user.
- **Database Persistence:** Stores users, orders, and portfolio holdings in PostgreSQL.
- **Input Validation:** Validates order details, including stock symbols, order side, and quantity.
- **Error Handling:** Handles invalid users, unsupported stocks, insufficient holdings, and market-data provider errors.
- **API Documentation:** Provides interactive API documentation through Swagger UI.

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Pydantic | Request validation and settings |
| PostgreSQL | Relational database |
| Supabase | Managed PostgreSQL database |
| Psycopg 3 | PostgreSQL connectivity |
| HTTPX | External API requests |
| Twelve Data | Stock market data provider |
| Render | Backend deployment |

## Architecture

The application follows a modular structure that separates API routes, request schemas, business logic, configuration, and database connectivity.

```text
Trading System - Backend/
├── app/
│   ├── core/
│   │   └── config.py
│   ├── routes/
│   │   ├── order.py
│   │   ├── order_history.py
│   │   └── portfolio.py
│   ├── schemas/
│   │   ├── order_schemas.py
│   │   └── stock_schemas.py
│   ├── service/
│   │   ├── market_data_service.py
│   │   ├── order_service.py
│   │   ├── order_history_service.py
│   │   └── portfolio_service.py
│   ├── database.py
│   └── main.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

*Note: The structure above reflects the current backend modules; adjust filenames if your repository differs.*

## API Endpoints

The following endpoints provide the core functionality. Confirm the exact paths and HTTP methods in your application's Swagger documentation.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/stocks` | Lists supported stocks, if enabled in the application |
| `GET` | `/stocks/{symbol}/quote` | Retrieves a stock quote |
| `POST` | `/orders` | Places a simulated BUY or SELL order |
| `GET` | `/orders/{user_id}` | Retrieves a user's order history |
| `GET` | `/portfolio/{user_id}` | Retrieves a user's portfolio holdings |

### Place an Order

**Endpoint:** `POST /orders`

Example BUY request:

```json
{
  "user_id": 1,
  "symbol": "AMD",
  "side": "BUY",
  "quantity": 4
}
```

Example SELL request:

```json
{
  "user_id": 1,
  "symbol": "AMD",
  "side": "SELL",
  "quantity": 1
}
```

The API retrieves a stock quote, validates the request and available holdings, records the order, and updates the portfolio within a database transaction.

Successful order responses include details such as the order ID, symbol, side, quantity, execution price, status, data source, and execution mode.

### View Portfolio

**Endpoint:** `GET /portfolio/{user_id}`

Returns the user's current holdings, including stock symbols, quantities, average purchase prices, and update timestamps.

### View Order History

**Endpoint:** `GET /orders/{user_id}`

Returns the user's recorded orders, ordered from newest to oldest.

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the installed dependencies.
- A Supabase PostgreSQL database.
- A Twelve Data API key.

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd "Trading System - Backend"
```

Replace `<YOUR_REPOSITORY_URL>` with your actual Git repository URL.

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

If you use Command Prompt instead:

```bat
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=your_supabase_postgresql_connection_string
TWELVE_DATA_API_KEY=your_twelve_data_api_key
```

Replace the placeholder values with your own credentials.

**Security:** Never commit `.env`, database passwords, or API keys to Git. Keep them in environment variables on Render as well.

### 5. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will normally be available at:

- Base URL: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Order Processing Logic

### BUY Flow

1. Retrieve the stock quote.
2. Validate the quote and request.
3. Verify the user and supported stock.
4. Record the simulated BUY
