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
                if existing_summary.status != 'On leave':
                    existing_summary.status = 'On leave'
                    if leave.leave_type == 'Official Business':
                        existing_summary.checkout_status = 'Official Business'

                    updated_summaries.append({
                        "employee_id": existing_summary.employee_id,
                        "date": existing_summary.date.strftime("%Y-%m-%d"),
                        "status": existing_summary.status,
                        "checkout_status": existing_summary.checkout_status
                    })
            current_date += timedelta(days=1)

    db1.commit()
    return {"message": "Summaries updated successfully","Updated": updated_summaries}



def get_leaves(db: Session,check_date: date = None):
    check_date = check_date or date.today() 

    results = db.query(
        Employee2.empID,
        Leave.leave_start,
        Leave.leave_end,
        Leave.leave_reason,
        Leave.leave_type
    ).join(Leave, Employee2.username == Leave.emp_username).filter(
        Leave.leave_status == "APPROVED",
        Leave.leave_start <= check_date,  
        Leave.leave_end >= check_date     
    ).all()  

    response = [
        {
            'employee_id': row.empID,
            'leave_start': row.leave_start,
            'leave_end': row.leave_end,
            'reason': row.leave_reason,
            'leave_type' : row.leave_type        
        }
        for row in results
    ]

    return response  





def leave_reports(db: Session, start_date: str, end_date: str, username: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    records = (
        db.query(
            Leave.emp_username,
            Leave.leave_type,
            Leave.leave_start,
            Leave.leave_end
        )
        .filter(
            Leave.emp_username == username,
            Leave.leave_status == 'APPROVED',
            Leave.leave_start <= end_date,
            Leave.leave_end >= start_date
        )
        .all()
    )

    result = {}
    unique_days = set()  # Track (employee, date) to avoid duplicate counting

    for record in records:
        current_date = max(record.leave_start, start_date)
        leave_end = min(record.leave_end, end_date)

        while current_date <= leave_end:
            if current_date.weekday() == 6:  
                current_date += timedelta(days=1)
                continue  

            if (record.emp_username, current_date) in unique_days:
                current_date += timedelta(days=1)
                continue  

            unique_days.add((record.emp_username, current_date))  

            year_month = f"{current_date.year} {calendar.month_name[current_date.month]}"

            if record.emp_username not in result:
                result[record.emp_username] = {}

            if year_month not in result[record.emp_username]:
                result[record.emp_username][year_month] = {}

            if record.leave_type not in result[record.emp_username][year_month]:
                result[record.emp_username][year_month][record.leave_type] = 0

            result[record.emp_username][year_month][record.leave_type] += 1

            current_date += timedelta(days=1)

    return result
