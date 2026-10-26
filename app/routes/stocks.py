from app.service.stocks_service import get_stocks
from fastapi import APIRouter
from app.service.market_data_service import get_market_quote
from app.schemas.stock_schemas import StockQuote

router = APIRouter()

@router.get("/stocks")
async def read_stocks():
  return get_stocks()

@router.get("/stocks/{symbol}/quote", response_model=StockQuote)
async def read_stock_quote(symbol: str):
  return get_market_quote(symbol)

