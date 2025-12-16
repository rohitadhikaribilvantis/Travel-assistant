import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./travel_assistant.db")

# For SQLite, use StaticPool to ensure thread safety
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== Models ====================
class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    fullName = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    passwordHash = Column(String)
    createdAt = Column(String)
    updatedAt = Column(String)

class ConversationModel(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True)
    userId = Column(String, index=True)
    title = Column(String, default="New Conversation")
    messages = Column(Text, default="[]")  # JSON string
    archived = Column(String, default="false")  # "true" or "false"
    createdAt = Column(String)
    updatedAt = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== Database Operations ====================
class DatabaseStorage:
    def __init__(self):
        pass
    
    @staticmethod
    def get_session():
        return SessionLocal()
    
    def create_user(self, user_data, password_hash: str) -> dict:
        """Create a new user in the database."""
        db = self.get_session()
        try:
            user_id = user_data.__dict__.get("id") or str(__import__("uuid").uuid4())
            now = datetime.now().isoformat()
            
            db_user = UserModel(
                id=user_id,
                email=user_data.email,
                username=user_data.username,
                fullName=user_data.fullName,
                avatar=None,
                passwordHash=password_hash,
                createdAt=now,
                updatedAt=now,
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            return {
                "id": db_user.id,
                "email": db_user.email,
                "username": db_user.username,
                "fullName": db_user.fullName,
                "avatar": db_user.avatar,
                "passwordHash": db_user.passwordHash,
                "createdAt": db_user.createdAt,
                "updatedAt": db_user.updatedAt,
            }
        finally:
            db.close()
    
    def get_user_by_email(self, email: str) -> dict:
        """Get user by email."""
        db = self.get_session()
        try:
            user = db.query(UserModel).filter(UserModel.email == email).first()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "fullName": user.fullName,
                    "avatar": user.avatar,
                    "passwordHash": user.passwordHash,
                    "createdAt": user.createdAt,
                    "updatedAt": user.updatedAt,
                }
            return None
        finally:
            db.close()
    
    def get_user_by_username(self, username: str) -> dict:
        """Get user by username."""
        db = self.get_session()
        try:
            user = db.query(UserModel).filter(UserModel.username == username).first()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "fullName": user.fullName,
                    "avatar": user.avatar,
                    "passwordHash": user.passwordHash,
                    "createdAt": user.createdAt,
                    "updatedAt": user.updatedAt,
                }
            return None
        finally:
            db.close()
    
    def get_user(self, user_id: str) -> dict:
        """Get user by ID."""
        db = self.get_session()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "fullName": user.fullName,
                    "avatar": user.avatar,
                    "passwordHash": user.passwordHash,
                    "createdAt": user.createdAt,
                    "updatedAt": user.updatedAt,
                }
            return None
        finally:
            db.close()
    
    def update_user(self, user_id: str, updates) -> dict:
        """Update user information."""
        db = self.get_session()
        try:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                return None
            
            if updates.fullName is not None:
                user.fullName = updates.fullName
            if updates.avatar is not None:
                user.avatar = updates.avatar
            
            user.updatedAt = datetime.now().isoformat()
            db.commit()
            db.refresh(user)
            
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "fullName": user.fullName,
                "avatar": user.avatar,
                "passwordHash": user.passwordHash,
                "createdAt": user.createdAt,
                "updatedAt": user.updatedAt,
            }
        finally:
            db.close()
    
    def create_conversation(self, user_id: str) -> dict:
        """Create a new conversation."""
        db = self.get_session()
        try:
            conv_id = str(__import__("uuid").uuid4())
            now = datetime.now().isoformat()
            
            conversation = ConversationModel(
                id=conv_id,
                userId=user_id,
                messages="[]",
                createdAt=now,
                updatedAt=now,
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            return {
                "id": conversation.id,
                "userId": conversation.userId,
                "title": conversation.title,
                "messages": json.loads(conversation.messages),
                "archived": conversation.archived == "true",
                "createdAt": conversation.createdAt,
                "updatedAt": conversation.updatedAt,
            }
        finally:
            db.close()
    
    def get_conversation(self, conversation_id: str) -> dict:
        """Get conversation by ID."""
        db = self.get_session()
        try:
            conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
            if conv:
                return {
                    "id": conv.id,
                    "userId": conv.userId,
                    "title": conv.title,
                    "messages": json.loads(conv.messages),
                    "archived": conv.archived == "true",
                    "createdAt": conv.createdAt,
                    "updatedAt": conv.updatedAt,
                }
            return None
        finally:
            db.close()
    
    def add_message(self, conversation_id: str, message: dict) -> dict:
        """Add a message to a conversation."""
        db = self.get_session()
        try:
            conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
            if not conv:
                return None
            
            messages = json.loads(conv.messages)
            messages.append(message)
            conv.messages = json.dumps(messages)
            conv.updatedAt = datetime.now().isoformat()
            
            db.commit()
            db.refresh(conv)
            
            return {
                "id": conv.id,
                "userId": conv.userId,
                "messages": json.loads(conv.messages),
                "createdAt": conv.createdAt,
                "updatedAt": conv.updatedAt,
            }
        finally:
            db.close()
    
    def get_user_conversations(self, user_id: str) -> list:
        """Get all conversations for a user."""
        db = self.get_session()
        try:
            convs = db.query(ConversationModel).filter(ConversationModel.userId == user_id).all()
            return [
                {
                    "id": conv.id,
                    "userId": conv.userId,
                    "title": conv.title,
                    "messages": json.loads(conv.messages),
                    "archived": conv.archived == "true",
                    "createdAt": conv.createdAt,
                    "updatedAt": conv.updatedAt,
                }
                for conv in convs
            ]
        finally:
            db.close()
    
    def rename_conversation(self, conversation_id: str, new_title: str) -> dict:
        """Rename a conversation."""
        db = self.get_session()
        try:
            conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
            if not conv:
                return None
            
            conv.title = new_title
            conv.updatedAt = datetime.now().isoformat()
            db.commit()
            db.refresh(conv)
            
            return {
                "id": conv.id,
                "userId": conv.userId,
                "title": conv.title,
                "messages": json.loads(conv.messages),
                "archived": conv.archived == "true",
                "createdAt": conv.createdAt,
                "updatedAt": conv.updatedAt,
            }
        finally:
            db.close()
    
    def archive_conversation(self, conversation_id: str, archived: bool) -> dict:
        """Archive or unarchive a conversation."""
        db = self.get_session()
        try:
            conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
            if not conv:
                return None
            
            conv.archived = "true" if archived else "false"
            conv.updatedAt = datetime.now().isoformat()
            db.commit()
            db.refresh(conv)
            
            return {
                "id": conv.id,
                "userId": conv.userId,
                "title": conv.title,
                "messages": json.loads(conv.messages),
                "archived": conv.archived == "true",
                "createdAt": conv.createdAt,
                "updatedAt": conv.updatedAt,
            }
        finally:
            db.close()
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        db = self.get_session()
        try:
            conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
            if not conv:
                return False
            
            db.delete(conv)
            db.commit()
            return True
        finally:
            db.close()
