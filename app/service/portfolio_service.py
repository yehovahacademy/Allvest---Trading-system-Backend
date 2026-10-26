
from fastapi import HTTPException

from app.database import get_connection


def get_user_portfolio(user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Confirm the user exists.
            cur.execute(
                "SELECT id FROM users WHERE id = %s",
                (user_id,),
            )

            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found.",
                )

            # 2. Retrieve the user's holdings.
            cur.execute(
                """
                SELECT
                    symbol,
                    quantity,
                    average_buy_price,
                    updated_at
                FROM portfolio_holdings
                WHERE user_id = %s
                  AND quantity > 0
                ORDER BY symbol ASC
                """,
                (user_id,),
            )

            rows = cur.fetchall()

    # 3. Format database values for the API response.
    holdings = [
        {
            "symbol": row[0],
            "quantity": str(row[1]),
            "average_buy_price": str(row[2]),
            "updated_at": row[3].isoformat(),
        }
        for row in rows
    ]

    return {
        "user_id": user_id,
        "holdings_count": len(holdings),
        "holdings": holdings,
    }
