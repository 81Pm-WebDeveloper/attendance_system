from fastapi import HTTPException
#from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance import Attendance
from models.employees import Employee
from models.attendance_summary import Summary
from datetime import datetime, date
from sqlalchemy import asc, or_,desc

from sqlalchemy.sql import func

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
    

