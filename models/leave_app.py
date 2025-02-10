from sqlalchemy import Column, String, Date,DateTime, Text,BIGINT
from db.database2 import Base
class Leave(Base):
    __tablename__ = 'leave_app'

    leave_id = Column(BIGINT, primary_key=True, nullable=False)
    temp_code = Column(String(50), nullable=False)
    emp_username = Column(String(20), nullable=True)
    leave_start = Column(Date, nullable=True)
    leave_end = Column(Date, nullable=True)
    start_day_type = Column(String(35), nullable=True)
    end_day_type = Column(String(35), nullable=True)
    leave_type = Column(String(50), nullable=True)
    leave_pay = Column(String(35), nullable=True)
    leave_reason = Column(Text, nullable=True)
    leave_status = Column(String(35), nullable=True)
    approved_by = Column(String(30), nullable=False)
    approved_at = Column(DateTime, nullable=False)
    leave_approver = Column(String(200), nullable=False)
    leave_attach = Column(String(200), nullable=False)
    created_by = Column(String(35), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_by = Column(String(35), nullable=True)
    updated_at = Column(DateTime, nullable=True)