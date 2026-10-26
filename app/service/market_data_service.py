
from datetime import date

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.stock_schemas import StockQuote


def get_market_quote(symbol: str) -> StockQuote:
    symbol = symbol.strip().upper()

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": settings.alpha_vantage_api_key,
    }

    try:
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Market data provider timed out.",
        )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve market data.",
        )

    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned invalid JSON.",
        )

    # Alpha Vantage may return API errors or rate-limit messages
    # even when the HTTP response status is 200.
    if "Error Message" in data:
        raise HTTPException(
            status_code=502,
            detail="Market data provider rejected the request.",
        )

    if "Note" in data or "Information" in data:
        raise HTTPException(
            status_code=503,
            detail="Market data is temporarily unavailable due to provider limits.",
        )

    quote_data = data.get("Global Quote", {})

    if not quote_data:
        raise HTTPException(
            status_code=404,
            detail=f"No quote available for symbol {symbol}.",
        )

    try:
        quote_symbol = quote_data["01. symbol"].strip().upper()
        price = float(quote_data["05. price"])
        trading_day = date.fromisoformat(
            quote_data["07. latest trading day"]
        )

        if price <= 0:
            raise ValueError("Price must be positive.")

    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned an invalid quote.",
        )

    return StockQuote(
        symbol=quote_symbol,
        price=price,
        latest_trading_day=trading_day,
        currency="USD",
        data_source="Alpha Vantage",
        data_status="UNVERIFIED",
    )
