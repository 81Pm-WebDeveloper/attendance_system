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

            
            att_id_exists = db.query(Summary).filter(Summary.att_id == item['att_id']).first()

                
            existing_entry = db.query(Summary).filter(
                Summary.employee_id == item['employee_id'], 
                Summary.date == item['date']
            ).first()

            if existing_entry:
                existing_entry.att_id = item['att_id']  
                
                if item.get('status') == 'On time':
                    existing_entry.status = 'On time'

                if existing_entry.time_in is None and item.get('time_in'):
                    existing_entry.time_in = item['time_in']

                if item.get('time_out'):
                    if not existing_entry.time_out or item['time_out'] > existing_entry.time_out:
                        existing_entry.time_out = item['time_out']

                if item.get('checkout_status'):
                    existing_entry.checkout_status = item['checkout_status']

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



#DONE
def fetch_summary(
    db1: Session,
    db2: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,  #Change to single date
    employee_id_filter: str = None,
) -> Dict:

    if page_size:
        offset = (page - 1) * page_size
    else:
        offset = 0  

    base_query = db1.query(Summary)

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


    employee_data = (
        db2.query(
            Employee2.empID,
            Employee2.fullname,
            Employee2.position,
            Employee2.department,
            Employee2.company,
            Employee2.branch,
        )
        .filter(Employee2.empID.in_([summary.employee_id for summary in result]))
        .order_by(Employee2.department) 
        .all()
    )

    employee_map = {employee.empID: employee for employee in employee_data}
                    #KEY            #VALUE
   
    sorted_result = sorted(
        result, 
        key=lambda summary: employee_map.get(summary.employee_id).department if employee_map.get(summary.employee_id) else ""
    )

    return {
        "total_records": total_count,
        "page": page if page_size else 1,  
        "limit": limit,
        "status_summary": status_summary,
        "results": [
            {
                **summary.__dict__, #EXTRACTS THE VALUE OF sorted_result -------------------------------------
                "employee_department": employee_map.get(summary.employee_id).department,
                "employee_name": employee_map.get(summary.employee_id).fullname,
                "employee_position": employee_map.get(summary.employee_id).position,
                "company": f"{employee_map.get(summary.employee_id).company} ({employee_map.get(summary.employee_id).branch})"
            }
            for summary in sorted_result  
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
            employee_summary[employee_key]["employee_name"] = employee.employee_name
            employee_summary[employee_key]["employee_department"] = employee.employee_department
            employee_summary[employee_key]["employee_position"] = employee.employee_position
            employee_summary[employee_key]["employee_company"] = employee.employee_company
            employee_summary[employee_key]["employee_branch"] = employee.employee_branch
            employee_summary[employee_key]["status_counts"][summary.status] += 1

    final_results = [
        {
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
