from fastapi import HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from models.attendance import Attendance
from models.employees import Employee
from datetime import datetime, date
from sqlalchemy import asc, or_,desc
from zk import ZK
from sqlalchemy.sql import func


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

    batch_insert_update_logs(db, today, employee_logs)


def batch_insert_update_logs(db: Session, today, employee_logs):
    inserts = []
    updates = []

    for emp_id, times in employee_logs.items():
        existing_record = db.query(Attendance).filter(Attendance.employee_id == emp_id,
                                                              Attendance.date == today).first()

        if existing_record:
            if times["time-out"]:
                updates.append({"time_out": times["time-out"], "employee_id": emp_id, "date": today})
        else:
            inserts.append(
                {"employee_id": emp_id, "date": today, "time_in": times["time-in"], "time_out": times["time-out"],
                 "status": times["status"]})

    if inserts:
        db.bulk_insert_mappings(Attendance, inserts)
    if updates:
        for update in updates:
            existing_record = db.query(Attendance).filter(Attendance.employee_id == update["employee_id"],
                                                                  Attendance.date == today).first()
            existing_record.time_out = update["time_out"]
            db.add(existing_record)

    db.commit()
    #conn.clear_attendance()

def check_existing_record(db: Session, user_id, log_date):
    return db.query(Attendance).filter(Attendance.employee_id == user_id,
                                               Attendance.date == log_date).count() > 0

def fetch_attendance(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_filter: str = None,
    status_filter: str = None,
    employee_id_filter: str = None,
):
    offset = (page - 1) * page_size

    # Start the query
    query = db.query(Attendance).order_by(desc(Attendance.date))

    # Apply general search query
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Attendance.date.ilike(search_term),  
                Attendance.status.ilike(search_term), 
                Attendance.employee_id.ilike(search_term),  
            )
        )

    if date_filter:
        query = query.filter(Attendance.date == date_filter)
    if status_filter:
        query = query.filter(Attendance.status.ilike(f"%{status_filter}%"))
    if employee_id_filter:
        query = query.filter(Attendance.employee_id.ilike(f"%{employee_id_filter}%"))

    total_records = query.count()

    
    records = query.offset(offset).limit(page_size).all()

    response = {
        "total_records": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_records + page_size - 1) // page_size,
        "records": records,
    }
    return response


def fetch_attendance_today(db: Session):
    results = (
        db.query(
            Employee.employee_id,
            Employee.name,
            Employee.department,
            Employee.position,
            func.coalesce(Attendance.status, "No info").label("status"),
        )
        .join(
            Attendance,
            (Employee.employee_id == Attendance.employee_id) & 
            (Attendance.date == func.current_date()),
            isouter=True,  
        )
        .order_by(Employee.department.asc())
        .all()
    )
    response = [
        {
            "employee_id": row.employee_id,
            "name": row.name,
            "department": row.department,
            "position": row.position,
            "date": date.today(),
            "status": row.status,
        }
        for row in results
    ]

    return response
