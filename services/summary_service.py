from fastapi import HTTPException
#from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance_summary import Summary
from datetime import datetime, date
from sqlalchemy import asc, or_,desc,func
from schemas.summary import UpdateSummary
from typing import Dict, List
from math import ceil
from models.emp_list import Employee2
from collections import defaultdict


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
                if existing_entry.status == 'No info': 
                    existing_entry.status = item.get('status', existing_entry.status)
                    db.add(existing_entry)
                if existing_entry.time_in is None and item.get('time_in'):
                    existing_entry.time_in = item['time_in']
                    db.add(existing_entry)
                if item.get('time_out'):
                    if existing_entry.time_out is None or item['time_out'] > existing_entry.time_out:
                        existing_entry.time_out = item['time_out']
                        db.add(existing_entry)
            
            else:
                if emp_date not in unique_employee_dates:  
                    unique_entries.append(item)
                    unique_employee_dates.add(emp_date)
                else:                        
                    print(f"Duplicate employee_id found for Date {item['date']} and employee_id {item['employee_id']}")
        
        if unique_entries:
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
    if page_size:
        offset = (page - 1) * page_size
    else:
        offset = 0  

    base_query = db.query(
        Summary,
        Employee2.fullname.label("employee_name"),  
        Employee2.position.label("employee_position"), 
        Employee2.company.label("employee_department"),  #CHANGEEEEEEEEEEEEEEEEEEEEEEEEEEE
    ).join(Employee2, Summary.employee_id == Employee2.empID)

    if search_query:
        search_term = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Summary.employee_id.like(search_term),
                Summary.status.like(search_term),
                Employee2.fullname.like(search_term), 
                Employee2.position.like(search_term),
                Employee2.company.like(search_term)  
            )
        )

    if date_from:
        base_query = base_query.filter(Summary.date >= date_from)
    if date_to:
        base_query = base_query.filter(Summary.date <= date_to)

    if employee_id_filter:
        base_query = base_query.filter(Summary.employee_id == employee_id_filter)

    total_count = base_query.count()

    status_counts = (
        base_query
        .with_entities(Summary.status, func.count(Summary.status))
        .group_by(Summary.status)
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

    return {
        "total_records": total_count,
        "page": page if page_size else 1,  
        "limit": limit,
        "status_summary": status_summary,
        "results": [
            {
                **summary.__dict__,  
                "employee_name": employee_name,
                "employee_position": employee_position,
                "department": employee_department,
            }
            for summary, employee_name, employee_position, employee_department in result
        ],
    }


def fetch_count(
    db: Session,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
) -> Dict:
    base_query = db.query(
        Summary,
        Employee2.fullname.label("employee_name"),  
        Employee2.position.label("employee_position"), 
        Employee2.company.label("employee_department"),
    ).join(Employee2, Summary.employee_id == Employee2.empID)

    if search_query:
        search_term = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Summary.employee_id.like(search_term),
                Summary.status.like(search_term),
                Employee2.fullname.like(search_term), 
                Employee2.position.like(search_term),
                Employee2.company.like(search_term)  
            )
        )

    if date_from:
        base_query = base_query.filter(Summary.date >= date_from)
    if date_to:
        base_query = base_query.filter(Summary.date <= date_to)

    if employee_id_filter:
        base_query = base_query.filter(Summary.employee_id == employee_id_filter)

    result = base_query.order_by(Summary.date.desc()).all()

    employee_summary = defaultdict(lambda: {
        "employee_name": None,
        "employee_position": None,
        "employee_department": None,
        "status_counts": defaultdict(int)
    })

    for summary, employee_name, employee_position, employee_department in result:
        employee_key = summary.employee_id

        employee_summary[employee_key]["employee_name"] = employee_name
        employee_summary[employee_key]["employee_position"] = employee_position
        employee_summary[employee_key]["employee_department"] = employee_department
        employee_summary[employee_key]["status_counts"][summary.status] += 1

    final_results = [
        {
            "employee_name": data["employee_name"],
            "employee_position": data["employee_position"],
            "employee_department": data["employee_department"],
            "status_counts": dict(data["status_counts"]),
        }
        for data in employee_summary.values()
    ]

    status_counts = (
        base_query
        .with_entities(Summary.status, func.count(Summary.status))
        .group_by(Summary.status)
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
        updated_summaries.append(summary)

    if not updated_summaries:
        raise HTTPException(status_code=400, detail="No records to update")

    db.bulk_save_objects(updated_summaries)
    db.commit()

    for summary in updated_summaries:
        db.refresh(summary)

    return {"updated": [summary.id for summary in updated_summaries], "failed": failed_updates}