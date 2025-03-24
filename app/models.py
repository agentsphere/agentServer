

from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    id: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    mail: Optional[str] = None
    token: Optional[str] = None