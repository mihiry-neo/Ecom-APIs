from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Database and Base import
from database import SessionLocal, engine, Base

# Routers
from Products.routes import router as products_router
from Orders.routes import order_router
from Users.routes import router as users_router
from Orders.routes import cart_router

# Logger and Data Generator
from datagen import DataGenerator

# Models
from Users.models import User
from Products.models import Product, Category

# Load environment variables and create DB tables
load_dotenv()
Base.metadata.create_all(bind=engine)
generator = DataGenerator()
scheduler = BackgroundScheduler()

# APScheduler Task
def scheduled_data_generation():
    db: Session = SessionLocal()
    try:

        if db.query(Category).count() == 0:
            categories = generator.create_categories(db)
        else:
            categories = db.query(Category).all()

        generator.create_products(db, categories=categories, count=10)

        users = db.query(User).all()
        products = db.query(Product).all()

        if users and products:
            generator.create_carts_and_orders(db, users, products, num_orders=10)
    finally:
        db.close()
# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")
    scheduler.add_job(scheduled_data_generation, "interval", minutes=10)
    scheduler.start()
    yield
    print("🛑 Shutting down...")
    scheduler.shutdown(wait=False)

# FastAPI App
app = FastAPI(description="FastAPI E-commerce Project", lifespan=lifespan)

# Routers
app.include_router(users_router, prefix="/users")
app.include_router(products_router)
app.include_router(order_router)
app.include_router(cart_router)