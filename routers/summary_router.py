from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import services.summary_service as summaryService
import services.attendance_service as attendanceService
from db.database import get_db
from schemas.summary import UpdateSummary 

router = APIRouter()

@router.post("/", status_code=200)
def insert_summary(
    db: Session = Depends(get_db),
    start_date = str,
    end_date = str 
    ):
    try:
        response = attendanceService.fetch_attendance_between_dates(db,start_date,end_date)

        data = [
            {
                "employee_id": row["employee_id"],
                "date": row["date"],
                "time_in":row["time_in"],
                "time_out":row["time_out"],
                "status": row["status"],
            }
            for row in response
        ]
        
        entries = summaryService.insert_summary(db, data)

        return {"detail": f"Summary logs inserted",
                "data": entries}
    except HTTPException as e:
        raise e  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

@router.get("/",status_code=200)
def get_summary(
    db:Session = Depends(get_db),
    page: int = 1,
    page_size: int = None,
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None):
    try:
        return summaryService.fetch_summary(db,page,page_size,search_query,date_from,date_to,employee_id_filter)
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"An error occured: {e}")

@router.get("/count")
def fetch_summary_count(
    db: Session = Depends(get_db),
    search_query: str = None,
    date_from: str = None,
    date_to: str = None,
    employee_id_filter: str = None,
):
    try:
        summary_data = summaryService.fetch_count(
            db=db,
            search_query=search_query,
            date_from=date_from,
            date_to=date_to,
            employee_id_filter=employee_id_filter,
        )
        return summary_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")

@router.put("/{id}", status_code=200)
def update_summary(id : int , data: UpdateSummary, db: Session = Depends(get_db)):
    try:
        updated_summary = summaryService.update_status(db,id,data)
        return {"message": "Summary updated successfully", "summary": updated_summary}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
