from fastapi import APIRouter

from app.schemas.order_schemas import OrderCreate
from app.service.order_service import place_order

router = APIRouter()


@router.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    return place_order(order)