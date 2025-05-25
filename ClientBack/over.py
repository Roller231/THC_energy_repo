from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.cors import CORSMiddleware

DATABASE_URL = "postgresql://postgres:141722@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OverConsumerDB(Base):
    __tablename__ = "over_consumers"

    account_id = Column(Integer, primary_key=True, index=True)
    is_checked = Column(String, nullable=True)
    address = Column(String, nullable=True)
    priority = Column(Text, nullable=True)
    avg_consumption_6m = Column(Float, nullable=True)  # Новое поле


class OverConsumer(BaseModel):
    accountId: int
    isChecked: Optional[str] = None
    address: Optional[str] = None
    priority: Optional[str] = None
    avgConsumption6m: Optional[float] = None  # Новое поле

    class Config:
        orm_mode = True


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Можно ["*"] для разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/over_consumers")
def get_all_over_consumers(db: Session = Depends(get_db)):
    consumers = db.query(OverConsumerDB).all()
    return {"over_consumers": consumers}


@app.post("/over_consumers")
def add_over_consumer(consumer: OverConsumer, db: Session = Depends(get_db)):
    db_consumer = OverConsumerDB(
        account_id=consumer.accountId,
        is_checked=consumer.isChecked,
        address=consumer.address,
        priority=consumer.priority,
        avg_consumption_6m=consumer.avgConsumption6m  # Новое поле
    )
    db.add(db_consumer)
    try:
        db.commit()
        db.refresh(db_consumer)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "created", "over_consumer": db_consumer}


@app.delete("/over_consumers/{account_id}")
def delete_over_consumer(account_id: int, db: Session = Depends(get_db)):
    consumer = db.query(OverConsumerDB).filter(OverConsumerDB.account_id == account_id).first()
    if not consumer:
        raise HTTPException(status_code=404, detail="Over consumer not found")
    db.delete(consumer)
    db.commit()
    return {"status": "deleted"}


@app.put("/over_consumers/{account_id}")
def update_over_consumer(account_id: int, consumer: OverConsumer, db: Session = Depends(get_db)):
    db_consumer = db.query(OverConsumerDB).filter(OverConsumerDB.account_id == account_id).first()
    if not db_consumer:
        raise HTTPException(status_code=404, detail="Over consumer not found")

    update_data = consumer.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_consumer, field if field != "accountId" else "account_id", value)

    db.commit()
    db.refresh(db_consumer)
    return {"status": "updated", "over_consumer": db_consumer}


@app.patch("/over_consumers/{account_id}")
def patch_over_consumer(account_id: int, fields: Dict[str, Any], db: Session = Depends(get_db)):
    allowed_fields = {"isChecked", "address", "priority", "avgConsumption6m"}  # Обновлено
    if not fields or not all(field in allowed_fields for field in fields.keys()):
        raise HTTPException(status_code=400, detail="Invalid fields")

    db_consumer = db.query(OverConsumerDB).filter(OverConsumerDB.account_id == account_id).first()
    if not db_consumer:
        raise HTTPException(status_code=404, detail="Over consumer not found")

    mapping = {
        "isChecked": "is_checked",
        "avgConsumption6m": "avg_consumption_6m"  # Новое поле
    }
    for field, value in fields.items():
        db_field = mapping.get(field, field)
        setattr(db_consumer, db_field, value)

    db.commit()
    db.refresh(db_consumer)
    return {"status": "patched", "over_consumer": db_consumer}


@app.post("/over_consumers/batch")
def add_over_consumers_batch(consumers: List[OverConsumer], db: Session = Depends(get_db)):
    db_consumers = []
    for consumer in consumers:
        db_consumer = OverConsumerDB(
            account_id=consumer.accountId,
            is_checked=consumer.isChecked,
            address=consumer.address,
            priority=consumer.priority,
            avg_consumption_6m=consumer.avgConsumption6m  # Новое поле
        )
        db_consumers.append(db_consumer)
    try:
        db.add_all(db_consumers)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error inserting batch: {str(e)}")
    return {"status": "created", "added": len(db_consumers)}


@app.delete("/over_consumers")
def delete_all_over_consumers(db: Session = Depends(get_db)):
    try:
        num_deleted = db.query(OverConsumerDB).delete()
        db.commit()
        return {"status": "success", "deleted_count": num_deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all: {str(e)}")