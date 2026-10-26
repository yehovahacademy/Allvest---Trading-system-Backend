
from fastapi import FastAPI, HTTPException

from app.database import get_connection

app = FastAPI(
    title="Trading System API",
    description="A simulated stock trading and portfolio management API.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Trading System API is running",
    }


@app.get("/db-check")
def database_check():
    try:
        with get_connection() as conn:
            result = conn.execute(
                "SELECT current_database()"
            ).fetchone()

        return {
            "status": "connected",
            "database": result[0],
        }

    except Exception as exc:
        print(f"Database connection error: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check server logs.",
        )
