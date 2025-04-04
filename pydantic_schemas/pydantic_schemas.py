from pydantic import BaseModel, EmailStr, constr


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: constr(min_length=6)

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class PostCreate(BaseModel):
    """Schema for creating a new post. Limits text to 1MB."""
    text: constr(max_length=1000000)

class PostResponse(BaseModel):
    """Schema for returning post details."""
    id: int
    text: str