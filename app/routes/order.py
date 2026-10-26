
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.schemas.order_schemas import OrderCreate
from app.service.order_service import place_order

router = APIRouter()


@router.post("/orders", status_code=201)
def create_order(
    order: OrderCreate,
    current_user: dict = Depends(get_current_user),
):
    return place_order(order, user_id=current_user["id"])
