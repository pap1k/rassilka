from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import  Column, Integer, String, Boolean
from orm.db import engine

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, default="")
    api_id = Column(Integer, default=0)
    api_hash = Column(String, default=0)
    session_string = Column(String, default="")

class Distribs(Base):
    __tablename__ = "distribs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(String)
    belong_to = Column(Integer)
    chats = Column(String, default="")

Base.metadata.create_all(bind=engine)