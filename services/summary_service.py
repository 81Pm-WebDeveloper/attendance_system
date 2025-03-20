from fastapi import HTTPException
#from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance_summary import Summary
from models.attendance import Attendance
from datetime import datetime, date
from sqlalchemy import asc, or_,desc,func,case,extract, and_
from schemas.summary import UpdateSummary
from typing import Dict, List
from math import ceil
from models.emp_list import Employee2
from collections import defaultdict
import calendar

def insert_summary(db: Session, data):
    try:
        unique_entries = []
        unique_employee_dates = set()

        for item in data:
            item['date'] = item.get('date') or date.today()
            emp_date = (item['employee_id'], item['date'])

            existing_entry = db.query(Summary).filter(
                Summary.employee_id == item['employee_id'], 
                Summary.date == item['date']
            ).first()

            if existing_entry:
                existing_entry.att_id = item['att_id']  #Assign att_id for faster lookups (Report, Voucher issuance etc.)
                
                if item.get('status') == 'On time' and existing_entry.status != 'On leave':
                    existing_entry.status = 'On time'

                if existing_entry.time_in is None and item.get('time_in'):
                    existing_entry.time_in = item['time_in']

                if item.get('time_out'):
                    if not existing_entry.time_out or item['time_out'] > existing_entry.time_out:
                        existing_entry.time_out = item['time_out']

                if item.get('checkout_status') and item['checkout_status'].strip() not in ['No info', ''] and existing_entry.checkout_status != 'Official Business':
                    existing_entry.checkout_status = item['checkout_status']
                elif not existing_entry.checkout_status and existing_entry.time_in:
                    existing_entry.checkout_status = 'No info'
                    
                db.add(existing_entry)

            else:
                # Prevent duplicate inserts
                if emp_date not in unique_employee_dates:
                    if item.get('status') != 'On time':
                        item['status'] = 'No info'  
                    unique_entries.append(item)
                    unique_employee_dates.add(emp_date)
                else:
                    print(f"Duplicate employee_id found for Date {item['date']} and employee_id {item['employee_id']}")

        if unique_entries:
            existing_keys = {
                (entry.employee_id, entry.date) for entry in db.query(Summary).filter(
                    Summary.date.in_([e['date'] for e in unique_entries]),
                    Summary.employee_id.in_([e['employee_id'] for e in unique_entries])
                ).all()
            }
            
            filtered_entries = [e for e in unique_entries if (e['employee_id'], e['date']) not in existing_keys]
            
            if filtered_entries:
                db.bulk_insert_mappings(Summary, filtered_entries)

        db.commit()
        return unique_entries  

    except Exception as e:
        db.rollback() 
        raise Exception(f"Failed to insert summary data: {e}")


def fetch_summary(
    db1: Session,
    db2: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,  # Change to single date
    employee_id_filter: str = None,
) -> Dict:

    if page_size:
        offset = (page - 1) * page_size
    else:
        offset = 0  

    base_query = db1.query(Summary, Attendance.voucher_id)\
        .outerjoin(Attendance, Summary.att_id == Attendance.id)  # Join Attendance to get voucher_id

    if search_query:
        search_term = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Summary.employee_id.like(search_term),
                Summary.status.like(search_term),
            )
        )

    if date_from:
        base_query = base_query.filter(Summary.date >= date_from)
    if date_to:
        base_query = base_query.filter(Summary.date <= date_to)

    if employee_id_filter:
        base_query = base_query.filter(Summary.employee_id == employee_id_filter).order_by(Summary.date.desc())
        
    total_count = base_query.count()

    status_counts = (
        base_query
        .with_entities(
            case(
                (Summary.status == "Official Business", "On time"),
                else_=Summary.status
            ).label("adjusted_status"),
            func.count(Summary.status)
        )
        .group_by("adjusted_status")
        .all()
    )

    status_summary = {status: count for status, count in status_counts}

    if page_size:
        result = (
            base_query.order_by(Summary.date.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        limit = ceil(total_count / page_size)
    else:
        result = base_query.all() 
        limit = total_count  

    employee_data = (
        db2.query(
            Employee2.empID,
            Employee2.fullname,
            Employee2.position,
            Employee2.department,
            Employee2.company,
            Employee2.branch,
        )
        .filter(Employee2.empID.in_([summary.employee_id for summary, _ in result]))
        .order_by(Employee2.department) 
        .all()
    )

    employee_map = {employee.empID: employee for employee in employee_data}
   
    sorted_result = sorted(
        result, 
        key=lambda row: employee_map.get(row[0].employee_id).department if employee_map.get(row[0].employee_id) else ""
    )

    return {
        "total_records": total_count,
        "page": page if page_size else 1,  
        "limit": limit,
        "status_summary": status_summary,
        "results": [
            {
                **summary.__dict__,
                "employee_department": employee_map.get(summary.employee_id).department,
                "employee_name": employee_map.get(summary.employee_id).fullname,
                "employee_position": employee_map.get(summary.employee_id).position,
                "company": f"{employee_map.get(summary.employee_id).company} ({employee_map.get(summary.employee_id).branch})",
                "voucher_id": voucher_id  
            }
            for summary, voucher_id in sorted_result  
        ],
    }




def fetch_count(
    db1: Session, 
    db2: Session,  
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
) -> Dict:
    
    base_query = db1.query(
        Summary,
    )

    if search_query:
        search_term = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Summary.employee_id.like(search_term),
                Summary.status.like(search_term),
            )
        )

    if date_from:
        base_query = base_query.filter(Summary.date >= date_from)
    if date_to:
        base_query = base_query.filter(Summary.date <= date_to)

    if employee_id_filter:
        base_query = base_query.filter(Summary.employee_id == employee_id_filter)

    result = base_query.order_by(Summary.date.desc()).all()

    # Fetch employee data from db2 (Employee2)
    employees = db2.query(
        Employee2.empID,
        Employee2.fullname.label("employee_name"),
        Employee2.department.label("employee_department"),
        Employee2.position.label("employee_position"),
        Employee2.company.label("employee_company"),
        Employee2.branch.label("employee_branch"),
    ).filter(Employee2.status == "active").all()

    employee_summary = defaultdict(lambda: {
        "employee_id":None,
        "employee_name": None,
        "employee_department": None,
        "employee_position": None,
        "employee_company": None,
        "employee_branch": None,
        "status_counts": defaultdict(int)
    })

    
    for summary in result:
        employee = next((e for e in employees if e.empID == summary.employee_id), None)
        if employee:
            employee_key = summary.employee_id
            employee_summary[employee_key]["employee_id"] = employee.empID
            employee_summary[employee_key]["employee_name"] = employee.employee_name
            employee_summary[employee_key]["employee_department"] = employee.employee_department
            employee_summary[employee_key]["employee_position"] = employee.employee_position
            employee_summary[employee_key]["employee_company"] = employee.employee_company
            employee_summary[employee_key]["employee_branch"] = employee.employee_branch
            status_key = "On time" if summary.status == "Official Business" else summary.status
            employee_summary[employee_key]["status_counts"][status_key] += 1


    final_results = [
        {
            "employee_id": data["employee_id"],
            "employee_name": data["employee_name"],
            "employee_department": data["employee_department"],
            "employee_position": data["employee_position"],
            "employee_company": f"{data['employee_company']} ({data['employee_branch']})",
            "status_counts": dict(data["status_counts"]),
        }
        for data in employee_summary.values()
    ]

    # Fetch the status counts from db1 for the Summary table
    status_counts = (
        base_query
        .with_entities(
            case(
                (Summary.status == "Official Business", "On time"),
                else_=Summary.status
            ).label("adjusted_status"),
            func.count(Summary.status)
        )
        .group_by("adjusted_status")
        .all()
    )

    status_summary = {status: count for status, count in status_counts}

    return {
        "status_summary": status_summary,
        "results": final_results,
    }



def update_status(db: Session, updates: List[UpdateSummary]):
    updated_summaries = []
    failed_updates = []

    for data in updates:
        summary = db.query(Summary).filter(Summary.id == data.id).first()

        if not summary:
            failed_updates.append(data.id)
            continue  

        summary.status = data.status
        summary.remarks = data.remarks

        if data.checkout_status is not None:
            summary.checkout_status = data.checkout_status

        updated_summaries.append(summary)

    if not updated_summaries:
        raise HTTPException(status_code=400, detail="No records to update")

    db.bulk_save_objects(updated_summaries)
    db.commit()

    for summary in updated_summaries:
        db.refresh(summary)

    return {"updated": [summary.id for summary in updated_summaries], "failed": failed_updates}



def attendanceReport(db: Session, start_date: datetime, end_date: datetime, employee_id: int):
    records = (
        db.query(
            extract('year', Summary.date).label("year"),
            extract('month', Summary.date).label("month"),
            func.coalesce(
                func.sum(
                    case(
                        (Summary.status.notin_(['On time', 'On leave']), Attendance.late_min),
                        else_=0
                    )
                ), 0
            ).label("total_late"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(
                            Summary.checkout_status.notin_(['On time', 'Official Business']),
                            Summary.status.notin_(['On leave', 'Official Business'])
                        ), Attendance.undertime_min),
                        else_=0
                    )
                ), 0
            ).label("total_undertime"),
            func.coalesce(func.sum(case((Summary.status == 'Late', 1), else_=0)), 0).label("late_count"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(Summary.status == 'No info', Attendance.late_min == None), 1), 
                        else_=0
                    )
                ), 0
            ).label("no_info_count"),
            func.coalesce(
                func.sum(
                    case(
                        (and_(Summary.status == 'No info', Attendance.late_min > 0), 1), 
                        else_=0
                    )
                ), 0
            ).label("late_no_info_count"),
            func.coalesce(
                func.sum(
                    case(
                        (Summary.status == 'Half day', 1),  
                        (Summary.checkout_status == 'Half day', 1), 
                        else_=0
                    )
                ), 
                0
            ).label("halfday_count"), #Time in
            func.coalesce(func.sum(case((Summary.status == 'Absent', 1), else_=0)), 0).label("absent_count"),
            func.coalesce(func.sum(case((Summary.checkout_status == 'Undertime', 1), else_=0)), 0).label("undertime_count"),
            func.coalesce(func.sum(case((Summary.checkout_status == 'No info', 1), else_=0)), 0).label("no_checkout"),
        )
        .outerjoin(Attendance, Summary.att_id == Attendance.id)
        .filter(
            Summary.date >= start_date,
            Summary.date <= end_date,
            Summary.employee_id == employee_id
        )
        .group_by("year", "month")  
        .order_by("year", "month")
        .all()

    )
    
    month_lookup = calendar.month_name  

    return [
    {
        "date": f"{int(record.year)} {month_lookup[int(record.month)]}",  # Properly formatted date string
        "results": {
            "total_late_min": record.total_late,
            "total_undertime_min": record.total_undertime,
            "Late": record.late_count,
            "Late(No info)": record.late_no_info_count,
            "Absent": record.absent_count,
            "No Info": record.no_info_count,
            "Half Day": record.halfday_count,
            "Undertime": record.undertime_count,
            "No timeout": record.no_checkout,
        }
    }
    for record in records
]