
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.service.order_history_service import get_user_orders

router = APIRouter()


@router.get("/orders")
def read_user_orders(
    current_user: dict = Depends(get_current_user),
):
    return get_user_orders(current_user["id"])
