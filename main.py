from fastapi import FastAPI
from db.database import engine
from db.database2 import engine2
from models.attendance import Attendance
from models.leave_app import Leave
from models.vouchers import Vouchers
from models.scoreboard import Score
from models.attendance_summary import Summary
from models.emp_list import Employee2
from routers import attendance_router
from routers import voucher_router
from routers import summary_router
from routers import scoreboard_router
#from routers import employee_router
from routers import leave_router
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import os

load_dotenv()


Attendance.metadata.create_all(bind=engine)
#Employee.metadata.create_all(bind=engine)
Summary.metadata.create_all(bind=engine)
Vouchers.metadata.create_all(bind=engine)
Score.metadata.create_all(bind=engine)


Employee2.metadata.create_all(bind=engine2)
Leave.metadata.create_all(bind=engine2)

#is_local = os.getenv("ENV", "local") == "local"

app = FastAPI(title="Attendance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"], 
    allow_headers=["*"],  
)

#app.include_router(employee_router.router, prefix="/employee", tags=["Employee"])
app.include_router(attendance_router.router, prefix="/attendance", tags=["Attendance"])
app.include_router(summary_router.router, prefix="/summary", tags=["Summary"])
app.include_router(leave_router.router, prefix="/leave-app", tags=["Leave"])

app.include_router(scoreboard_router.router, prefix="/score", tags=["Score"]) #SideQuest


app.include_router(voucher_router.router,prefix = "/voucher", tags=["Voucher"])  # RELEASE
