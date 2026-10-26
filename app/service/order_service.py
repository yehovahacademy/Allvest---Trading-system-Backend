
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.database import get_connection
from app.schemas.order_schemas import OrderCreate
from app.service.market_data_service import get_market_quote


def place_order(order: OrderCreate):
    symbol = order.symbol.strip().upper()
    quantity = order.quantity

    # 1. Retrieve a quote from Twelve Data.
    # Preserve the provider's meaningful HTTP error.
    quote = get_market_quote(symbol)

    # 2. Validate quote timestamp.
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
    # This does not guarantee that a quote is live or current.
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

    # 3. Validate the user, stock, and holdings and update
    # the order and portfolio in one database transaction.
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

            # Validate stock exists in our reference catalogue.
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

            # Lock an existing holding before checking a SELL.
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

            # Insert the simulated order.
            cur.execute(
                """
                INSERT INTO orders
                    (user_id, symbol, side, quantity, price, status)
                VALUES (%s, %s, %s, %s, %s, 'FILLED')
                RETURNING id, user_id, symbol, side, quantity, price,
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

        # Commit both order and holding changes together.
        conn.commit()

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
