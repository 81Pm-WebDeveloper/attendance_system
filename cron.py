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

#-----------------------------------------------------------

def timeout_status(time_in, time_out, is_friday=False,is_saturday= False,is_voucher= False):
    
    half_day_threshold = datetime.strptime('13:10:00', '%H:%M:%S').time()
    
    regular_out_time = datetime.strptime('18:00:00', '%H:%M:%S').time()
    
    if is_friday:
        
        if time_in < datetime.strptime('08:01:00', '%H:%M:%S').time():
            half_day_threshold = datetime.strptime('12:10:00','%H:%M:%S').time()
            regular_out_time = datetime.strptime('17:00:00', '%H:%M:%S').time()
            #print('Friday')
        elif time_in < datetime.strptime('08:31:00', '%H:%M:%S').time():
            half_day_threshold = datetime.strptime('12:40:00','%H:%M:%S').time()
            regular_out_time = datetime.strptime('17:30:00', '%H:%M:%S').time()
            #print('Condition 2') 
    if is_saturday:
        if is_voucher:
            regular_out_time = datetime.strptime('15:00:00', '%H:%M:%S').time()
            
        else:
            regular_out_time = datetime.strptime('15:00:00', '%H:%M:%S').time()
            
        #print('Saturday')

      
    if time_out <= half_day_threshold:
        return (None, "Half Day")

    elif time_out < regular_out_time:
        undertime_min = (datetime.combine(datetime.min, regular_out_time) - datetime.combine(datetime.min, time_out)).seconds // 60
        undertime_min = max(0, undertime_min)
        return (undertime_min, "Undertime")

    elif time_out >= regular_out_time:
        #print(f"{time_out} - {regular_out_time}")
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
        if time_in <= half_day_base_time:
            return (None, "Half Day")
        
        late_min = (datetime.combine(datetime.min, time_in) - datetime.combine(datetime.min, half_day_base_time)).seconds // 60
        return (late_min, "Half Day")

    elif time_in >= late_threshold: 
        late_min = (datetime.combine(datetime.min, time_in) - datetime.combine(datetime.min, base_time)).seconds // 60
        return (late_min, "Late")

    else:
        return (None,"On time")
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
                "checkout_status": None,
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

            voucher = db.query(Attendance.voucher_id).filter(
                Attendance.employee_id == user_id,
                Attendance.date == log_date
            ).first()

            is_voucher = bool(voucher and voucher[0])
            
            result = timeout_status(time_in, time_out, is_friday, is_saturday, is_voucher)

            if isinstance(result, tuple):
                employee_logs[user_id][log_date]["undertime_min"], employee_logs[user_id][log_date]["checkout_status"] = result
            elif result:
                employee_logs[user_id][log_date]["checkout_status"] = result

    #print(employee_logs)
    try:
        conn.enable_device()
    finally:
        conn.disconnect()

    if employee_logs:
        return batch_insert_update_logs(db, employee_logs)

    print(f"No attendance records for the past {days} days. Skipping database update.")
    return None

#-----------------------------------------------------------

def batch_insert_update_logs(db, employee_logs):
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

def connect_to_device(ip, port=4370):
    zk = ZK(ip, port=port, timeout=5)
    try:
        conn = zk.connect()
        conn.disable_device()
        return conn
    except Exception as e:
        raise Exception(f"Unable to connect to device: {e}")
#-----------------------------------------------------------

def insert_summary(
    db: Session ,
    db2: Session,
    start_date = str,
    end_date = str 
    ):
    try:
        response = attendanceService.fetch_attendance_cron(db,db2,start_date,end_date) #first loop
        data = [
            {
                "employee_id": row["employee_id"],
                "att_id": row["att_id"],
                "date": row["date"],
                "time_in":row["time_in"],
                "time_out":row["time_out"],
                "status": row["status"],
                "checkout_status": row["checkout_status"],
            }
            for row in response #loop 2
        ]
        
        entries = summaryService.insert_summary(db, data)

        return {"detail": f"Summary logs inserted"}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


"""def insert_summary_today(
    db: Session ,
    db2: Session,
    start_date = str,
    end_date = str 
    ):
    try:
        response = attendanceService.fetch_attendance_between_dates(db,db2,start_date,end_date)
        data = [
            {
                "employee_id": row["employee_id"],
                "att_id": row["att_id"],
                "date": row["date"],
                "time_in":row["time_in"],
                "time_out":row["time_out"],
                "status": row["status"],
                "checkout_status": row["checkout_status"],
            }
            for row in response 
        ]
        
        entries = summaryService.insert_summary(db, data)

        return {"detail": f"Summary logs inserted"}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
"""
if __name__ == "__main__":
    load_dotenv()
    device_ip = os.getenv("device_ip")
    port = int(os.getenv("device_port", 4370))
    start_time = time.time()
    days = 3
    today = date.today()
    start_date = today - timedelta(days=days)
    db = next(get_db())
    db2 = next(get_db2())
    try:
        conn = connect_to_device(device_ip, port)
        fetch_logs_for_past_days(conn, db, days)
        insert_summary(db,db2,start_date = start_date, end_date=today)
        #insert_summary_today(db,db2,start_date=today,end_date=today)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        db2.close()
    end_time = time.time()

    total_time = end_time - start_time
    print(f"Total execution time: {total_time} seconds")