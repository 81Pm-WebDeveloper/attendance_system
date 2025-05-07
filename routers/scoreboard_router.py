from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
import services.scoreboard_service as scoreService
from config.authentication import verify_key
from schemas.scoreboard_schema import ScoreRequest

router = APIRouter()

@router.post("/submit-score/", status_code=200, dependencies=[Depends(verify_key)])
def submit_score(body: ScoreRequest, db: Session = Depends(get_db)):
    try:
        result = scoreService.submit_score(db, body)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting score: {str(e)}")


@router.get("/leaderboard/",status_code=200,dependencies=[Depends(verify_key)])
def get_leaderboard(db:Session = Depends(get_db)):
    try:
        result = scoreService.get_leaderboard(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")
