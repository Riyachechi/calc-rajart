"""
Database setup for Raj Art Service dashboard.

Uses SQLite by default (a single file: raj_art.db) so it works out of the
box with zero configuration. If a DATABASE_URL environment variable is
supplied (e.g. a Postgres URL from Render/Railway), that is used instead,
so saved orders persist properly across deploys on platforms with
ephemeral disks.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./raj_art.db")

# SQLite needs this connect arg when used with FastAPI's threaded requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
