from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.middleware.cors import CORSMiddleware

DATABASE_URL = "postgresql://postgres:141722@localhost:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Модель таблицы Clients
class ClientDB(Base):
    __tablename__ = "clients"

    account_id = Column(Integer, primary_key=True, index=True)
    is_checked = Column(String, nullable=True)
    is_commercial = Column(Boolean, nullable=True)  # Изменено на nullable=True
    address = Column(String, nullable=True)  # Изменено на nullable=True
    building_type = Column(String, nullable=True)  # Изменено на nullable=True
    rooms_count = Column(Integer, nullable=True)  # Изменено на nullable=True
    residents_count = Column(Integer, nullable=True)  # Изменено на nullable=True
    total_area = Column(Float, nullable=True)  # Изменено на nullable=True
    consumption = Column(JSON, nullable=True)  # Изменено на nullable=True
    priority = Column(Text, nullable=True)


# Pydantic-модель для валидации данных
class Client(BaseModel):
    accountId: int  # Единственное обязательное поле
    isChecked: Optional[str] = None
    isCommercial: Optional[bool] = None
    address: Optional[str] = None
    buildingType: Optional[str] = None
    roomsCount: Optional[int] = None
    residentsCount: Optional[int] = None
    totalArea: Optional[float] = None
    consumption: Optional[Dict[str, int]] = None
    priority: Optional[str] = None

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
# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Создание таблиц (один раз)
Base.metadata.create_all(bind=engine)


# Получить всех клиентов
@app.get("/clients/get")
def get_all_clients(db: Session = Depends(get_db)):
    clients = db.query(ClientDB).all()
    return {"clients": clients}


# Добавить клиента
@app.post("/clients")
def add_client(client: Client, db: Session = Depends(get_db)):
    db_client = ClientDB(
        account_id=client.accountId,
        is_checked=client.isChecked,
        is_commercial=client.isCommercial,
        address=client.address,
        building_type=client.buildingType,
        rooms_count=client.roomsCount,
        residents_count=client.residentsCount,
        total_area=client.totalArea,
        consumption=client.consumption,
        priority=client.priority
    )
    db.add(db_client)
    try:
        db.commit()
        db.refresh(db_client)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "created", "client": db_client}


# Удалить клиента по account_id
@app.delete("/clients/{account_id}")
def delete_client(account_id: int, db: Session = Depends(get_db)):
    client = db.query(ClientDB).filter(ClientDB.account_id == account_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"status": "deleted"}


# Полное обновление клиента (PUT)
@app.put("/clients/{account_id}")
def update_client(account_id: int, client: Client, db: Session = Depends(get_db)):
    db_client = db.query(ClientDB).filter(ClientDB.account_id == account_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Обновляем только те поля, которые были переданы
    update_data = client.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_client, field if field != "accountId" else "account_id", value)

    db.commit()
    db.refresh(db_client)
    return {"status": "updated", "client": db_client}


# Частичное обновление клиента (PATCH)
@app.patch("/clients/{account_id}")
def patch_client(account_id: int, fields: Dict[str, Any], db: Session = Depends(get_db)):
    allowed_fields = {
        "isChecked", "isCommercial", "address", "buildingType",
        "roomsCount", "residentsCount", "totalArea", "consumption", "priority"
    }
    if not fields or not all(field in allowed_fields for field in fields.keys()):
        raise HTTPException(status_code=400, detail="Invalid fields")

    db_client = db.query(ClientDB).filter(ClientDB.account_id == account_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Преобразуем поля из camelCase в snake_case для модели БД
    mapping = {
        "isChecked": "is_checked",
        "isCommercial": "is_commercial",
        "buildingType": "building_type",
        "roomsCount": "rooms_count",
        "residentsCount": "residents_count",
        "totalArea": "total_area"
    }
    for field, value in fields.items():
        db_field = mapping.get(field, field)
        setattr(db_client, db_field, value)

    db.commit()
    db.refresh(db_client)
    return {"status": "patched", "client": db_client}


@app.post("/clients/batch")
def add_clients_batch(clients: List[Client], db: Session = Depends(get_db)):
    db_clients = []
    for client in clients:
        db_client = ClientDB(
            account_id=client.accountId,
            is_checked=client.isChecked,
            is_commercial=client.isCommercial,
            address=client.address,
            building_type=client.buildingType,
            rooms_count=client.roomsCount,
            residents_count=client.residentsCount,
            total_area=client.totalArea,
            consumption=client.consumption,
            priority=client.priority
        )
        db_clients.append(db_client)
    try:
        db.add_all(db_clients)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error inserting clients batch: {str(e)}")
    return {"status": "created", "added": len(db_clients)}


@app.delete("/clients/")
def delete_all_clients(db: Session = Depends(get_db)):
    try:
        num_deleted = db.query(ClientDB).delete()
        db.commit()
        return {"status": "success", "deleted_count": num_deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting all clients: {str(e)}")



  