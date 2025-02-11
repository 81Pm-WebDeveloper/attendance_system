from sqlalchemy import Column, Integer, String, Date, Index
from db.database import Base

class Vouchers(Base):
    __tablename__ = "attendance_vouchers"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False, index=True)  
    issue_date = Column(Date, nullable=False, index=True)  
    expiry_date = Column(Date, nullable=False)
    date_used = Column(Date)

    __table_args__ = (
        Index("idx_vouchers_employee_date", "employee_id", "issue_date"), 
    )
