from sqlalchemy import Column, Integer, String, Date, Time, Text, ForeignKey, Index,UniqueConstraint
from db.database import Base

class Summary(Base):
    __tablename__ = "attendance_summary"
    id = Column(Integer, primary_key=True)
    att_id = Column(Integer, ForeignKey('eportal_attendance.id'), nullable=True) 
    employee_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    time_in = Column(Time)
    time_out = Column(Time)
    status = Column(String(30), nullable=False) #CONVERT TO ENUM 
    checkout_status = Column(String(30), nullable=True) #CONVERT TO ENUM 
    remarks = Column(Text)

    __table_args__ = (
        UniqueConstraint('employee_id', 'date', name='uq_employee_date'),
    )
