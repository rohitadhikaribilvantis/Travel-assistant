import os
import json
from datetime import datetime
from collections import Counter
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


class BookingModel(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, index=True)
    userId = Column(String, index=True)

    origin = Column(String, nullable=True)
    destination = Column(String, nullable=True)

    airlineCode = Column(String, nullable=True)
    airlineName = Column(String, nullable=True)

    tripType = Column(String, nullable=True)

    departureDate = Column(String, nullable=True)
    departureTime = Column(String, nullable=True)
    arrivalTime = Column(String, nullable=True)

    returnOrigin = Column(String, nullable=True)
    returnDestination = Column(String, nullable=True)
    returnDate = Column(String, nullable=True)
    returnDepartureTime = Column(String, nullable=True)
    returnArrivalTime = Column(String, nullable=True)

    cabinClass = Column(String, nullable=True)

    price = Column(String, nullable=True)
    currency = Column(String, nullable=True)

    bookedAt = Column(String, nullable=True)
    createdAt = Column(String)

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

    def add_booking(self, user_id: str, booking: dict) -> dict:
        """Persist a booking record for travel history."""
        db = self.get_session()
        try:
            booking_id = str(__import__("uuid").uuid4())
            now = datetime.now().isoformat()
            booked_at = booking.get("booked_at") or now

            db_booking = BookingModel(
                id=booking_id,
                userId=user_id,
                origin=booking.get("origin"),
                destination=booking.get("destination"),
                airlineCode=booking.get("airline") or booking.get("airline_code"),
                airlineName=booking.get("airline_name") or booking.get("airline"),
                tripType=booking.get("trip_type") or booking.get("tripType"),
                departureDate=booking.get("departure_date"),
                departureTime=booking.get("departure_time"),
                arrivalTime=booking.get("arrival_time"),
                returnOrigin=booking.get("return_origin"),
                returnDestination=booking.get("return_destination"),
                returnDate=booking.get("return_date"),
                returnDepartureTime=booking.get("return_departure_time"),
                returnArrivalTime=booking.get("return_arrival_time"),
                cabinClass=booking.get("cabin_class"),
                price=str(booking.get("price")) if booking.get("price") is not None else None,
                currency=booking.get("currency"),
                bookedAt=booked_at,
                createdAt=now,
            )

            db.add(db_booking)
            db.commit()
            db.refresh(db_booking)

            return {
                "id": db_booking.id,
                "origin": db_booking.origin,
                "destination": db_booking.destination,
                "airline": db_booking.airlineName or db_booking.airlineCode,
                "airline_code": db_booking.airlineCode,
                "airline_name": db_booking.airlineName,
                "tripType": db_booking.tripType,
                "departure_date": db_booking.departureDate,
                "departure_time": db_booking.departureTime,
                "arrival_time": db_booking.arrivalTime,
                "return_origin": db_booking.returnOrigin,
                "return_destination": db_booking.returnDestination,
                "return_date": db_booking.returnDate,
                "return_departure_time": db_booking.returnDepartureTime,
                "return_arrival_time": db_booking.returnArrivalTime,
                "cabin_class": db_booking.cabinClass,
                "price": float(db_booking.price) if db_booking.price else None,
                "currency": db_booking.currency,
                "booked_at": db_booking.bookedAt,
            }
        finally:
            db.close()

    def list_bookings(self, user_id: str) -> list:
        """Return all bookings for a user (newest first)."""
        db = self.get_session()
        try:
            rows = (
                db.query(BookingModel)
                .filter(BookingModel.userId == user_id)
                .order_by(BookingModel.bookedAt.desc())
                .all()
            )

            result = []
            for r in rows:
                result.append(
                    {
                        "id": r.id,
                        "origin": r.origin,
                        "destination": r.destination,
                        "airline": r.airlineName or r.airlineCode,
                        "airline_code": r.airlineCode,
                        "airline_name": r.airlineName,
                        "tripType": r.tripType,
                        "departure_date": r.departureDate,
                        "departure_time": r.departureTime,
                        "arrival_time": r.arrivalTime,
                        "return_origin": r.returnOrigin,
                        "return_destination": r.returnDestination,
                        "return_date": r.returnDate,
                        "return_departure_time": r.returnDepartureTime,
                        "return_arrival_time": r.returnArrivalTime,
                        "cabin_class": r.cabinClass,
                        "price": float(r.price) if r.price else None,
                        "currency": r.currency,
                        "booked_at": r.bookedAt,
                    }
                )
            return result
        finally:
            db.close()

    def list_frequent_routes(self, user_id: str, limit: int = 5) -> list:
        """Return the most frequent routes based on saved bookings."""
        bookings = self.list_bookings(user_id)
        counter: Counter[str] = Counter()

        def norm_iata(value: str | None) -> str | None:
            if not isinstance(value, str):
                return None
            code = value.strip().upper()
            return code if len(code) == 3 else None

        for b in bookings:
            o = norm_iata(b.get("origin"))
            d = norm_iata(b.get("destination"))
            if o and d:
                counter[f"{o} → {d}"] += 1

            ro = norm_iata(b.get("return_origin"))
            rd = norm_iata(b.get("return_destination"))
            if ro and rd:
                counter[f"{ro} → {rd}"] += 1

        if not counter:
            return []

        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        return [{"route": route, "count": count} for route, count in ranked[: max(1, limit)]]
    
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
