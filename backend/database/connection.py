import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite setup
SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///./ims.db")
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
