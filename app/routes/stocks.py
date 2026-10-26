from app.service.stocks_service import get_stocks
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/stocks")
async def read_stocks():
  return get_stocks()

