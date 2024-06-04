from sqlalchemy import create_engine


engine = create_engine("sqlite:///database.db?charset=utf8mb4")

