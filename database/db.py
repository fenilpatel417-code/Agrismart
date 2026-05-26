import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read database URL from environment (e.g. Render/Heroku PostgreSQL)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if SQLALCHEMY_DATABASE_URL:
    # Heroku / Render postgresql dialect fix: replace postgres:// with postgresql://
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # Check if we have a persistent Render disk mount path
    if os.path.exists("/var/lib/agrismart"):
        db_path = "/var/lib/agrismart/agrismart.db"
    else:
        db_path = "./agrismart.db"
        
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

