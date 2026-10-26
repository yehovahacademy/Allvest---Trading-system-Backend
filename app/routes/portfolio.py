
from fastapi import APIRouter, Path

from app.service.portfolio_service import get_user_portfolio

router = APIRouter()


@router.get("/portfolio/{user_id}")
def read_user_portfolio(
    user_id: int = Path(gt=0),
):
    return get_user_portfolio(user_id)
