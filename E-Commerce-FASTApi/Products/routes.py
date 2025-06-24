from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from typing import List, Optional, Union
import Products.schemas, Products.crud
from database import get_db
from datagen import DataGenerator
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

router = APIRouter(prefix="/products", tags=["Products"])
generator = DataGenerator()

@router.post("/", response_model=Products.schemas.Product)
def create_product(product: Products.schemas.ProductCreate, db: Session = Depends(get_db)):
    return Products.crud.create_product_manual(db, product)

@router.get("/", response_model=Products.schemas.ProductListResponse)
def get_all_products(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search products"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_dir: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    in_stock_only: bool = Query(False, description="Show only in-stock items")
):
    
    skip = (page - 1) * per_page
    filters = {
        'min_price': min_price,
        'max_price': max_price,
        'category_id': category_id,
        'in_stock_only': in_stock_only
    }
    
    total, products = Products.crud.get_paginated_products(
        db, skip, per_page, search, sort_by, sort_dir, filters
    )
    
    clean_products = []
    for product in products:
        rating = None
        if product.attributes and 'rating' in product.attributes:
            rating = product.attributes['rating']
        
        clean_products.append({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "brand": product.brand,
            "stock_quantity": product.inventory.quantity_available if product.inventory else 0,
            "category_name": product.category.name if product.category else "Unknown",
            "rating": rating
        })
    
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "products": clean_products
    }

@router.get("/{product_id}", response_model=Products.schemas.Product)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = Products.crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/auto-generate", response_model=List[Products.schemas.Product])
def auto_generate_products(count: int = 1, db: Session = Depends(get_db)):
    categories = Products.crud.get_all_categories(db)
    return generator.create_products(db, categories, count)

from fastapi import Query

@router.post("/update-prices")
def update_all_prices(
    count: int = Query(50, ge=1, le=500, description="Number of products to update"),
    db: Session = Depends(get_db)
):
    products = Products.crud.get_all_products(db)
    if not products:
        return {"message": "No products found to update"}
    generator.randomly_update_prices(db, products, batch_size=count)
    return {"message": f"Price updated for {min(count, len(products))} products"}


@router.patch("/{product_id}", response_model=Products.schemas.Product)
def update_product(
    product_id: str, 
    product_update: Products.schemas.ProductUpdate,
    db: Session = Depends(get_db)
):

    product = None
    if product_id.isdigit():
        product = Products.crud.get_product_by_id(db, int(product_id))
    if not product:
        product = Products.crud.get_product_by_name(db, product_id)
    if not product:
        product = Products.crud.get_product_by_brand(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product_update.category_id is not None:
        valid_category_ids = [cat.id for cat in Products.crud.get_all_categories(db)]
        if product_update.category_id not in valid_category_ids:
            raise HTTPException(status_code=400, detail="Invalid category_id")

    updated_product = Products.crud.update_product(db, product.id, product_update)

    return updated_product

@router.get("/{product_id}/inventory", response_model=Products.schemas.Inventory)
def get_product_inventory(product_id: int, db: Session = Depends(get_db)):
    inventory = Products.crud.get_inventory_by_product_id(db, product_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory

@router.patch("/{product_id}/inventory")
def adjust_inventory(
    product_id: int,
    quantity_delta: int,
    reason: str = "manual adjustment",
    order_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        updated_inventory = Products.crud.update_inventory_quantity(
            db, product_id, quantity_delta, reason, order_id
        )
        return {
            "message": f"Inventory updated for Product ID {product_id}",
            "new_quantity": updated_inventory.quantity_available
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{product_id}/stock-movements", response_model=List[Products.schemas.StockMovement])
def get_stock_movements(product_id: int, db: Session = Depends(get_db)):
    return Products.crud.get_stock_movements_for_product(db, product_id)

@router.patch("/{product_id}/inventory/settings", response_model=Products.schemas.Inventory)
def update_inventory_settings(
    product_id: int,
    inventory_update: Products.schemas.InventoryUpdate,
    db: Session = Depends(get_db)
):
    try:
        updated_inventory = Products.crud.update_inventory_settings(
            db=db,
            product_id=product_id,
            update_data=inventory_update
        )
        return updated_inventory
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
