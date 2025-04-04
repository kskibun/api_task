import datetime
from typing import List

import jwt
from cachetools import TTLCache
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from models import User, Post
from pydantic_schemas import UserCreate, UserLogin, PostCreate, PostResponse

# Database Configuration
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security Settings
SECRET_KEY = ""
ALGORITHM = "HS256"

# Caching Mechanism (5-minute TTL)
post_cache = TTLCache(maxsize=100, ttl=300)


def get_db():
    """Provides a database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(user_id: int):
    """Generates a JWT token for the given user ID."""
    payload = {"sub": user_id, "exp": datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, db: Session):
    """Verifies and decodes a JWT token, returning the associated user."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(User.id == payload["sub"]).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# FastAPI Instance
app = FastAPI()

@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """Handles user registration and returns an authentication token."""
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"token": create_token(new_user.id)}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Authenticates a user and returns a JWT token upon successful login."""
    user_record = db.query(User).filter(User.email == user.email, User.password == user.password).first()
    if not user_record:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"token": create_token(user_record.id)}

@app.post("/addpost")
def add_post(post: PostCreate, token: str, db: Session = Depends(get_db)):
    """Creates a new post for the authenticated user and invalidates cache."""
    user = verify_token(token, db)
    new_post = Post(text=post.text, owner_id=user.id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    post_cache.pop(user.id, None)
    return {"postID": new_post.id}

@app.get("/getposts", response_model=List[PostResponse])
def get_posts(token: str, db: Session = Depends(get_db)):
    """Retrieves all posts for the authenticated user, with caching enabled."""
    user = verify_token(token, db)
    if user.id in post_cache:
        return post_cache[user.id]
    posts = db.query(Post).filter(Post.owner_id == user.id).all()
    post_cache[user.id] = posts
    return posts

@app.delete("/deletepost")
def delete_post(postID: int, token: str, db: Session = Depends(get_db)):
    """Deletes a specific post for the authenticated user and invalidates cache."""
    user = verify_token(token, db)
    post = db.query(Post).filter(Post.id == postID, Post.owner_id == user.id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    post_cache.pop(user.id, None)
    return {"detail": "Post deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    Base.metadata.create_all(bind=engine)