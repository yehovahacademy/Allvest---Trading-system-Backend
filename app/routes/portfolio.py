
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.service.portfolio_service import get_user_portfolio

router = APIRouter()


@router.get("/portfolio")
def read_user_portfolio(
    current_user: dict = Depends(get_current_user),
):
    return get_user_portfolio(current_user["id"])
