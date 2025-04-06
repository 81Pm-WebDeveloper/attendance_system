from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.vouchers import Vouchers
from models.attendance import Attendance
from models.emp_list import Employee2
from datetime import date,datetime,timedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_,desc,and_,tuple_
from schemas.voucher import InsertVoucher

voucher_day = 5

def insert_voucher(db:Session,voucher:InsertVoucher):
    issue_date = datetime.strptime(voucher.issue_date, "%Y-%m-%d") 
    expiry_date = issue_date + timedelta(days=37)
    if issue_date.weekday() != voucher_day:
        raise HTTPException(status_code=400, detail="Vouchers can only be issued on saturdays")
      
    existing_voucher = (
            db.query(Vouchers)
            .filter(
                Vouchers.employee_id == voucher.employee_id,
                Vouchers.issue_date == issue_date  
            )
            .first()
        )
    if existing_voucher:
        raise HTTPException(status_code=400, detail="Voucher already exist")
    
    new_voucher = Vouchers(
        **voucher.model_dump(),
        expiry_date=expiry_date
    )

    db.add(new_voucher)
    db.commit()
    db.refresh(new_voucher)

    return new_voucher
#VOUCHER DISPLAY FOR HR
def fetch_all_vouchers(
    db: Session,
    db2: Session,
    page: int = 1,
    page_size: int = 10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
    used_filter: str = 'unused'
):
    
    query = db.query(Vouchers).order_by(desc(Vouchers.expiry_date))

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(Vouchers.employee_id.ilike(search_term))

    if date_from and date_to:
        query = query.filter(Vouchers.issue_date.between(date_from, date_to))

    if employee_id_filter:
        query = query.filter(Vouchers.employee_id.ilike(f"%{employee_id_filter}%"))

    if used_filter:
        if used_filter == "used":
            query = query.filter(Vouchers.date_used.isnot(None))
        elif used_filter == "unused":
            query = query.filter(Vouchers.date_used.is_(None))

    total_count = query.count()

    if page and page_size:
        query = query.offset((page - 1) * page_size).limit(page_size)

    vouchers = query.all()

    
    emp_ids = {v.employee_id for v in vouchers}  
    emp_query = db2.query(Employee2.empID, Employee2.fullname).filter(Employee2.empID.in_(emp_ids)).all()
    emp_dict = {emp.empID: emp.fullname for emp in emp_query}  

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": v.id,
                "employee_id":v.employee_id,
                "employee_name": emp_dict.get(v.employee_id, "Unknown"), 
                "issue_date": v.issue_date.strftime("%Y-%m-%d"),
                "expiry_date": v.expiry_date.strftime("%Y-%m-%d"),
                "date_used": v.date_used.strftime("%Y-%m-%d") if v.date_used else None
            }
            for v in vouchers
        ]
    }

#TEST ROUTE
def search_voucher(db: Session, db2: Session, search_query: str = None):
    employee_data = db2.query(Employee2.empID, Employee2.fullname).all()
    
    if search_query:
        employee_data = db2.query(Employee2.empID, Employee2.fullname).filter(or_(
            Employee2.fullname.ilike(f"%{search_query}%"),
            Employee2.username.ilike(f"%{search_query}%"),
        )).all()
    
    employee_map = {emp_id: fullname for emp_id, fullname in employee_data}
    employee_ids = list(employee_map.keys())
    
    if not employee_ids:
        return {"voucher": []}
    
    result = db.query(Vouchers).filter(and_(Vouchers.employee_id.in_(employee_ids), Vouchers.date_used == None)).all()
    
    return {
        "voucher": [
            {
                "employee_id": i.employee_id,
                "fullname": employee_map.get(i.employee_id, ""),
                "issue_date": i.issue_date,
                "expiry_date": i.expiry_date,
                "date_used": i.date_used
            }
            for i in result
        ]
    }



#DISPLAY EMPLOYEE WITH AVAILABLE VOUCHERS => GETS OLDEST VOUCHER
def fetch_attendance_vouchers(db: Session, db2: Session, departments: list[str],username:str):
    today = date.today()
    if today.weekday() != voucher_day:
        return {"error": f"Vouchers can only be used on Saturdays"}  
    if not departments:
        return {"error": "Department is required"}
    branch = db2.query(Employee2.branch).filter(Employee2.username == username).scalar()

    emp_query = db2.query(
        Employee2.empID, Employee2.fullname
        ).filter(Employee2.department.in_(departments)).filter(
        Employee2.branch == branch
        ).all()
    
    emp_dict = {emp.empID: emp.fullname for emp in emp_query}

    if not emp_dict:
        return {"empty": 0, "data": []}
    
    vouchers = []
    for emp_id, fullname in emp_dict.items():
        voucher = (
            db.query(
                Vouchers.id, Vouchers.employee_id, Vouchers.expiry_date, 
                Attendance.id.label("attendance_id"), Attendance.time_in, Attendance.status
            )
            .join(Attendance, Attendance.employee_id == Vouchers.employee_id)  
            .filter(
                Vouchers.employee_id == emp_id,
                Vouchers.expiry_date >= today, 
                Vouchers.date_used.is_(None), 
                Attendance.date == today,
                Attendance.voucher_id.is_(None),
                Attendance.status == 'On time'
            )
            .order_by(Vouchers.issue_date)
            .first()
        )

        if voucher:
            vouchers.append({
                "voucher_id": voucher.id,
                "employee_id": voucher.employee_id,
                "employee_name": fullname,
                "expiry_date": voucher.expiry_date.strftime("%Y-%m-%d"),
                "attendance_id": voucher.attendance_id,
                "time_in": voucher.time_in.strftime("%H:%M:%S") if voucher.time_in else None,
                "status": voucher.status
            })

    return {"total": len(vouchers), "data": vouchers}


#DISPLAY VOUCHERS FOR EMPLOYEEs
def fetch_vouchers(db: Session, employee_id: int, date: date, voucher_id: int):
    vouchers = db.query(Vouchers).filter(  
        Vouchers.expiry_date >= date
    )
    if voucher_id:
        vouchers = vouchers.filter(Vouchers.id == voucher_id).all()
    else:
        vouchers = vouchers.filter(Vouchers.employee_id == employee_id,Vouchers.date_used == None).all()
    
    return vouchers

#VOUCHER CANCEL
def cancel_voucher(db: Session, voucher_id: int, att_id: int):
    if not voucher_id or not att_id:
        raise HTTPException(status_code=400, detail="voucher_id and att_id are required.")

    result = db.query(Attendance, Vouchers)\
        .join(Vouchers, Attendance.employee_id == Vouchers.employee_id)\
        .filter(
            Attendance.id == att_id,
            Attendance.voucher_id == voucher_id,
            Vouchers.id == voucher_id,
            Attendance.date <= Vouchers.expiry_date
        ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Invalid att_id or voucher_id")

    attendance, voucher = result

    if attendance.time_out < datetime.strptime('17:00:00', '%H:%M:%S').time() or attendance.date.weekday() != voucher_day:
        raise HTTPException(status_code=400, detail="Invalid")

    try:
        voucher.date_used = None
        attendance.voucher_id = None
        db.commit()
    except Exception as e:
        db.rollback()  
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Voucher successfully canceled"}

#VOUCHER USE FOR EMPLOYEEs
def use_voucher(db: Session, voucher_id: int = None, att_id: int = None):
    if not voucher_id or not att_id:
        raise HTTPException(status_code=400, detail="voucher_id and att_id are required.")

   
    result = db.query(Attendance, Vouchers)\
        .join(Vouchers, Attendance.employee_id == Vouchers.employee_id)\
        .filter(
            Attendance.id == att_id, 
            Vouchers.id == voucher_id,
            Attendance.date <= Vouchers.expiry_date
        ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Invalid att_id or voucher_id")

    attendance, voucher = result 
    if attendance.voucher_id:
        raise HTTPException(status_code=404, detail="Voucher already applied")

    if attendance.date.weekday() != voucher_day:
        raise HTTPException(status_code=403, detail="Voucher can only be used on a Saturday.")

    if attendance.status != 'On time':
        raise HTTPException(status_code=403, detail="Voucher can only be used if status is 'On time'")

    voucher.date_used = attendance.date
    attendance.voucher_id = voucher_id

    db.commit()
    return {"success": "Voucher applied successfully"}


#FOR PARSO REMARKS
def get_voucher_dates(db: Session, voucher_ids: list[int]):
    results = db.query(Vouchers.id, Vouchers.issue_date).filter(Vouchers.id.in_(voucher_ids)).all()

    voucher_dates = {}
    for row in results:
        start_date = (row.issue_date - timedelta(days=5)).strftime('%m-%d')  # "02-17"
        end_date = row.issue_date.strftime('%m-%d')  # "02-22"
        voucher_dates[str(row.id)] = f"{start_date} - {end_date}"

    return voucher_dates

#ALLOW HEAD/MANAGER TO APPLY VOUCHERS FOR EMPLOYEEs (CAN ONLY BE USED ON SATURDAYS)
def use_multiple_vouchers(db: Session, data: dict[int, int]):
    today = date.today()
    if today.weekday() != voucher_day:
        raise HTTPException(status_code=403, detail="Vouchers can only be used on a Saturday.")
    try:
        for update in data.updates:
            att_id = update.attendance_id
            voucher_id = update.voucher_id

            updated_rows = db.query(Attendance).filter(Attendance.id == att_id).update({"voucher_id": voucher_id})
            
            if updated_rows == 0:
                raise ValueError(f"Attendance ID {att_id} not found")  
            
            
            db.query(Vouchers).filter(Vouchers.id == voucher_id).update({"date_used": today})

        db.commit()
        return {"success": "Vouchers applied successfully"}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

#VOID VOUCHERS FOR PARSO
def use_vouchers(db: Session, voucher_ids: list[int], date: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    if not voucher_ids or not date:
        raise HTTPException(status_code=400, detail="voucher_ids and date_used are required.")
    if date_obj.weekday() != voucher_day:
        raise HTTPException(status_code=403, detail="Vouchers can only be used on a Saturday.")
    try:
        vouchers = db.query(Vouchers).filter(Vouchers.id.in_(voucher_ids)).all()

        if len(vouchers) != len(voucher_ids):
            raise HTTPException(status_code=404, detail="One or more voucher_ids are invalid")

        for voucher in vouchers:
            if voucher.date_used:
                raise HTTPException(status_code=400, detail=f"Voucher {voucher.id} already used")

        for voucher in vouchers:
            voucher.date_used = date  # Use provided date

        db.commit()
        return {"success": "Vouchers applied successfully"}

    except HTTPException as e:
        db.rollback()
        raise e  

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error. Transaction rolled back.")




