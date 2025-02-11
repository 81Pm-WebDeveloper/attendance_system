from sqlalchemy import Column, Integer, String, Date, Time,Index
from db.database import Base

class Attendance(Base):
    __tablename__ = 'eportal_attendance'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    time_in = Column(Time, nullable=False)
    time_out = Column(Time, nullable=True)
    status = Column(String(30), nullable=True)

    __table_args__ = (
        Index("idx_employee_date", "employee_id", "date"),  
        Index("idx_date", "date"),  
    )
