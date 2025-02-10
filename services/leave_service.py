from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.leave_app import Leave
from models.emp_list import Employee2
from datetime import datetime, date
from sqlalchemy import or_,desc,and_
from sqlalchemy.sql import func


def get_leaves(db: Session,check_date: date = None):
    check_date = check_date or date.today() 

    results = db.query(
        Employee2.empID,
        Leave.leave_start,
        Leave.leave_end,
        Leave.leave_reason
    ).join(Leave, Employee2.username == Leave.emp_username).filter(
        Leave.leave_status == "Approved",
        Leave.leave_start <= check_date,  
        Leave.leave_end >= check_date     
    ).all()  

    response = [
        {
            'employee_id': row.empID,
            'leave_start': row.leave_start,
            'leave_end': row.leave_end,
            'reason': row.leave_reason,
        }
        for row in results
    ]

    return response  
