import enum
from sqlalchemy import JSON, Column, Enum, Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class OrderStatus(enum.Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    canceled = "canceled"

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_date = Column(DateTime, default=utc_now, nullable=False)
    items = Column(JSON, nullable=False)  
    total_amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)
    payment_method = Column(String(50), nullable=True)
    shipping_address = Column(String(255), nullable=False)

class CartItem(Base):
    __tablename__ = "cart_items"
    item_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    cart = relationship("Cart", back_populates="items")

class Cart(Base):
    __tablename__ = "carts"

    cart_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")