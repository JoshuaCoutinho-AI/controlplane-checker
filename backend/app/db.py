"""
SQLite for this sprint. To swap to Postgres later: change DATABASE_URL to
e.g. postgresql+psycopg://user:pass@host/db and add psycopg to
requirements.txt — no other code in this module needs to change, since
SQLAlchemy abstracts the dialect.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./controlplane.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
