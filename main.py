from fastapi import FastAPI
from db.database import engine
from models.attendance import Attendance
from models.employees import Employee
from models.attendance_summary import Summary
from routers import attendance_router
from routers import summary_router

Attendance.metadata.create_all(bind=engine)
Employee.metadata.create_all(bind=engine)
Summary.metadata.create_all(bind=engine)

app = FastAPI(title="Attendance System")

app.include_router(attendance_router.router, prefix="/attendance", tags=["Attendance"])
app.include_router(summary_router.router, prefix="/summary", tags=["Summary"])