import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # No rompemos import; fallará en runtime con mensaje claro.
    print("[WARN] DATABASE_URL no está seteada. Configure Neon y el .env antes de ejecutar.")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
) if DATABASE_URL else None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True) if engine else None

Base = declarative_base()

def get_db():
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL no configurada. Establezca la variable de entorno antes de iniciar la app.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()