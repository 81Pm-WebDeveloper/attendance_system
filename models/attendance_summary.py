from sqlalchemy import Column, Integer, String, Date, Time, UniqueConstraint,Text
from db.database import Base

class Summary(Base):
    __tablename__ = "attendance_summary"
    id = Column(Integer,primary_key=True)
    employee_id = Column(Integer,nullable=False,index=True)
    date = Column(Date, nullable=False, index=True)
    time_in = Column(Time)
    time_out = Column(Time)
    status = Column(String(30), nullable=False)
    remarks = Column(Text)
    __table_args__ = (UniqueConstraint('employee_id', 'date', name='unique_employee_date'),)
    