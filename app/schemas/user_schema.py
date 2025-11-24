from uuid import UUID
from pydantic import EmailStr, ConfigDict


class UserResponse:
    uid: UUID
    email: EmailStr
    status: bool
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)
