
from fastapi import APIRouter, Path

from app.service.order_history_service import get_user_orders

router = APIRouter()


@router.get("/orders/{user_id}")
def read_user_orders(
    user_id: int = Path(gt=0),
):
    return get_user_orders(user_id)
