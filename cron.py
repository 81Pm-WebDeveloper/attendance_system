from datetime import datetime, date, timedelta
from models.attendance import Attendance  
from sqlalchemy.orm import sessionmaker
from zk import ZK
from dotenv import load_dotenv
from db.database import engine
import os

# SCHEDULED TASK
SessionLocal = sessionmaker(bind=engine)
Session = SessionLocal()

def time_status(time_in):
    late_threshold = datetime.strptime('09:01:00', '%H:%M:%S').time()
    half_day_threshold = datetime.strptime('11:00:00', '%H:%M:%S').time()

    if time_in >= half_day_threshold:
        return "Half Day"
    elif time_in >= late_threshold:
        return "Late"
    else:
        return "Present"

def fetch_logs_for_past_days(conn, db, days=7):
    today = date.today()
    start_date = today - timedelta(days=days)

    logs = conn.get_attendance()
    employee_logs = {}

    for log in logs:
        log_date = log.timestamp.date()

        if start_date <= log_date <= today:  # Check if within range
            user_id = log.user_id
            timestamp = str(log.timestamp).split(' ')[1]
            punch = "time-in" if log.punch == 0 else "time-out"

            if user_id not in employee_logs:
                employee_logs[user_id] = {}

            if log_date not in employee_logs[user_id]:
                employee_logs[user_id][log_date] = {"time-in": None, "time-out": None, "status": "Present"}

            if punch == "time-in" and employee_logs[user_id][log_date]["time-in"] is None:
                time_in = datetime.strptime(timestamp, '%H:%M:%S').time()
                employee_logs[user_id][log_date]["time-in"] = timestamp
                employee_logs[user_id][log_date]["status"] = time_status(time_in)
            elif punch == "time-out":
                employee_logs[user_id][log_date]["time-out"] = timestamp
    conn.enable_device()
    conn.disconnect()
    if employee_logs:
        logs_inserted = batch_insert_update_logs(db, employee_logs)
        return logs_inserted
    else:
        print(f"No attendance records for the past {days} days. Skipping database update.")
        return None

def batch_insert_update_logs(db, employee_logs):
    inserts = []
    updates = []

    for emp_id, dates in employee_logs.items():
        for log_date, times in dates.items():
            existing_record = db.query(Attendance).filter(Attendance.employee_id == emp_id,
                                                          Attendance.date == log_date).first()

            if existing_record:
                if times["time-out"]:
                    updates.append({"time_out": times["time-out"], "employee_id": emp_id, "date": log_date})
            else:
                if times["time-in"]:
                    inserts.append({
                        "employee_id": emp_id,
                        "date": log_date,
                        "time_in": times["time-in"],
                        "time_out": times["time-out"],
                        "status": times["status"]
                    })
                else:
                    print(f"Skipping insert for employee_id {emp_id} on {log_date} because time_in is missing.")

    if inserts:
        db.bulk_insert_mappings(Attendance, inserts)
    if updates:
        for update in updates:
            existing_record = db.query(Attendance).filter(Attendance.employee_id == update["employee_id"],
                                                          Attendance.date == update["date"]).first()
            existing_record.time_out = update["time_out"]
            db.add(existing_record)

    db.commit()
    return inserts, updates

def connect_to_device(ip, port=4370):
    zk = ZK(ip, port=port, timeout=5)
    try:
        conn = zk.connect()
        conn.disable_device()
        return conn
    except Exception as e:
        raise Exception(f"Unable to connect to device: {e}")

if __name__ == "__main__":
    load_dotenv()

    device_ip = os.getenv("device_ip")
    port = int(os.getenv("device_port", 4370))

    try:
        conn = connect_to_device(device_ip, port)
        fetch_logs_for_past_days(conn, Session, days=7)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        Session.close()
        
