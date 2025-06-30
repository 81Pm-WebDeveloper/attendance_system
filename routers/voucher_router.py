from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.voucher_service as voucherService
from db.database import get_db
from db.database2 import get_db2
from dotenv import load_dotenv
import os
from config.authentication import verify_key
from schemas.attendance import VoucherUseRequest
from schemas.voucher import parsoVouchers, VoucherUpdateRequest
from typing import List
from schemas.voucher import InsertVoucher

router = APIRouter()

@router.post("/generate-vouchers/",status_code=201,dependencies=[Depends(verify_key)])
def generate_vouchers(db: Session = Depends(get_db)):
    """
    GENERATES VOUCHERS - CRON/SCHEDULED TASK/MANUAL KAHIT ANOO
    """
    date_from, date_to = voucherService.get_last_week_range()
    required_days = voucherService.check_holiday(db, date_from, date_to)
    emp_list = voucherService.get_perfect_attendance(db, date_from, date_to, required_days)

    if not emp_list:
        return {"message": "No employees qualified for vouchers."}

    try:
        voucherService.generate_voucher(db, emp_list, date_to)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error issuing vouchers: {str(e)}")

    return {"message": f"Vouchers issued to: {emp_list}"}

@router.post("/search/",status_code=200,dependencies=[Depends(verify_key)])
def search_voucher(search_query:str = None,db:Session=Depends(get_db),db2:Session=Depends(get_db2)):
    try:
        result = voucherService.search_voucher(db,db2,search_query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.post("/insert/",status_code=202,dependencies=[Depends(verify_key)])
def insert_voucher(voucher: InsertVoucher,db:Session = Depends(get_db)):
    """
    MANUAL VOUCHER INSERT - FOR HR
    """
    try:
        result = voucherService.insert_voucher(db, voucher)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/all/",status_code=200,dependencies=[Depends(verify_key)])
def fetch_all_vouchers(
    db:Session = Depends(get_db),
    db2:Session = Depends(get_db2),
    page: int =None,
    page_size:int =None,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
    used_filter: str = None  
):
    """
    FETCH ALL VOUCHER - NOT USED 
    """
    try:
        result = voucherService.fetch_all_vouchers(db,db2,page,page_size,search_query,date_from,date_to,employee_id_filter,used_filter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")
    

@router.post('/eligible-employees/', status_code=200, dependencies=[Depends(verify_key)])
def fetch_eligible_emp(db: Session = Depends(get_db), db2: Session = Depends(get_db2), departments: List[str] = None,username:str= None):
    """
    GETS ALL EMPLOYEE ELIGABLE EMPLOYEES FOR VOUCHER USE - APPLY VOUCHER on EPORTAL 
    """
    try:
        result = voucherService.fetch_attendance_vouchers(db, db2, departments,username)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")


@router.get("/", status_code=200, dependencies=[Depends(verify_key)])
def fetch_vouchers(
    db: Session = Depends(get_db),
    employee_id: int = None,
    date: str = None,
    voucher_id: int= None
):
    """
    RETURN VOUCHERS FOR EACH EMPLOYEE
    """
    if employee_id is None:
        raise HTTPException(status_code=400, detail="Employee ID is required.")

    try:
        result = voucherService.fetch_vouchers(db, employee_id,date,voucher_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    

@router.post("/perfect-attendance/", status_code=200, dependencies=[Depends(verify_key)])
def perfect_attendance_dates(voucher_ids: List[int], db: Session = Depends(get_db)):
    """
    RETURN PERFECT ATTENDANCE DATES - FOR PARSO LEAVE REMARKS
    """
    if not voucher_ids:
        raise HTTPException(status_code=400, detail="voucher_ids are required.")
    
    return voucherService.get_voucher_dates(db, voucher_ids)

@router.put("/",status_code=200, dependencies=[Depends(verify_key)])
def use_voucher(body: VoucherUseRequest, db: Session = Depends(get_db)):
    """
    VOUCHER USE FOR EMPLOYEE
    """
    try:
        return voucherService.use_voucher(db, body.voucher_id, body.att_id )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.put("/cancel/",status_code=200, dependencies=[Depends(verify_key)])
def cancel_voucher(body: VoucherUseRequest, db: Session= Depends(get_db)):
    """
    CANCEL/REMOVE VOUCHER
    """
    try:
        return voucherService.cancel_voucher(db,body.voucher_id,body.att_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")
    
@router.put("/parso/",status_code=200, dependencies=[Depends(verify_key)])
def use_parso(body: parsoVouchers, db: Session= Depends(get_db)):
    """
    VOIDS VOUCHERS WHEN PARSO LEAVE == APPROVED - TRIGGERED IN post_leave_status.php
    """
    try:
        return voucherService.use_vouchers(db,body.voucher_ids, body.date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")

@router.put("/multiple/",status_code=200, dependencies=[Depends(verify_key)])
def use_multiple_voucher(body:VoucherUpdateRequest,db:Session = Depends(get_db)):
    """
    Enables heads/manager or kahit sino iassign to redeem vouchers for their team members
    """
    try:
        return voucherService.use_multiple_vouchers(db,body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")
