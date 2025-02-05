from datetime import datetime, date
from models.attendance import Attendance  
from sqlalchemy.orm import sessionmaker
from zk import ZK
from dotenv import load_dotenv
from db.database import engine
import os


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

def fetch_logs_for_today(conn, db):
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

    if employee_logs:  
        logs_today = batch_insert_update_logs(db, today, employee_logs)
        return logs_today
    else:
        print("No attendance records for today. Skipping database update.")
        return None

def batch_insert_update_logs(db, today, employee_logs):
    inserts = []
    updates = []

    for emp_id, times in employee_logs.items():
        existing_record = db.query(Attendance).filter(Attendance.employee_id == emp_id,
                                                      Attendance.date == today).first()

        if existing_record:
            if times["time-out"]:
                updates.append({"time_out": times["time-out"], "employee_id": emp_id, "date": today})
        else:
            if times["time-in"]:
                inserts.append({
                    "employee_id": emp_id,
                    "date": today,
                    "time_in": times["time-in"],
                    "time_out": times["time-out"],
                    "status": times["status"]
                })
            else:
                print(f"Skipping insert for employee_id {emp_id} on {today} because time_in is missing.")

    if inserts:
        db.bulk_insert_mappings(Attendance, inserts)
    if updates:
        for update in updates:
            existing_record = db.query(Attendance).filter(Attendance.employee_id == update["employee_id"],
                                                          Attendance.date == today).first()
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
    conn = connect_to_device(device_ip, port)
    

   
    test = fetch_logs_for_today(conn, Session)
