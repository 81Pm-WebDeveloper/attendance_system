from fastapi import HTTPException
#from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance import Attendance
from models.employees import Employee
from models.attendance_summary import Summary
from datetime import datetime, date
from sqlalchemy import asc, or_,desc
from typing import Dict
from sqlalchemy.sql import func
from math import ceil


def insert_summary(db: Session, data):
    try:
        unique_entries = []
        unique_employee_dates = set()
        
        for item in data:
            emp_date = (item['employee_id'], item['date'])  
            
            existing_entry = db.query(Summary).filter(Summary.employee_id == item['employee_id'], 
                                                      Summary.date == item['date']).first()
            
            if not existing_entry:  
                if emp_date not in unique_employee_dates:  
                    unique_entries.append(item)
                    unique_employee_dates.add(emp_date)
                else:
                    print(f"Duplicate employee_id found for Date {item['date']} and employee_id {item['employee_id']}")
        db.bulk_insert_mappings(Summary, unique_entries)
        db.commit()
        return unique_entries  
    
    except Exception as e:
        db.rollback() 
        raise Exception(f"Failed to insert summary data: {e}")
    
def fetch_summary(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
) -> Dict:
    offset = (page - 1) * page_size

    base_query = db.query(Summary)

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

    total_count = base_query.count()
    limit = ceil(total_count / page_size)

    status_counts = (
        base_query
        .with_entities(Summary.status, func.count(Summary.status))
        .group_by(Summary.status)
        .all()
    )
    status_summary = {status: count for status, count in status_counts}

    paginated_results = (
        base_query.order_by(Summary.date.desc()).offset(offset).limit(page_size).all()
    )

    return {
        "total_records": total_count,
        "page": page,
        "limit": limit,
        "status_summary": status_summary,
        "results": paginated_results,
    }
