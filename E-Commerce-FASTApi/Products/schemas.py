from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime

# =========================================================
# 🗂️ CATEGORY SCHEMAS
# =========================================================

class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class Category(CategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List['Category'] = []

    class Config:
        from_attributes = True

# Update forward reference
Category.model_rebuild()

# =========================================================
# 💰 PRICE HISTORY SCHEMAS
# =========================================================

class ProductPriceHistoryBase(BaseModel):
    old_price: float
    new_price: float
    reason: Optional[str] = None

class ProductPriceHistory(ProductPriceHistoryBase):
    id: int
    product_id: int
    changed_at: datetime

    class Config:
        from_attributes = True

# =========================================================
# 📦 PRODUCT SCHEMAS
# =========================================================

# ---------- Input / Base Models ----------

class ProductBase(BaseModel):
    name: str
    price: float
    category_id: int
    brand: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0, description="Price must be positive")
    category_id: Optional[int] = Field(None, gt=0, description="Category ID must be positive")
    brand: Optional[str] = Field(None, max_length=100)
    attributes: Optional[Dict[str, Any]] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Name cannot be empty or just whitespace')
        return v.strip() if v else v

    @field_validator('brand')
    @classmethod
    def validate_brand(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Brand cannot be empty or just whitespace')
        return v.strip() if v else v

# ---------- Output / Full Models ----------

class ProductSummary(BaseModel):
    id: int
    name: str
    price: float
    brand: Optional[str] = None
    category_name: str
    rating: Optional[float] = None

    class Config:
        from_attributes = True

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    category: Category
    price_history: List[ProductPriceHistory] = []

    class Config:
        from_attributes = True

# =========================================================
# 📋 PAGINATED RESPONSE SCHEMAS
# =========================================================

class ProductListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    products: List[ProductSummary]

# =========================================================
# 🧮 INVENTORY SCHEMAS
# =========================================================

class InventoryBase(BaseModel):
    quantity_available: int = 0
    quantity_reserve: int = 0
    reorder_level: Optional[int] = 10
    reorder_quantity: Optional[int] = 20
    unit_cost: Optional[float] = None
    last_restocked: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    batch_number: Optional[str] = None
    location: Optional[str] = None

class Inventory(InventoryBase):
    id: int
    product_id: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class InventoryUpdate(BaseModel):
    quantity_available: Optional[int] = Field(None, ge=0, description="Cannot be negative")
    reorder_level: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, gt=0)
    
    @field_validator('reorder_quantity')
    @classmethod
    def validate_reorder_quantity(cls, v, info):
        if v is not None and info.data.get('reorder_level') is not None:
            if v <= info.data['reorder_level']:
                raise ValueError('Reorder quantity should be greater than reorder level')
        return v

# =========================================================
# 🔁 STOCK MOVEMENT SCHEMAS
# =========================================================

class StockMovementBase(BaseModel):
    product_id: int
    order_id: Optional[int] = None
    change: int
    reason: Optional[str] = None

class StockMovement(StockMovementBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
