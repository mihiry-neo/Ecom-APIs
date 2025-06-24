from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password = Column(String(255), nullable=False)
    gender = Column(String(20))
    age = Column(Integer)
    phone_number = Column(String(20))
    nationality = Column(String(50))
    is_active = Column(Boolean, default=True)
