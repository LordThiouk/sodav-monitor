from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class ReportRequest(BaseModel):
    type: str
    format: str = "csv"
    start_date: datetime
    end_date: datetime
    filters: Optional[Dict] = None


class ReportResponse(BaseModel):
    id: int
    type: str
    status: str
    format: str
    created_at: datetime
    completed_at: Optional[datetime] = None
