
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.stock_schemas import StockQuote


def get_market_quote(symbol: str) -> StockQuote:
    symbol = symbol.strip().upper()

    if not symbol:
        raise HTTPException(
            status_code=400,
            detail="Stock symbol is required.",
        )

    try:
        response = httpx.get(
            "https://api.twelvedata.com/quote",
            params={
                "symbol": symbol,
                "apikey": settings.twelve_data_api_key,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Market data provider timed out.",
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(
                status_code=503,
                detail="Market data provider rate limit reached.",
            )
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned an HTTP error.",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Unable to contact market data provider.",
        )
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned invalid JSON.",
        )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="Invalid market data response.",
        )

    if "code" in data and "message" in data:
        code = str(data.get("code"))
        if code == "429":
            raise HTTPException(
                status_code=503,
                detail="Market data provider rate limit reached.",
            )
        if code in ("401", "403"):
            raise HTTPException(
                status_code=502,
                detail="Market data API key or plan does not permit this request.",
            )
        raise HTTPException(
            status_code=502,
            detail="Market data provider could not return this quote.",
        )

    try:
        price = Decimal(str(data["close"]))
        trading_day = date.fromisoformat(data["datetime"])
        timestamp = datetime.fromtimestamp(
            int(data["timestamp"]),
            tz=timezone.utc,
        )

        if not price.is_finite() or price <= 0:
            raise ValueError("Invalid price")

        if timestamp > datetime.now(timezone.utc):
            raise ValueError("Future quote timestamp")

    except (KeyError, TypeError, ValueError, InvalidOperation, OverflowError):
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned an invalid or incomplete quote.",
        )

    return StockQuote(
        symbol=symbol,
        price=float(price),
        latest_trading_day=trading_day,
        quote_timestamp=timestamp,
        currency=data.get("currency", "USD"),
        data_source="Twelve Data",
        data_status="UNVERIFIED",
    )
