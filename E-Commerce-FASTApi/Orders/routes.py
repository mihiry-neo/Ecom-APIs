from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import Orders.crud, Orders.schemas
from utils import get_current_user

# ------------------- CART ROUTER -------------------
cart_router = APIRouter(prefix="/cart", tags=["Carts"])

@cart_router.get("/{user_id}")
def read_cart(user_id: int, current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return Orders.crud.get_user_cart(user_id)

@cart_router.post("/", response_model=Orders.schemas.CartResponse, status_code=status.HTTP_201_CREATED)
def create_cart(cart_in: Orders.schemas.CartCreate, db: Session = Depends(get_db)):
    return Orders.crud.create_cart(db, cart_in)

@cart_router.get("/{cart_id}/details", response_model=Orders.schemas.CartResponse)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    return Orders.crud.get_cart(db, cart_id)

@cart_router.post("/{cart_id}/items", response_model=Orders.schemas.CartItemResponse)
def add_item_to_cart(cart_id: int, item_in: Orders.schemas.CartItemCreate, db: Session = Depends(get_db)):
    return Orders.crud.add_item(db, cart_id, item_in)

@cart_router.get("/{cart_id}/items", response_model=list[Orders.schemas.CartItemResponse])
def list_items(cart_id: int, db: Session = Depends(get_db)):
    return Orders.crud.list_cart_items(db, cart_id)

@cart_router.put("/{cart_id}/items/{product_id}", response_model=Orders.schemas.CartItemResponse)
def update_item(cart_id: int, product_id: int, quantity: int, db: Session = Depends(get_db)):
    return Orders.crud.update_item_quantity(db, cart_id, product_id, quantity)

@cart_router.delete("/{cart_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    Orders.crud.remove_item(db, item_id)
    return {"message": "Item removed and stock released."}

@cart_router.delete("/{cart_id}/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(cart_id: int, db: Session = Depends(get_db)):
    Orders.crud.clear_cart(db, cart_id)
    return {"message": "Cart cleared and stock released."}


# ------------------- ORDER ROUTER -------------------
order_router = APIRouter(prefix="/orders", tags=["Orders"])

@order_router.post("/", response_model=Orders.schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_in: Orders.schemas.OrderCreate, db: Session = Depends(get_db)):
    return Orders.crud.create_order(db, order_in)

@order_router.get("/{order_id}", response_model=Orders.schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return Orders.crud.get_order(db, order_id)

@order_router.get("/", response_model=list[Orders.schemas.OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return Orders.crud.list_orders(db)

@order_router.patch("/{order_id}/status", response_model=Orders.schemas.OrderResponse)
def update_order_status(order_id: int, status_in: Orders.schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    return Orders.crud.update_order_status(db, order_id, status_in.status)

@order_router.delete("/{order_id}", response_model=Orders.schemas.OrderCancelResponse)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    Orders.crud.cancel_order(db, order_id)
    return {"detail": f"Order {order_id} canceled and reserved inventory released."}
