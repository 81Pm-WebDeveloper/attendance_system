from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance import Attendance
from models.emp_list import Employee2
from datetime import datetime, date
from sqlalchemy import or_,desc,and_,tuple_
from zk import ZK
from sqlalchemy.sql import func
from math import ceil
from sqlalchemy.dialects.mysql import insert
from datetime import timedelta

load_dotenv()

def connect_to_device(ip, port=4370):
    zk = ZK(ip, port=port, timeout=5)
    try:
        conn = zk.connect()
        conn.disable_device()
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to connect to device: {e}")

def time_status(time_in):
    late_threshold = datetime.strptime('09:01:00', '%H:%M:%S').time()
    half_day_threshold = datetime.strptime('11:00:00', '%H:%M:%S').time()

    if time_in >= half_day_threshold:
        return "Half Day"
    elif time_in >= late_threshold:
        return "Late"
    else:
        return "Present"


def fetch_logs_for_today(conn, db: Session):
    today = date.today()
    logs = conn.get_attendance()
    employee_logs = {}

    for log in logs:
        log_date = log.timestamp.date()
        date_now = datetime.now().date()

        if log_date == date_now:
            user_id = log.user_id
            timestamp = str(log.timestamp).split(' ')[1]
            punch = "time-in" if log.punch == 0 else "time-out"

            if user_id not in employee_logs:
                employee_logs[user_id] = {"time-in": None, "time-out": None, "status": "Present"}

            if punch == "time-in" and employee_logs[user_id]["time-in"] is None:
                time_in = datetime.strptime(timestamp, '%H:%M:%S').time()
                employee_logs[user_id]["time-in"] = timestamp
                employee_logs[user_id]["status"] = time_status(time_in)
            elif punch == "time-out":
                employee_logs[user_id]["time-out"] = timestamp

    logs_today = batch_insert_update_logs(db, today, employee_logs)
    return logs_today


## NEW
def batch_insert_update_logs(db:Session, employee_logs):
    emp_date_pairs = [(emp_id, date) for emp_id, dates in employee_logs.items() 
                      for date in dates.keys()]
    
    existing_records = {
        (record.employee_id, record.date): record
        for record in db.query(Attendance).filter(
            tuple_(Attendance.employee_id, Attendance.date).in_(emp_date_pairs)
        )
    }
    
    inserts = []
    updates = []
    
    for emp_id, dates in employee_logs.items():
        for log_date, times in dates.items():
            existing_record = existing_records.get((emp_id, log_date))
            
            if existing_record:
                if times["time-out"]:
                    existing_record.time_out = times["time-out"]
                    existing_record.checkout_status = times["checkout_status"]
                    existing_record.undertime_min = times["undertime_min"]
                    updates.append(existing_record)
            else:
                if times["time-in"]:
                    inserts.append({
                        'employee_id': emp_id,
                        'date': log_date,
                        'time_in': times["time-in"],
                        'time_out': times["time-out"],
                        'status': times["status"],
                        'checkout_status': times["checkout_status"],
                        'late_min': times.get("late_min", 0),
                        'undertime_min': times.get("undertime_min", 0)
                    })
                else:
                    print(f"Skipping insert for employee_id {emp_id} on {log_date} because time_in is missing.")
    
    try:
        if inserts:
            for batch in chunks(inserts, 1000): 
                stmt = insert(Attendance).values(batch)
                update_dict = {
                    'time_out': stmt.inserted.time_out,
                    'checkout_status': stmt.inserted.checkout_status,
                    'undertime_min': stmt.inserted.undertime_min
                }
                stmt = stmt.on_duplicate_key_update(**update_dict)
                db.execute(stmt)
        
        if updates:
            db.bulk_update_mappings(Attendance, [
                {
                    'id': record.id,
                    'time_out': record.time_out,
                    'checkout_status': record.checkout_status,
                    'undertime_min': record.undertime_min
                }
                for record in updates
            ])
            
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise
    
    return len(inserts), len(updates)
#-----------------------------------------------------------

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
#-----------------------------------------------------------



def check_existing_record(db: Session, user_id, log_date):
    return db.query(Attendance).filter(Attendance.employee_id == user_id,
                                               Attendance.date == log_date).count() > 0



def fetch_attendance(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    status_filter: str = None,
    employee_id_filter: str = None,
):
    query = db.query(Attendance).order_by(desc(Attendance.date))

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Attendance.date.ilike(search_term),
                Attendance.status.ilike(search_term),
                Attendance.employee_id.ilike(search_term),
            )
        )

    if date_from and date_to:
        query = query.filter(Attendance.date.between(date_from, date_to))
    elif date_from:
        query = query.filter(Attendance.date >= date_from)
    elif date_to:
        query = query.filter(Attendance.date <= date_to)

    if status_filter:
        query = query.filter(Attendance.status.ilike(f"%{status_filter}%"))
    if employee_id_filter:
        query = query.filter(Attendance.employee_id.ilike(f"%{employee_id_filter}%"))

    total_records = query.count()

    if page is None or page_size is None or page == 0 or page_size == 0:
        records = query.all()

        response = {
            "total_records": total_records,
            "page": 1,
            "limit": total_records,
            "total_pages": 1,
            "records": records,
        }
    else:
        offset = (page - 1) * page_size
        limit = ceil(total_records / page_size)

        records = query.offset(offset).limit(page_size).all()

        response = {
            "total_records": total_records,
            "page": page,
            "limit": limit,
            "total_pages": (total_records + page_size - 1) // page_size,
            "records": records,
        }

    return response

def fetch_attendance_today(db: Session):
    results = (
        db.query(
            Employee2.empID, #empID
            Employee2.fullname, #fullname
            Employee2.company, #Company 
            Employee2.position, #position 
            Employee2.branch, #branch
            func.coalesce(Attendance.status, "No info").label("status"),
            Attendance.time_in,
            Attendance.time_out
        )
        .join(
            Attendance,
            (Employee2.empID == Attendance.employee_id) & 
            (Attendance.date == date.today()),
            isouter=True, # OUTERRRR JOINNNNNNNNNNN
        )
        .order_by(Employee2.department.asc())
        .all()
    )
    response = [
        {
            "employee_id": row.empID,
            "name": row.fullname,
            "department": row.company,
            "position": row.position,
            "date": date.today(),
            "time_in": row.time_in,
            "time_out": row.time_out,
            "status": row.status,
        }
        for row in results
    ]

    return response




# def fetch_attendance_between_dates(db1: Session, db2: Session, start_date: date, end_date: date):
#     today = date.today().strftime('%a').upper()

#     employees = db2.query(
#         Employee2.empID,
#         Employee2.fullname,
#         Employee2.company,
#         Employee2.position,
#         Employee2.status,
#         Employee2.work_sched
#     ).filter(
#         Employee2.status == "Active",
#         func.find_in_set(today, Employee2.work_sched) > 0  
#     ).all()

   
#     attendance_data = db1.query(
#         Attendance.employee_id,
#         Attendance.date,
#         Attendance.time_in,
#         Attendance.time_out,
#         Attendance.status
#     ).filter(Attendance.date.between(start_date, end_date)).all()

    
#     result = []
#     for employee in employees:
#         employee_attendance = [
#             att for att in attendance_data if att.employee_id == employee.empID
#         ]
#         for att in employee_attendance:
#             result.append({
#                 "employee_id": employee.empID,
#                 "name": employee.fullname,
#                 "department": employee.company,
#                 "position": employee.position,
#                 "date": att.date,
#                 "time_in": att.time_in,
#                 "time_out": att.time_out,
#                 "status": att.status if att.status else "No info",
#             })

#     return result

# Linear
def fetch_attendance_between_dates(db1: Session, db2: Session, start_date: date, end_date: date):
   
    today = date.today().strftime('%a').upper()

    excluded_positions = {'System Admin', 'SystemTester','Admin','CEO','Manager','HRdev','WebDev'}

    employees = db2.query(
        Employee2.empID,
        Employee2.work_sched
    ).filter(
        Employee2.status == "Active",
        Employee2.department != 'MANAGEMENT',
        ~Employee2.position.in_(excluded_positions),  
        func.find_in_set(today, Employee2.work_sched) > 0  
    ).all()

    attendance_data = db1.query(
        Attendance.id,
        Attendance.employee_id,        
        Attendance.date,
        Attendance.time_in,
        Attendance.time_out,
        Attendance.status,
        Attendance.checkout_status
    ).filter(Attendance.date.between(start_date, end_date)).all()


    attendance_dict = {emp.empID: [] for emp in employees}

    for att in attendance_data:
        if att.employee_id in attendance_dict:
            attendance_dict[att.employee_id].append(att)

    result = []
    for employee in employees:
        if attendance_dict[employee.empID]: # DICTIONARY o(1) look up
            for att in attendance_dict[employee.empID]:
                result.append({
                    "employee_id": employee.empID,
                    "att_id": att.id,
                    "date": att.date,
                    "time_in": att.time_in,
                    "time_out": att.time_out,
                    "status": att.status,
                    "checkout_status": att.checkout_status,
                })
        else:
            result.append({
                "employee_id": employee.empID,
                "att_id": None,
                "date": None,
                "time_in": None,
                "time_out": None,
                "status": None,
                "checkout_status": None,
            })

    return result

#OPTION 2 - slower - works better even without daily trigger
# def fetch_attendance_cron(db1: Session, db2: Session, start_date: date, end_date: date):
#     excluded_positions = {'System Admin', 'SystemTester', 'Admin', 'CEO', 'Manager'}
#     result = []

#     current_date = start_date
#     while current_date <= end_date:
#         day_of_week = current_date.strftime('%a').upper()

#         employees = db2.query(
#             Employee2.empID,
#             Employee2.work_sched
#         ).filter(
#             Employee2.status == "Active",
#             Employee2.department != 'MANAGEMENT',
#             ~Employee2.position.in_(excluded_positions),
#             func.find_in_set(day_of_week, Employee2.work_sched) > 0  
#         ).all()

#         for employee in employees:
#             # Fetch attendance for this employee on this specific date
#             attendance = db1.query(
#                 Attendance.id,
#                 Attendance.employee_id,
#                 Attendance.date,
#                 Attendance.time_in,
#                 Attendance.time_out,
#                 Attendance.status,
#                 Attendance.checkout_status
#             ).filter(
#                 Attendance.date == current_date,
#                 Attendance.employee_id == employee.empID
#             ).first()

#             if attendance:  # Employee has an attendance record
#                 result.append({
#                     "employee_id": employee.empID,
#                     "att_id": attendance.id,
#                     "date": attendance.date,
#                     "time_in": attendance.time_in,
#                     "time_out": attendance.time_out,
#                     "status": attendance.status,
#                     "checkout_status": attendance.checkout_status,
#                 })

#         current_date += timedelta(days=1)

#     return result

#faster - enough if (daily trigger)
def fetch_attendance_cron(db1: Session, db2: Session, start_date: date, end_date: date):
    today = date.today().strftime('%a').upper()

    excluded_positions = {'System Admin', 'SystemTester', 'Admin', 'CEO', 'Manager','WebDev'}

    employees = db2.query(
        Employee2.empID,
        Employee2.work_sched
    ).filter(
        Employee2.status == "Active",
        Employee2.department != 'MANAGEMENT',
        ~Employee2.position.in_(excluded_positions),  
        #func.find_in_set(today, Employee2.work_sched) > 0  
    ).all()

    # Get only existing attendance records
    attendance_data = db1.query(
        Attendance.id,
        Attendance.employee_id,        
        Attendance.date,
        Attendance.time_in,
        Attendance.time_out,
        Attendance.status,
        Attendance.checkout_status
    ).filter(Attendance.date.between(start_date, end_date)).all()

    attendance_dict = {}
    for att in attendance_data:
        if att.employee_id not in attendance_dict:
            attendance_dict[att.employee_id] = []
        attendance_dict[att.employee_id].append(att)

    result = []
    for employee in employees:
        if employee.empID in attendance_dict:  # Employee has existing attendance
            for att in attendance_dict[employee.empID]:
                result.append({
                    "employee_id": employee.empID,
                    "att_id": att.id,
                    "date": att.date,
                    "time_in": att.time_in,
                    "time_out": att.time_out,
                    "status": att.status,
                    "checkout_status": att.checkout_status,
                })

    return result