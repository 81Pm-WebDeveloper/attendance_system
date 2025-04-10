from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("database_url2")  # REPLACE WITH DOT ENV

engine2 = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True,
    )

SessionLocal2 = sessionmaker(autocommit=False, autoflush=False, bind=engine2)

Base = declarative_base()


def get_db2():
    db2 = SessionLocal2()
    try:
        yield db2
    finally:
        db2.close()
