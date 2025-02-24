from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func,exists,or_
from models.attendance import Attendance  
from models.attendance_summary import Summary  
from models.vouchers import Vouchers
from datetime import datetime, timedelta
from db.database import engine
#from dateutil.relativedelta import relativedelta
from datetime import date
SessionLocal = sessionmaker(bind=engine)
Session = SessionLocal()

def get_last_week_range():
    today = datetime.today()
    last_week_monday = today - timedelta(days=today.weekday() + 7)
    last_week_saturday = last_week_monday + timedelta(days=5)
    
    return last_week_monday.date(), last_week_saturday.date()
    



def get_perfect_attendance(db, start_date: str, end_date: str, required_days: int = 6):
    result = (
        db.query(Summary.employee_id)
        .filter(Summary.date.between(start_date, end_date))
        .filter(Summary.status == "On time")
        .filter(or_(Summary.checkout_status == "On time", Summary.checkout_status.is_(None)))
        .group_by(Summary.employee_id)
        .having(func.count(Summary.date) == required_days)
        .all()
    )
    
    return [emp[0] for emp in result]
 

def insert_voucher(db, emp_list, last_sat):
    #today = date.today()
    expiry_date = last_sat + timedelta(days=30 + 7)  

    for emp_id in emp_list:
 
        existing_voucher = (
            db.query(Vouchers)
            .filter(
                Vouchers.employee_id == emp_id,
                Vouchers.issue_date >= last_sat  
            )
            .first()
        )

        if existing_voucher:
            print(f"Voucher already exists for Employee ID {emp_id}. Skipping...")
            continue  

        voucher = Vouchers(
            employee_id=emp_id,
            issue_date=last_sat,
            expiry_date=expiry_date,
            date_used=None  
        )
        db.add(voucher)

    db.commit()



if __name__ == "__main__":
    date_from, date_to = get_last_week_range()
    print(date_from, date_to) 
    emp_list = get_perfect_attendance(Session, date_from, date_to)
    print(emp_list)
    if emp_list:
        insert_voucher(Session, emp_list,date_to)
        print(f"Vouchers issued to: {emp_list}")
    else:
        print("No employees qualified for vouchers.")
