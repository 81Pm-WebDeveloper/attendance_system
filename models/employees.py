from sqlalchemy import Column, Integer, String
from db.database import Base

class Employee(Base):
    __tablename__ = 'eportal_employee'
    employee_id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    department = Column(String(30), nullable=False)
    position = Column(String(30), nullable=False)