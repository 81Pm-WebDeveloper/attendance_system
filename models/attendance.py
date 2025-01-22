from sqlalchemy import Column, Integer, String, Date, Time
from db.database import Base

class Attendance(Base):
    __tablename__ = 'eportal_attendance'
    id = Column(Integer, primary_key= True)
    employee_id = Column(Integer,nullable= False)
    date = Column(Date, nullable=False)
    time_in = Column(Time, nullable=False)
    time_out = Column(Time, nullable=True)
    status = Column(String(30), nullable=True)
