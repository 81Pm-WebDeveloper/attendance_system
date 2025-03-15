from fastapi import HTTPException
from sqlalchemy.orm import Session
from models.vouchers import Vouchers
from models.attendance import Attendance
from datetime import date,datetime
#from schemas.attendance import VoucherUseRequest

from sqlalchemy.exc import SQLAlchemyError

def fetch_vouchers(db: Session, employee_id: int, date: date):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    if date_obj.weekday() != 5:
        raise HTTPException(status_code=400, detail="Vouchers are only valid for saturdays")
    vouchers = db.query(Vouchers).filter(
        Vouchers.employee_id == employee_id,
        Vouchers.date_used == None,  
        Vouchers.expiry_date >= date
    ).all()
    return vouchers

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

    if attendance.time_out < datetime.strptime('17:00:00', '%H:%M:%S').time() or attendance.date.weekday() != 5:
        raise HTTPException(status_code=400, detail="Invalid")

    try:
        voucher.date_used = None
        attendance.voucher_id = None
        db.commit()
    except Exception as e:
        db.rollback()  
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"message": "Voucher successfully canceled"}


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

    if attendance.date.weekday() != 5:
        raise HTTPException(status_code=403, detail="Voucher can only be used on a Saturday.")

    if attendance.status != 'On time':
        raise HTTPException(status_code=403, detail="Voucher can only be used if status is 'On time'")

    voucher.date_used = attendance.date
    attendance.voucher_id = voucher_id

    db.commit()
    return {"success": "Voucher applied successfully"}



def use_vouchers(db: Session, voucher_ids: list[int], date: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    if not voucher_ids or not date:
        raise HTTPException(status_code=400, detail="voucher_ids and date_used are required.")
    if date_obj.weekday() != 5:
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




