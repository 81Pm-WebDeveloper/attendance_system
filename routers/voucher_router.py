from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.voucher_service as voucherService
from db.database import get_db
from db.database2 import get_db2
from dotenv import load_dotenv
import os
from config.authentication import verify_key
from schemas.attendance import VoucherUseRequest
from schemas.voucher import parsoVouchers
from typing import List
router = APIRouter()

@router.get("/all/",status_code=200,dependencies=[Depends(verify_key)])
def fetch_all_vouchers(
    db:Session = Depends(get_db),
    db2:Session = Depends(get_db2),
    page: int =1,
    page_size:int =10,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
    used_filter: str = 'unused'  
):
    try:
        result = voucherService.fetch_all_vouchers(db,db2,page,page_size,search_query,date_from,date_to,employee_id_filter,used_filter)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")
    
@router.get('/unused/',status_code=200, dependencies=[Depends(verify_key)])
def fetch_unused_vouchers(db:Session =Depends(get_db),db2:Session=Depends(get_db2), username: str = None):
    try:
        result = voucherService.fetch_oldest_unused_vouchers(db,db2,username)
        return result
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/", status_code=200, dependencies=[Depends(verify_key)])
def fetch_vouchers(
    db: Session = Depends(get_db),
    employee_id: int = None,
    date: str = None
):
    if employee_id is None:
        raise HTTPException(status_code=400, detail="Employee ID is required.")

    try:
        result = voucherService.fetch_vouchers(db, employee_id,date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    

@router.post("/perfect-attendance/", status_code=200, dependencies=[Depends(verify_key)])
def perfect_attendance_dates(voucher_ids: List[int], db: Session = Depends(get_db)):
    if not voucher_ids:
        raise HTTPException(status_code=400, detail="voucher_ids are required.")
    
    return voucherService.get_voucher_dates(db, voucher_ids)



@router.put("/",status_code=200, dependencies=[Depends(verify_key)])
def use_voucher(body: VoucherUseRequest, db: Session = Depends(get_db)):
    try:
        return voucherService.use_voucher(db, body.voucher_id, body.att_id )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.put("/cancel/",status_code=200, dependencies=[Depends(verify_key)])
def cancel_voucher(body: VoucherUseRequest, db: Session= Depends(get_db)):
    try:
        return voucherService.cancel_voucher(db,body.voucher_id,body.att_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")
    
@router.put("/parso/",status_code=200, dependencies=[Depends(verify_key)])
def use_parso(body: parsoVouchers, db: Session= Depends(get_db)):
    try:
        return voucherService.use_vouchers(db,body.voucher_ids, body.date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occured: {e}")