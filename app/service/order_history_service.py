
from fastapi import HTTPException

from app.database import get_connection


def get_user_orders(user_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM users WHERE id = %s",
                (user_id,),
            )

            if cur.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found.",
                )

            cur.execute(
                """
                SELECT
                    id,
                    user_id,
                    symbol,
                    side,
                    quantity,
                    price,
                    status,
                    created_at
                FROM orders
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )

            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "symbol": row[2],
            "side": row[3],
            "quantity": str(row[4]),
            "price": str(row[5]),
            "status": row[6],
            "created_at": row[7].isoformat(),
        }
        for row in rows
    ]
