from sqlalchemy import Column, Integer, String, Date, Time,Index,UniqueConstraint,ForeignKey
from db.database import Base

class Attendance(Base):
    __tablename__ = 'eportal_attendance'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False)
    time_in = Column(Time, nullable=False)
    time_out = Column(Time, nullable=True)
    status = Column(String(30), nullable=True) #CONVERT TO ENUM 
    checkout_status = Column(String(30), nullable=True) #CONVERT TO ENUM 
    late_min = Column(Integer,nullable=True)
    undertime_min = Column(Integer,nullable=True)
    voucher_id = Column(Integer, ForeignKey('attendance_vouchers.id'), nullable=True)

    
    __table_args__ = (
        Index("idx_date", "date"),  # Keep if you frequently query by date alone
        UniqueConstraint('employee_id', 'date', name='uq_employee_date')  # Ensures uniqueness
    )

