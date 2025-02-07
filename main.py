from fastapi import FastAPI
from db.database import engine
from db.database2 import engine2
from models.attendance import Attendance
from models.employees import Employee
from models.attendance_summary import Summary
from models.emp_list import Employee2
from routers import attendance_router
from routers import summary_router
from routers import employee_router

from fastapi.middleware.cors import CORSMiddleware




Attendance.metadata.create_all(bind=engine)
Employee.metadata.create_all(bind=engine)
Summary.metadata.create_all(bind=engine)
Employee2.metadata.create_all(bind=engine2)



app = FastAPI(title="Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"], 
    allow_headers=["*"],  
)


app.include_router(employee_router.router, prefix="/employee", tags=["Employee"])
app.include_router(attendance_router.router, prefix="/attendance", tags=["Attendance"])
app.include_router(summary_router.router, prefix="/summary", tags=["Summary"])
