from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate
from auth import get_password_hash

def create_user(db: Session, user: UserCreate):
    hashed_pw = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_pw,
        gender=user.gender,
        age=user.age,
        phone_number=user.phone_number,
        nationality=user.nationality,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session):
    return db.query(User).all()

def delete_user(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    if user:
        db.delete(user)
        db.commit()
        return True
    return False