from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.voucher_service as voucherService
from db.database import get_db
from dotenv import load_dotenv
import os
from config.authentication import verify_key
from schemas.attendance import VoucherUseRequest
from schemas.voucher import parsoVouchers

router = APIRouter()
@router.put
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