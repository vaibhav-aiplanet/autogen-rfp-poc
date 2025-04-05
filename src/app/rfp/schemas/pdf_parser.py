from pydantic import BaseModel


class CreateFolder(BaseModel):
    name: str
    description: str
