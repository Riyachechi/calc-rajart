from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func

from .database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer_name = Column(String, default="")
    customer_phone = Column(String, default="")
    notes = Column(String, default="")

    gsm = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    printing_side = Column(String, nullable=False)
    lamination = Column(String, nullable=False)

    rate_quantity_used = Column(Integer, nullable=False)
    used_nearest_quantity = Column(Boolean, default=False)

    printing_min = Column(Float, nullable=False)
    printing_max = Column(Float, nullable=False)
    lamination_price = Column(Float, nullable=False)

    final_min_per_piece = Column(Float, nullable=False)
    final_max_per_piece = Column(Float, nullable=False)

    total_min = Column(Float, nullable=False)
    total_max = Column(Float, nullable=False)
