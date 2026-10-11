from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.scenario_runner import ScenarioRunner

router = APIRouter()

@router.get("/")
def list_scenarios(db: Session = Depends(get_db)):
    runner = ScenarioRunner(db)
    return runner.get_scenarios()

@router.post("/{scenario_id}/run")
def run_scenario(scenario_id: str, db: Session = Depends(get_db)):
    runner = ScenarioRunner(db)
    try:
        results = runner.run_scenario(scenario_id)
        return results
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
