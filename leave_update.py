from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.leave_app import Leave
from models.emp_list import Employee2
from models.attendance_summary import Summary
from datetime import datetime, date
from sqlalchemy import or_,desc,and_
from sqlalchemy.sql import func
import calendar 
from datetime import datetime, timedelta
import services.summary_service as summaryService
from db.database import get_db
from db.database2 import get_db2

def update_summaries(db1: Session, db2: Session, start_date: date =None, end_date: date = None):
    updated_summaries = []
    start_date = start_date or date.today()
    end_date = end_date or date.today()

    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    leaves = db2.query(
        Employee2.empID,
        Leave.leave_start,
        Leave.leave_end,
        Leave.leave_reason,
        Leave.leave_type
    ).join(Leave, Employee2.username == Leave.emp_username).filter(
        Leave.leave_status == "APPROVED",
        Leave.leave_start <= end_date,
        Leave.leave_end >= start_date
    ).all()

    for leave in leaves:
        current_date = max(leave.leave_start, start_date)  

        while current_date <= min(leave.leave_end, end_date):
            if current_date.weekday() == 6:
                current_date += timedelta(days=1)
                continue  

            existing_summary = db1.query(Summary).filter(
                Summary.employee_id == leave.empID,
                Summary.date == current_date
            ).first()

            if existing_summary:
                if existing_summary.status != 'On leave' or 'Official Business':
                    existing_summary.status = 'On leave'
                    if leave.leave_type == 'Official Business':
                        existing_summary.status = 'Official Business'
                    if leave.leave_type == 'Perfect Attendance Reward Saturday Off':
                        existing_summary.status = 'PARSO'
                    updated_summaries.append({
                        "employee_id": existing_summary.employee_id,
                        "date": existing_summary.date.strftime("%Y-%m-%d"),
                        "status": existing_summary.status,
                        "checkout_status": existing_summary.checkout_status
                    })
            current_date += timedelta(days=1)

    db1.commit()
    return {"message": "Summaries updated successfully","Updated": updated_summaries}

if __name__ == "__main__":
    db = next(get_db())
    db2 = next(get_db2())
    today = date.today()
    date_from = today - timedelta(days=5)
    #print(f"{date_from} - {today}")
    try:
        result = update_summaries(db,db2, date_from, today)
        #print(result)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        db2.close()