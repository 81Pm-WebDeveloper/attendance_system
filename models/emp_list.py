from sqlalchemy import Column, Integer, String, Date,DateTime, TIMESTAMP
from db.database2 import Base

class Employee2(Base):
    __tablename__ = 'emp_list'
    idx = Column(Integer,primary_key=True)
    empID = Column(Integer)
    fullname = Column(String(35), nullable=True)
    username = Column(String(20),nullable=True)
    password = Column(String(50),nullable=True)
    usertype = Column(String(15),nullable=True)
    department = Column(String(50),nullable=True)
    position = Column(String(50),nullable=True)
    company = Column(String(50),nullable=True)
    branch = Column(String(20),nullable=False)
    emp_status = Column(String(30),nullable=False)
    work_sched = Column(String(50),nullable=False)
    emp_head = Column(String(199),nullable=False)
    emp_email = Column(String(199),nullable=False)
    status = Column(String(12),nullable=True)
    memo = Column(String(5),nullable=False)
    date_started = Column(Date,nullable=False)
    date_ended = Column(Date,nullable=False)
    created_by = Column(String(20),nullable=False)
    created_at = Column(DateTime,nullable=False)
    updated_by = Column(String(20),nullable=False)
    created_at = Column(TIMESTAMP,nullable=False)