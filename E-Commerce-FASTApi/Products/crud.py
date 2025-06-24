from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import joinedload
from typing import Tuple, Dict, Any, Optional, List, Union
from database import get_db
import Products.models, Products.schemas
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_product_manual(db: Session, product: Products.schemas.ProductCreate):
    try:
        db_product = Products.models.Product(**product.model_dump())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        raise

def get_all_products(db: Session):
    products = db.query(Products.models.Product).all()
    return products

def get_product_by_id(db: Session, id: int):
    product = db.query(Products.models.Product).filter(Products.models.Product.id == id).first()
    return product

def get_product_by_name(db: Session, name: str):
    return db.query(Products.models.Product).filter(Products.models.Product.name == name).first()

def get_product_by_brand(db: Session, brand: str):
    return db.query(Products.models.Product).filter(Products.models.Product.brand == brand).first()

def get_products_by_category(db: Session, category_id: int):
    products = db.query(Products.models.Product).filter(Products.models.Product.category_id == category_id).all()
    return products

def get_all_categories(db: Session):
    categories = db.query(Products.models.Category).all()
    return categories

def get_paginated_products(
    db: Session, 
    skip: int, 
    limit: int, 
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    filters: Optional[Dict[str, Any]] = None
) -> Tuple[int, List[Products.models.Product]]:
    try:
        query = db.query(Products.models.Product).options(joinedload(Products.models.Product.category))
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Products.models.Product.name.like(search_term),
                    Products.models.Product.brand.like(search_term)
                )
            )
        
        if filters:
            if filters.get('min_price'):
                query = query.filter(Products.models.Product.price >= filters['min_price'])
            if filters.get('max_price'):
                query = query.filter(Products.models.Product.price <= filters['max_price'])
            if filters.get('category_id'):
                query = query.filter(Products.models.Product.category_id == filters['category_id'])
            if filters.get('in_stock_only'):
                query = query.filter(Products.models.Product.stock_quantity > 0)

        total = query.count()

        if hasattr(Products.models.Product, sort_by):
            sort_column = getattr(Products.models.Product, sort_by)
            if sort_dir == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

        products = query.offset(skip).limit(limit).all()
        return total, products
    
    except Exception as e:
        raise

def update_product(db: Session, product_id: int, product_update: Products.schemas.ProductUpdate):
    """Update a product with only the provided fields"""
    
    db_product = db.query(Products.models.Product).filter(Products.models.Product.id == product_id).first()
    
    if not db_product:
        db_product = db.query(Products.models.Product).filter(Products.models.Product.name == str(product_id)).first()
    
    if not db_product:
        db_product = db.query(Products.models.Product).filter(Products.models.Product.brand == str(product_id)).first()
    
    if not db_product:
        return None
    
    update_data = product_update.model_dump(exclude_unset=True)
    
    if 'attributes' in update_data:
        new_attributes = update_data.pop('attributes')
        
        if new_attributes is not None:
            existing_attributes = db_product.attributes or {}
            
            if isinstance(new_attributes, dict) and new_attributes:
                merged_attributes = dict(existing_attributes)
                merged_attributes.update(new_attributes)
                db_product.attributes = merged_attributes
            elif new_attributes == {}:
                db_product.attributes = {}
                
    for field, value in update_data.items():
        if hasattr(db_product, field):
            setattr(db_product, field, value)
    
    try:
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        raise e
    
def get_inventory_by_product_id(db: Session, product_id: int):
    return db.query(Products.models.Inventory).filter(Products.models.Inventory.product_id == product_id).first()

def update_inventory_quantity(db: Session, product_id: int, quantity_delta: int, reason: str = None, order_id: int = None):
    inventory = get_inventory_by_product_id(db, product_id)
    if not inventory:
        raise Exception("Inventory record not found for product_id")

    inventory.quantity_available += quantity_delta
    inventory.quantity_available = max(0, inventory.quantity_available)

    movement = Products.models.StockMovement(
        product_id=product_id,
        order_id=order_id,
        change=quantity_delta,
        reason=reason
        )
    db.add(movement)
    db.commit()
    db.refresh(inventory)
    return inventory

def create_or_update_inventory(db: Session, product_id: int, data: Products.schemas.InventoryBase):
    inventory = get_inventory_by_product_id(db, product_id)
    if not inventory:
        inventory = Products.models.Inventory(product_id=product_id, **data.model_dump())
        db.add(inventory)
    else:
        for key, value in data.model_dump().items():
            setattr(inventory, key, value)
    db.commit()
    db.refresh(inventory)
    return inventory

def get_stock_movements_for_product(db: Session, product_id: int):
    return db.query(Products.models.StockMovement).filter(Products.models.StockMovement.product_id == product_id).order_by(Products.models.StockMovement.timestamp.desc()).all()


def update_inventory_settings(
    db: Session,
    product_id: int,
    update_data: Products.schemas.InventoryUpdate
):
    inventory = db.query(Products.models.Inventory).filter(Products.models.Inventory.product_id == product_id).first()
    if not inventory:
        raise Exception("Inventory not found")

    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(inventory, key, value)

    db.commit()
    db.refresh(inventory)
    return inventory

def reserve_stock(db: Session, product_id: int, quantity: int) -> bool:
    """Reserve stock with proper transaction management"""
    try:
        inventory = get_inventory_by_product_id(db, product_id)
        if not inventory or inventory.quantity_available < quantity:
            return False
            
        inventory.quantity_available -= quantity
        inventory.quantity_reserve += quantity
        
        movement = Products.models.StockMovement(
            product_id=product_id,
            change=-quantity,
            reason="reserved"
        )
        db.add(movement)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    
def generate_recommendations(user_id: int, limit: int, db: Session) -> List[dict]:
    products = db.query(Products.models.Product)\
        .join(Products.models.Inventory)\
        .filter(Products.models.Inventory.quantity_available > 0)\
        .order_by(func.random())\
        .limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "brand": p.brand,
            "category_name": p.category.name if p.category else "Unknown",
            "rating": p.attributes.get("rating") if p.attributes else None,
            "stock_quantity": p.inventory.quantity_available if p.inventory else 0
        } for p in products
    ]


def reserve_products(
    reservations: Union[List[dict], dict],
    cart_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Reserve single or multiple products for an order (atomic operation)"""
    if isinstance(reservations, dict):
        reservations = [reservations]
    
    try:
        reserved_items = []
        
        for item in reservations:
            inventory = Products.crud.get_inventory_by_product_id(db, item["product_id"])
            if not inventory or inventory.quantity_available < item["quantity"]:
                db.rollback()
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock for product {item['product_id']} (requested: {item['quantity']}, available: {inventory.quantity_available if inventory else 0})"
                )
        
        for item in reservations:
            inventory = Products.crud.get_inventory_by_product_id(db, item["product_id"])
            inventory.quantity_available -= item["quantity"]
            inventory.quantity_reserve += item["quantity"]
            
            movement = Products.models.StockMovement(
                product_id=item["product_id"],
                cart_id=item["cart_id"],
                change=-item["quantity"],
                reason=f"reserve_order_{cart_id}" if cart_id else "reserve"
            )
            db.add(movement)
            reserved_items.append({
                **item,
                "remaining_available": inventory.quantity_available
            })
        
        db.commit()
        
        return {
            "success": True,
            "reserved_items": reserved_items,
            "total_items": len(reserved_items),
            "cart_id": cart_id,
            "message": f"Successfully reserved {len(reserved_items)} product(s)"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    

def release_products(
    reservations: Union[List[dict], dict],
    cart_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Release single or multiple reserved products (e.g., if user cancels checkout)"""
    if isinstance(reservations, dict):
        reservations = [reservations]
    
    try:
        released_items = []
        
        for item in reservations:
            inventory = Products.crud.get_inventory_by_product_id(db, item["product_id"])
            if inventory and inventory.quantity_reserve >= item["quantity"]:
                inventory.quantity_reserve -= item["quantity"]
                inventory.quantity_available += item["quantity"]
                
                movement = Products.models.StockMovement(
                    product_id=item["product_id"],
                    cart_id=item["cart_id"],
                    change=item["quantity"],
                    reason=f"release_order_{cart_id}" if cart_id else "release"
                )
                db.add(movement)
                released_items.append({
                    **item,
                    "new_available": inventory.quantity_available
                })
        
        db.commit()
        return {
            "success": True,
            "released_items": released_items,
            "total_items": len(released_items),
            "order_id": cart_id,
            "message": f"Successfully released {len(released_items)} product(s)"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
def finalize_products(
    reservations: Union[List[dict], dict],
    order_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Finalize single or multiple reserved products (convert reserves to sold)"""
    if isinstance(reservations, dict):
        reservations = [reservations]
    
    try:
        finalized_items = []
        
        for item in reservations:
            inventory = Products.crud.get_inventory_by_product_id(db, item["product_id"])
            if inventory and inventory.quantity_reserve >= item["quantity"]:
                inventory.quantity_reserve -= item["quantity"]
                
                movement = Products.models.StockMovement(
                    product_id=item["product_id"],
                    order_id=item["order_id"],
                    change=-item["quantity"],
                    reason=f"finalize_order_{order_id}" if order_id else "finalize"
                )
                db.add(movement)
                finalized_items.append({
                    **item,
                    "remaining_reserved": inventory.quantity_reserve
                })
        
        db.commit()
        return {
            "success": True,
            "finalized_items": finalized_items,
            "total_items": len(finalized_items),
            "order_id": order_id,
            "message": f"Successfully finalized {len(finalized_items)} product(s)"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))