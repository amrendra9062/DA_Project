from sqlalchemy import Column, Integer, String, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    department = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    interests = Column(String(300), nullable=True)
    session_token = Column(String(100), nullable=True)

