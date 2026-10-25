import datetime
import os
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select,JSON, Column
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

ENV_DIR = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(ENV_DIR)

class PredictionBase(SQLModel):
    seed_data: dict = Field(sa_column=Column(JSON))
    probability: float
    prediction: str

class PredictionSeedLog(PredictionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory= lambda : datetime.now(timezone.utc)
    )

class PredictionPublic(PredictionBase):
    id: int

sqlite_file_name = "seed_logs.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(os.getenv("DATABASE_URL",sqlite_url))

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
