from fastapi import FastAPI
from db.database import engine
from models.attendance import Attendance
from routers import attendance_router


Attendance.metadata.create_all(bind=engine)

app = FastAPI(title="Attendance System")

app.include_router(attendance_router.router, prefix="/attendance", tags=["Attendance"])
