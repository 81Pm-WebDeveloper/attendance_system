from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.leave_app import Leave
from models.emp_list import Employee2
from models.attendance_summary import Summary
from datetime import datetime, date, timedelta
from sqlalchemy import or_,desc,and_
from sqlalchemy.sql import func
import calendar 
import hashlib
import random

def reward_leave(db: Session, data):
    if len(data.vouchers) != 4:
        raise HTTPException(status_code=403, detail="Not enough vouchers/System error: Try Again!")
    if datetime.strptime(data.date, "%Y-%m-%d").weekday() != 5:  # Ensure it's Saturday (5)
        raise HTTPException(status_code=403, detail="Vouchers can only be used on a Saturday.")
    
    emp = db.query(Employee2.username, Employee2.emp_head).filter(Employee2.empID == data.employee_id).first()
    

    if not emp:
        return {'Message': 'Employee not found'}

    temp_code = hashlib.md5(f"{random.randint(1000, 9999999999)}-{datetime.now().strftime('%Y%m%d%H%M%S')}".encode()).hexdigest()

    leave_reason = ",".join(map(str, data.vouchers)) 
    
    leave_form = Leave(
        temp_code=temp_code,
        emp_username=emp.username,
        leave_start=data.date,
        leave_end=data.date,
        start_day_type="Whole Day",
        end_day_type="Whole Day",
        leave_type="Perfect Attendance Reward Saturday Off",
        leave_pay="Paid",
        leave_reason=leave_reason,
        approved_by='',  #DB ERROR
        approved_at='0000-00-00 00:00:00',
        leave_attach='',#DB ERROR
        leave_approver=emp.emp_head,
        created_by=emp.username,
        created_at= datetime.now()
    )

    db.add(leave_form)
    db.commit()
    db.refresh(leave_form)  # Refresh the inserted object

    return {'Message': 'Success'}


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
        Leave.leave_pay == "Paid",
        Leave.leave_start <= end_date,
        Leave.leave_end >= start_date
    ).all()

    for leave in leaves:
        current_date = max(leave.leave_start, start_date)  

        while current_date <= min(leave.leave_end, end_date):
            if current_date.weekday() == 6: # SKIPS SUNDAY
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
        Leave.leave_type,
        Leave.leave_pay
    ).join(Leave, Employee2.username == Leave.emp_username).filter(
        Leave.leave_status == "APPROVED",
        Leave.leave_pay =='Paid',
        Leave.leave_start <= check_date,  
        Leave.leave_end >= check_date     
    ).all()  

    response = [
        {
            'employee_id': row.empID,
            'leave_pay': row.leave_pay,
            'leave_start': row.leave_start,
            'leave_end': row.leave_end,
            'reason': row.leave_reason,
            'leave_type' : row.leave_type        
        }
        for row in results
    ]

    return response  


def leave_reports(db: Session, start_date: str, end_date: str, employee_id: int):
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    emp = db.query(Employee2.username, Employee2.fullname).filter(Employee2.empID == employee_id).first()
    
    if not emp:
        return {"error": "Employee not found"}

    records = (
        db.query(
            Leave.leave_type,
            Leave.leave_start,
            Leave.leave_end,
            Leave.leave_pay,
            Leave.start_day_type,
            Leave.end_day_type
        )
        .filter(
            Leave.emp_username == emp.username,
            Leave.leave_status == 'APPROVED',
            Leave.leave_start <= end_date,
            Leave.leave_end >= start_date
        )
        .all()
    )

    result = {}
    leave_frequency = {}

    unique_days = set() #REMOVE

    for record in records:
        current_date = max(record.leave_start, start_date)
        leave_end = min(record.leave_end, end_date)

        while current_date <= leave_end:
            if current_date.weekday() == 6:  # Skip Sundays
                current_date += timedelta(days=1)
                continue  

            if current_date in unique_days: #REMOVE
                current_date += timedelta(days=1)
                continue  

            unique_days.add(current_date) # REMOVE

            year_month = f"{current_date.year} {calendar.month_name[current_date.month]}"

            if year_month not in result:
                result[year_month] = {
                    "Vacation Leave": 0,
                    "Sick Leave": 0,
                    "Solo Parent Leave": 0,
                    "Other Leave": 0,
                    "Unpaid Leave": 0,
                }
                leave_frequency[year_month] = 0  # Initialize frequency

            if record.leave_pay == 'Paid':
                if record.leave_type in ["Vacation Leave", "Sick Leave"]:
                    leave_type = record.leave_type
                elif record.leave_type in ['Paternity Maternity Leave', 'Solo Parent Leave', 'Emergency Leave', 'Special Leave']:
                    leave_type = "Other Leave"
                else:
                    continue  
            else:
                leave_type = "Unpaid Leave"
               
            leave_frequency[year_month] += 1

                
            if current_date == record.leave_start and record.start_day_type in ["Morning", "Afternoon"]:
                    leave_count = 0.5
            elif current_date == record.leave_end and record.end_day_type in ["Morning", "Afternoon"]:
                    leave_count = 0.5
            else:
                    leave_count = 1

            result[year_month][leave_type] += leave_count

            current_date += timedelta(days=1)

    # Structure the response properly
    formatted_result = {
        "fullname": emp.fullname,
        "leave_data": [
            {
                "date": month,
                "results": {**leaves,"leave_frequency": leave_frequency.get(month, 0)}
                
            }
            for month, leaves in result.items()
        ]
    }

    return formatted_result
