
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()
