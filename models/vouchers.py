from sqlalchemy import Column, Integer, String, Date, Time, UniqueConstraint
from db.database import Base

class Vouchers(Base):
    __tablename__ = "attendance_vouchers"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    date_used = Column(Date)