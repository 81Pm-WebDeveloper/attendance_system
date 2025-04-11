from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func,exists,or_,and_
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
    last_week_monday = today - timedelta(days=today.weekday() + 7) #0-6 => mon - sun
    last_week_saturday = last_week_monday + timedelta(days=5)
    
    return last_week_monday.date(), last_week_saturday.date()
    

def check_holiday(db, monday, saturday):
    all_dates = set(monday + timedelta(days=i) for i in range(6)) #OR sat - mon + 1 

    recorded_dates = set(
        record.date for record in db.query(Attendance.date)
        .filter(Attendance.date.between(monday, saturday))
        .distinct()
    )

    missing_dates = all_dates - recorded_dates
    print(missing_dates)
    return 5 if len(missing_dates) == 1 else 6



def get_perfect_attendance(db, start_date: str, end_date: str, required_days):
    if required_days < 5:
        print('Working holiday > 1')
        return []

    result = (
        db.query(Summary.employee_id)
        .filter(Summary.date.between(start_date, end_date))
        .filter(
            and_(
                Summary.status.in_(["On time", "Official Business", "PARSO"]),
                or_(
                    Summary.checkout_status == "On time",
                    Summary.checkout_status == '',
                    Summary.checkout_status.is_(None),
                    and_(
                        Summary.status == "Official Business",
                        Summary.checkout_status == "No info"
                    )
                )
            )
        )
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
                Vouchers.issue_date == last_sat  
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
    required_days = check_holiday(Session,date_from,date_to)

    emp_list = get_perfect_attendance(Session, date_from, date_to,required_days)

    if emp_list:
        try:
            insert_voucher(Session, emp_list,date_to)
            print(f"Vouchers issued to: {emp_list}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            Session.close()
    else:
        print("No employees qualified for vouchers.")
