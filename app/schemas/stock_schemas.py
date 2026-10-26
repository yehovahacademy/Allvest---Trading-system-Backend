from pydantic import BaseModel
from datetime import datetime

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
  price: float
  timestamp: datetime  
  currency: str
  data_source: str
  data_status: str
  
