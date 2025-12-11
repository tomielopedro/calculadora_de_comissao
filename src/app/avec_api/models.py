from pydantic import BaseModel
from typing import Optional

class Servico(BaseModel):
    id:int
    servico: str
    tempo: int
    valor: Optional[float] = None
    categoria: str
