# models.py
from sqlalchemy import Column, Integer, String, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(200), unique=True)
    password = Column(String(200))
    department = Column(String(100))
    bio = Column(Text)
    interests = Column(String(300))

