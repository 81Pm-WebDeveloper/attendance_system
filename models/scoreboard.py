from sqlalchemy import Column, Integer, String,DateTime,Date,Text
from db.database import Base
from datetime import datetime

class Score(Base):
    __tablename__ = "scoreboard"

    username = Column(String(50),primary_key=True)
    score = Column(Integer,nullable=False)
    guesses = Column(Text)
    last_guess_submission = Column(Date, nullable=True)
    last_submission = Column(Date, nullable=True)