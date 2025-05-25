# from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
# from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
#
# engine = create_engine('postgresql://postgres:Admin@localhost:5432/THS')
#
#
# class Base(DeclarativeBase):
#     pass
#
#
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
#
# class User(Base):
#     __tablename__ = 'users'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     username = Column(String)
#     tg_id = Column(String, nullable=False, unique=True)
#     phone_number = Column(String, nullable=True, unique=True)
#
#     complaints = relationship('Complaint', back_populates='user')
#
#
# class Complaint(Base):
#     __tablename__ = 'complaints'
#
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     message = Column(String, nullable=False)
#     user_address = Column(String, nullable=True)
#     address_complaints = Column(String, nullable=True)
#
#     user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
#     user = relationship('User', back_populates='complaints')
#
#
#
#
