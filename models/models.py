from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    """User model representing registered users."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    posts = relationship("Post", back_populates="owner")

class Post(Base):
    """Post model representing user-generated posts."""
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="posts")