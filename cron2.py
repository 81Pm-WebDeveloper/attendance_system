from datetime import datetime, date, timedelta
from models.attendance import Attendance  
from sqlalchemy.orm import sessionmaker
from zk import ZK
from dotenv import load_dotenv
from db.database import engine
from fastapi import HTTPException
from db.database import get_db
from db.database2 import get_db2
from sqlalchemy.orm import Session
import os
import services.summary_service as summaryService
import services.attendance_service as attendanceService
from sqlalchemy import tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.mysql import insert
# Initialize DB session
import time

import requests
import json

#-----------------------------------------------------------

def timeout_status(time_in, time_out, is_friday=False,is_saturday= False,is_voucher= False):
    
    half_day_threshold = datetime.strptime('13:00:00', '%H:%M:%S').time()
    
    regular_out_time = datetime.strptime('18:00:00', '%H:%M:%S').time()
    
    if is_friday:
        
        if time_in < datetime.strptime('08:00:00', '%H:%M:%S').time():
            regular_out_time = datetime.strptime('17:00:00', '%H:%M:%S').time()
            #print('Friday')
        elif time_in < datetime.strptime('08:30:00', '%H:%M:%S').time():
            regular_out_time = datetime.strptime('17:30:00', '%H:%M:%S').time()
            #print('Condition 2') 
    if is_saturday:
        if is_voucher:
            regular_out_time = datetime.strptime('15:00:00', '%H:%M:%S').time()
            
        else:
            regular_out_time = datetime.strptime('17:00:00', '%H:%M:%S').time()
            
        #print('Saturday')

      
    if time_out <= half_day_threshold:
        undertime_min = (datetime.combine(datetime.min, regular_out_time) - datetime.combine(datetime.min, time_out)).seconds // 60
        undertime_min = max(0, undertime_min -60)
        return (undertime_min, "Undertime")

    elif time_out < regular_out_time:
        undertime_min = (datetime.combine(datetime.min, regular_out_time) - datetime.combine(datetime.min, time_out)).seconds // 60
        undertime_min = max(0, undertime_min)
        return (undertime_min, "Undertime")

    elif time_out >= regular_out_time:
        return (None, "On time")

    else:
        return (None, "WTF EDGE CASE")
#-----------------------------------------------------------

def time_status(time_in):
    late_threshold = datetime.strptime('09:01:00', '%H:%M:%S').time()  
    half_day_threshold = datetime.strptime('11:00:00', '%H:%M:%S').time()  
    half_day_base_time = datetime.strptime('13:00:00', '%H:%M:%S').time() 
    base_time = datetime.strptime('09:00:00', '%H:%M:%S').time()  

    if time_in >= half_day_threshold:  
        late_min = (datetime.combine(datetime.min, time_in) - datetime.combine(datetime.min, half_day_base_time)).seconds // 60
        return (late_min, "Half Day") if time_in > half_day_base_time else (None, "Half Day")

    elif time_in >= late_threshold: 
        late_min = (datetime.combine(datetime.min, time_in) - datetime.combine(datetime.min, base_time)).seconds // 60
        return (late_min, "Late")

    else:
        return "On time"
#-----------------------------------------------------------

def fetch_logs_for_past_days(conn, db, days):
    today = date.today()
    start_date = today if days == 0 else today - timedelta(days=days)  # Fix for days=0

    logs = conn.get_attendance()
    if not logs:
        print(f"No attendance records found.")
        return None

    employee_logs = {}
    
    for log in logs:
        log_date = log.timestamp.date()
        if not (start_date <= log_date <= today):
            continue

        user_id = log.user_id
        timestamp = log.timestamp.strftime("%H:%M:%S")
        punch = "time-in" if log.punch == 0 else "time-out"

        if user_id not in employee_logs:
            employee_logs[user_id] = {}

        if log_date not in employee_logs[user_id]:
            employee_logs[user_id][log_date] = {
                "time-in": None, 
                "time-out": None, 
                "status": None,
                "checkout_status": "No info",
                "late_min": None,
                "undertime_min": None,
            }
        
        if punch == "time-in" and employee_logs[user_id][log_date]["time-in"] is None:
            time_in = datetime.strptime(timestamp, "%H:%M:%S").time()
            employee_logs[user_id][log_date]["time-in"] = timestamp
            result = time_status(time_in)

            if isinstance(result, tuple):
                employee_logs[user_id][log_date]["late_min"], employee_logs[user_id][log_date]["status"] = result
            else:
                employee_logs[user_id][log_date]["status"] = result

        elif punch == "time-out":
            time_in_str = employee_logs[user_id][log_date].get("time-in")

            # Ignore time-out if time-in doesn't exist yet
            if not time_in_str:
                print(f"Skipping time-out for {user_id} on {log_date} - No time-in found.")
                continue

            employee_logs[user_id][log_date]["time-out"] = timestamp
            time_in = datetime.strptime(time_in_str, "%H:%M:%S").time()
            time_out = datetime.strptime(timestamp, "%H:%M:%S").time()

            is_friday = log_date.strftime("%A") == "Friday"
            is_saturday = log_date.strftime("%A") == "Saturday"

            # voucher = db.query(Attendance.voucher_id).filter(
            #     Attendance.employee_id == user_id,
            #     Attendance.date == log_date
            # ).first()

            #is_voucher = bool(voucher and voucher[0])
            is_voucher = True
            result = timeout_status(time_in, time_out, is_friday, is_saturday, is_voucher)

            if isinstance(result, tuple):
                employee_logs[user_id][log_date]["undertime_min"], employee_logs[user_id][log_date]["checkout_status"] = result
            elif result:
                employee_logs[user_id][log_date]["checkout_status"] = result
    dataBody = prepare_employee_logs(employee_logs)
    #print(employee_logs)
    try:
        conn.enable_device()
    finally:
        conn.disconnect()

    if employee_logs:
        insert_attendance(dataBody)
        return 

    print(f"No attendance records for the past {days} days. Skipping database update.")
    return None


#--------------------------------------------------------------
def prepare_employee_logs(employee_logs):
    formatted_logs = {
        emp_id: {
            log_date.strftime("%Y-%m-%d"): log_data  # Convert date to string
            for log_date, log_data in dates.items()
        }
        for emp_id, dates in employee_logs.items()
    }
    return formatted_logs
#-----------------------------------------------------------
import requests
import json

def insert_attendance(data):
    url = "http://127.0.0.1:8080/attendance/"
    headers = {
        "Content-Type": "application/json",
        "API-KEY": os.getenv('api_key')
        }
    
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        return response.json()  # Return the parsed JSON response
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


#-----------------------------------------------------------

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
#-----------------------------------------------------------

def connect_to_device(ip, port=4370):
    zk = ZK(ip, port=port, timeout=5)
    try:
        conn = zk.connect()
        conn.disable_device()
        return conn
    except Exception as e:
        raise Exception(f"Unable to connect to device: {e}")
#-----------------------------------------------------------


if __name__ == "__main__":
    load_dotenv()
    device_ip = os.getenv("device_ip")
    port = int(os.getenv("device_port", 4370))
    start_time = time.time()
    days = 4
    today = date.today()
    start_date = today - timedelta(days=days)
    db = next(get_db())
    db2 = next(get_db2())
    try:
        conn = connect_to_device(device_ip, port)
        fetch_logs_for_past_days(conn, db, days)
        #insert_summary(db,db2,start_date = start_date, end_date=today)
        #insert_summary_today(db,db2,start_date=today,end_date=today)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        db2.close()
    end_time = time.time()

    total_time = end_time - start_time
    print(f"Total execution time: {total_time} seconds")