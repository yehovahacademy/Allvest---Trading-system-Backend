
from app.database import get_connection


def get_all_stocks():
    query = """
        SELECT
            symbol,
            company_name,
            exchange,
            sector,
            currency,
            reference_price,
            price_timestamp,
            data_source,
            data_status
        FROM stock_reference_data
        ORDER BY symbol;
    """

    with get_connection() as conn:
        rows = conn.execute(query).fetchall()

    stocks = []

    for row in rows:
        stocks.append(
            {
                "symbol": row[0],
                "company_name": row[1],
                "exchange": row[2],
                "sector": row[3],
                "currency": row[4],
                "reference_price": (
                    float(row[5]) if row[5] is not None else None
                ),
                "price_timestamp": (
                    row[6].isoformat() if row[6] else None
                ),
                "data_source": row[7],
                "data_status": row[8],
            }
        )

    return stocks
