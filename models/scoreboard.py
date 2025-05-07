from sqlalchemy import Column, Integer, String,DateTime,Date
from db.database import Base
from datetime import datetime
class Score(Base):
    __tablename__ = "scoreboard"

    username = Column(String(50),primary_key=True)
    score = Column(Integer,nullable=False)
    last_submission = Column(Date, nullable=True)