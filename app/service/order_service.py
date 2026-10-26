
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg
from fastapi import HTTPException

from app.database import get_connection
from app.schemas.order_schemas import OrderCreate
from app.service.market_data_service import get_market_quote

logger = logging.getLogger(__name__)


def place_order(order: OrderCreate):
    symbol = order.symbol.strip().upper()
    quantity = order.quantity

    # 1. Retrieve a market quote.
    quote = get_market_quote(symbol)

    # 2. Validate the quote timestamp.
    now = datetime.now(timezone.utc)
    quote_timestamp = quote.quote_timestamp

    if quote_timestamp.tzinfo is None:
        raise HTTPException(
            status_code=502,
            detail="Market quote timestamp has no timezone.",
        )

    if quote_timestamp > now:
        raise HTTPException(
            status_code=503,
            detail="Order rejected: quote timestamp is in the future.",
        )

    # Demo policy: reject quotes older than seven days.
    if now - quote_timestamp > timedelta(days=7):
        raise HTTPException(
            status_code=503,
            detail="Order rejected: the available quote is too old.",
        )

    price = Decimal(str(quote.price))

    if not price.is_finite() or price <= 0:
        raise HTTPException(
            status_code=502,
            detail="Order rejected: invalid market price.",
        )

    try:
        # 3. Perform order and portfolio changes in one transaction.
        with get_connection() as conn:
            with conn.cursor() as cur:

                # Validate user.
                cur.execute(
                    "SELECT id FROM users WHERE id = %s",
                    (order.user_id,),
                )
                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="User not found.",
                    )

                # Validate stock catalogue entry.
                cur.execute(
                    """
                    SELECT symbol
                    FROM stock_reference_data
                    WHERE symbol = %s
                    """,
                    (symbol,),
                )
                if cur.fetchone() is None:
                    raise HTTPException(
                        status_code=404,
                        detail="Stock not found.",
                    )

                # Retrieve and lock an existing holding.
                cur.execute(
                    """
                    SELECT quantity, average_buy_price
                    FROM portfolio_holdings
                    WHERE user_id = %s AND symbol = %s
                    FOR UPDATE
                    """,
                    (order.user_id, symbol),
                )
                holding = cur.fetchone()

                # Prevent selling shares the user does not own.
                if order.side == "SELL":
                    available_quantity = (
                        Decimal(str(holding[0]))
                        if holding is not None
                        else Decimal("0")
                    )

                    if available_quantity < quantity:
                        raise HTTPException(
                            status_code=400,
                            detail="Insufficient shares to sell.",
                        )

                # Insert simulated order.
                cur.execute(
                    """
                    INSERT INTO orders
                        (user_id, symbol, side, quantity, price, status)
                    VALUES (%s, %s, %s, %s, %s, 'FILLED')
                    RETURNING
                        id, user_id, symbol, side, quantity, price,
                        status, created_at
                    """,
                    (
                        order.user_id,
                        symbol,
                        order.side,
                        quantity,
                        price,
                    ),
                )
                saved_order = cur.fetchone()

                if order.side == "BUY":
                    old_quantity = (
                        Decimal(str(holding[0]))
                        if holding is not None
                        else Decimal("0")
                    )
                    old_average = (
                        Decimal(str(holding[1]))
                        if holding is not None
                        else Decimal("0")
                    )

                    new_quantity = old_quantity + quantity

                    # Calculate weighted average purchase price.
                    new_average = (
                        old_quantity * old_average + quantity * price
                    ) / new_quantity

                    cur.execute(
                        """
                        INSERT INTO portfolio_holdings
                            (user_id, symbol, quantity, average_buy_price)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, symbol)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            average_buy_price = EXCLUDED.average_buy_price,
                            updated_at = NOW()
                        """,
                        (
                            order.user_id,
                            symbol,
                            new_quantity,
                            new_average,
                        ),
                    )

                else:
                    old_quantity = Decimal(str(holding[0]))
                    old_average = Decimal(str(holding[1]))
                    remaining = old_quantity - quantity

                    cur.execute(
                        """
                        UPDATE portfolio_holdings
                        SET quantity = %s,
                            average_buy_price = %s,
                            updated_at = NOW()
                        WHERE user_id = %s AND symbol = %s
                        """,
                        (
                            remaining,
                            old_average if remaining > 0 else Decimal("0"),
                            order.user_id,
                            symbol,
                        ),
                    )

            # Commit order and portfolio changes together.
            conn.commit()

    except HTTPException:
        # Preserve expected errors such as 404 and 400.
        raise

    except psycopg.Error as exc:
        # Log the technical traceback on the server, not to the client.
        logger.exception("Database error while placing order")
        raise HTTPException(
            status_code=500,
            detail="Database error while placing order.",
        ) from exc

    except Exception as exc:
        # Capture unexpected application errors for diagnosis.
        logger.exception("Unexpected error while placing order")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error while placing order. Check server logs.",
        ) from exc

    # 4. Return the saved order.
    return {
        "id": saved_order[0],
        "user_id": saved_order[1],
        "symbol": saved_order[2],
        "side": saved_order[3],
        "quantity": str(saved_order[4]),
        "price": str(saved_order[5]),
        "status": saved_order[6],
        "created_at": saved_order[7].isoformat(),
        "execution_mode": "SIMULATED",
        "data_source": quote.data_source,
        "quote_data_status": quote.data_status,
        "quote_timestamp": quote_timestamp.isoformat(),
    }
