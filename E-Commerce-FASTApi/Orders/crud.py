from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
 
from Orders.models import Cart, CartItem, Order, OrderStatus
from Orders.schemas import CartCreate, CartItemCreate, OrderCreate
from Products import crud as Products_crud  # << central change: use crud instead of routes
 
# ---------------------- CART OPERATIONS ----------------------
 
def create_cart(db: Session, cart_in: CartCreate) -> Cart:
    cart = Cart(user_id=cart_in.user_id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart
 
def get_cart(db: Session, cart_id: int) -> Cart:
    cart = db.query(Cart).filter_by(cart_id=cart_id).first()
    if not cart:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Cart {cart_id} not found")
    return cart
 
def get_user_cart(user_id: int) -> List[CartItem]:
    # This is used in `/cart/{user_id}`
    from database import SessionLocal
    db = SessionLocal()
    cart = db.query(Cart).filter_by(user_id=user_id).first()
    if not cart:
        return []
    return cart.items
 
def add_item(db: Session, cart_id: int, item_in: CartItemCreate) -> CartItem:
    # Reserve stock before adding
    Products_crud.reserve_products(
        reservations={"product_id": item_in.id, "quantity": item_in.quantity},
        cart_id=f"cart_{cart_id}",
        db=db
    )
 
    item = db.query(CartItem).filter_by(cart_id=cart_id, product_id=item_in.id).first()
    if item:
        item.quantity += item_in.quantity
    else:
        item = CartItem(cart_id=cart_id, **item_in.dict())
        db.add(item)
 
    db.commit()
    db.refresh(item)
    return item
 
def list_cart_items(db: Session, cart_id: int) -> List[CartItem]:
    cart = get_cart(db, cart_id)
    return cart.items
 
def update_item_quantity(db: Session, cart_id: int, id: int, quantity: int) -> CartItem:
    if quantity < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quantity must be >= 0")
 
    item = db.query(CartItem).filter_by(cart_id=cart_id, product_id=id).first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found in cart")
 
    quantity_diff = quantity - item.quantity
    cart_key = f"cart_{cart_id}"
 
    if quantity_diff > 0:
        Products_crud.reserve_products(
            reservations={"product_id": id, "quantity": quantity_diff},
            cart_id=cart_key,
            db=db
        )
    elif quantity_diff < 0:
        Products_crud.release_products(
            reservations={"product_id": id, "quantity": abs(quantity_diff)},
            cart_id=cart_key,
            db=db
        )
 
    if quantity == 0:
        db.delete(item)
        db.commit()
        return item
 
    item.quantity = quantity
    db.commit()
    db.refresh(item)
    return item
 
def remove_item(db: Session, item_id: int):
    item = db.query(CartItem).filter_by(item_id=item_id).first()
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart item not found")
 
    Products_crud.release_products(
        reservations={"product_id": item.id, "quantity": item.quantity},
        cart_id=f"cart_{item.cart_id}",
        db=db
    )
 
    db.delete(item)
    db.commit()
 
def clear_cart(db: Session, cart_id: int):
    items = db.query(CartItem).filter_by(cart_id=cart_id).all()
    for item in items:
        Products_crud.release_products(
            reservations={"product_id": item.id, "quantity": item.quantity},
            cart_id=f"cart_{cart_id}",
            db=db
        )
        db.delete(item)
    db.commit()
 
# ---------------------- ORDER OPERATIONS ----------------------
 
def create_order(db: Session, order_in: OrderCreate) -> Order:
    total = sum(item.quantity * item.price for item in order_in.items)
    db_order = Order(
        user_id=order_in.user_id,
        items=[item.model_dump() for item in order_in.items],
        total_amount=total,
        payment_method=order_in.payment_method,
        shipping_address=order_in.shipping_address
    )
 
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
 
    try:
        reservations = [
            {"product_id": item.id, "quantity": item.quantity}
            for item in order_in.items
        ]
        Products_crud.finalize_products(
            reservations=reservations,
            order_id=str(db_order.id),
            db=db
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Order created but stock finalization failed: {str(e)}")
 
    return db_order
 
def get_order(db: Session, order_id: int) -> Order:
    order = db.query(Order).get(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Order {order_id} not found")
    return order
 
def list_orders(db: Session) -> List[Order]:
    return db.query(Order).all()
 
def update_order_status(db: Session, order_id: int, status_str: str) -> Order:
    order = get_order(db, order_id)
    try:
        order.status = OrderStatus(status_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid status: {status_str}")
    db.commit()
    db.refresh(order)
    return order
 
def cancel_order(db: Session, order_id: int):
    order = get_order(db, order_id)
    if order.status == OrderStatus.canceled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Order already cancelled")
 
    order.status = OrderStatus.canceled
 
    try:
        reservations = [
            {"product_id": item.get("id"), "quantity": item.get("quantity", 0)}
            for item in order.items
        ]
        Products_crud.release_products(
            reservations=reservations,
            cart_id=f"order_{order_id}",
            db=db
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Order cancelled but releasing stock failed: {str(e)}")
 
    db.commit()