from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.scenario_runner import ScenarioRunner


def load_scenarios(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """
    Returns the collection of predefined demonstration scenarios (A through E).
    If a database session is provided, ScenarioRunner initializes the active context.
    """
    runner = ScenarioRunner(db=db)
    return runner.get_scenarios()
