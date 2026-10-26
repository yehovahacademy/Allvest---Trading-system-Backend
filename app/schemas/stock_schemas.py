from pydantic import BaseModel, Field
from datetime import date, datetime

class Stock(BaseModel):
  symbol: str
  company_name: str
  exchange: str
  sector: str
  currency: str
  reference_price: float | None = None
  price_timestamp: datetime | None = None
  data_source: str
  data_status: str


class StockQuote(BaseModel):
    symbol: str
    price: float = Field(gt=0)
    latest_trading_day: date
    quote_timestamp: datetime
    currency: str
    data_source: str
    data_status: str
