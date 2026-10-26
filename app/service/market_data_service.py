
import logging
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.stock_schemas import StockQuote

logger = logging.getLogger(__name__)


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

    except httpx.TimeoutException as exc:
        logger.warning("Market data provider timed out.")
        raise HTTPException(
            status_code=504,
            detail="Market data provider timed out.",
        ) from exc

    except httpx.HTTPStatusError as exc:
        # Log the status only; never log the request URL or API key.
        status_code = exc.response.status_code
        logger.error(
            "Twelve Data returned HTTP status %s.",
            status_code,
        )

        if status_code == 429:
            raise HTTPException(
                status_code=503,
                detail="Market data provider rate limit reached.",
            ) from exc

        if status_code in (401, 403):
            raise HTTPException(
                status_code=502,
                detail="Market data API key or plan does not permit this request.",
            ) from exc

        raise HTTPException(
            status_code=502,
            detail=f"Market data provider returned HTTP status {status_code}.",
        ) from exc

    except httpx.HTTPError as exc:
        logger.error(
            "Unable to contact Twelve Data: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to contact market data provider.",
        ) from exc

    except ValueError as exc:
        logger.error("Twelve Data returned invalid JSON.")
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned invalid JSON.",
        ) from exc

    # Twelve Data may return an API error in a successful HTTP response.
    if not isinstance(data, dict):
        logger.error("Twelve Data returned a non-object response.")
        raise HTTPException(
            status_code=502,
            detail="Invalid market data response.",
        )

    if "code" in data and "message" in data:
        code = str(data.get("code"))
        logger.warning(
            "Twelve Data API error: code=%s",
            code,
        )

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

    # Parse the quote and its timestamp.
    try:
        price = Decimal(str(data["close"]))
        trading_day = date.fromisoformat(str(data["datetime"]))

        timestamp_value = data["timestamp"]
        timestamp = datetime.fromtimestamp(
            int(timestamp_value),
            tz=timezone.utc,
        )

        if not price.is_finite() or price <= 0:
            raise ValueError("Invalid price")

        if timestamp > datetime.now(timezone.utc):
            raise ValueError("Future quote timestamp")

    except (
        KeyError,
        TypeError,
        ValueError,
        InvalidOperation,
        OverflowError,
        OSError,
    ) as exc:
        logger.warning(
            "Twelve Data quote was invalid or incomplete: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="Market data provider returned an invalid or incomplete quote.",
        ) from exc

    return StockQuote(
        symbol=symbol,
        price=float(price),
        latest_trading_day=trading_day,
        quote_timestamp=timestamp,
        currency=data.get("currency") or "USD",
        data_source="Twelve Data",
        data_status="UNVERIFIED",
    )
