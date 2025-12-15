import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import jwt
import bcrypt
from dotenv import load_dotenv

load_dotenv()

from agent import process_message
from database import DatabaseStorage

# ==================== Configuration ====================
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 7 * 24  # 7 days
PYTHON_BACKEND_PORT = int(os.getenv("PYTHON_BACKEND_PORT", 8000))

# Initialize database storage
storage = DatabaseStorage()

# ==================== Data Models ====================
class TokenPayload(BaseModel):
    userId: str
    email: str

class UserBase(BaseModel):
    email: EmailStr
    username: str
    fullName: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    fullName: Optional[str] = None
    avatar: Optional[str] = None

class UserResponse(UserBase):
    id: str
    avatar: Optional[str] = None
    createdAt: str
    updatedAt: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    user: UserResponse
    token: str

class FlightSegment(BaseModel):
    departure: dict
    arrival: dict
    carrierCode: str
    carrierName: Optional[str] = None
    number: str
    aircraft: Optional[str] = None
    duration: str
    numberOfStops: int

class FlightOffer(BaseModel):
    id: str
    price: dict
    itineraries: list
    numberOfBookableSeats: Optional[int] = None
    validatingAirlineCodes: Optional[list] = None
    travelClass: Optional[str] = None
    tags: Optional[list] = None

class ChatMessageModel(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    flightResults: Optional[list] = []
    isStreaming: Optional[bool] = False
    memoryContext: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None
    userId: Optional[str] = None

class ChatResponse(BaseModel):
    message: ChatMessageModel
    conversationId: str

class ConversationModel(BaseModel):
    id: str
    userId: str
    messages: list
    createdAt: str
    updatedAt: str

# ==================== Authentication Functions ====================
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hash_value: str) -> bool:
    return bcrypt.checkpw(password.encode(), hash_value.encode())

def generate_token(user: dict) -> str:
    payload = {
        "userId": user["id"],
        "email": user["email"],
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, ValueError):
        return None

def extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:]

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    token = extract_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = storage.get_user(payload.userId)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user

# ==================== FastAPI App ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[FastAPI] Travel Assistant Backend started on port {PYTHON_BACKEND_PORT}")
    yield
    print("[FastAPI] Travel Assistant Backend shutting down")

app = FastAPI(
    title="Travel Assistant API",
    description="Agentic travel assistant with flight search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Health Check ====================
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }

# ==================== Authentication Routes ====================
@app.post("/api/auth/register", status_code=201)
async def register(user_data: UserCreate):
    try:
        # Check if email exists
        if storage.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Check if username exists
        if storage.get_user_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        # Create user
        password_hash = hash_password(user_data.password)
        user = storage.create_user(user_data, password_hash)

        # Generate token
        token = generate_token(user)

        # Return response without password
        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            username=user["username"],
            fullName=user["fullName"],
            avatar=user["avatar"],
            createdAt=user["createdAt"],
            updatedAt=user["updatedAt"],
        )

        return JSONResponse(
            status_code=201,
            content={
                "user": user_response.model_dump(),
                "token": token
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Register endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )

@app.post("/api/auth/login")
async def login(credentials: LoginRequest):
    try:
        user = storage.get_user_by_email(credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not verify_password(credentials.password, user["passwordHash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = generate_token(user)

        user_response = UserResponse(
            id=user["id"],
            email=user["email"],
            username=user["username"],
            fullName=user["fullName"],
            avatar=user["avatar"],
            createdAt=user["createdAt"],
            updatedAt=user["updatedAt"],
        )

        return JSONResponse(
            status_code=200,
            content={
                "user": user_response.model_dump(),
                "token": token
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Login endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        username=current_user["username"],
        fullName=current_user["fullName"],
        avatar=current_user["avatar"],
        createdAt=current_user["createdAt"],
        updatedAt=current_user["updatedAt"],
    )

@app.put("/api/auth/profile", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    current_user: dict = Depends(get_current_user),
):
    updated_user = storage.update_user(current_user["id"], updates)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=updated_user["id"],
        email=updated_user["email"],
        username=updated_user["username"],
        fullName=updated_user["fullName"],
        avatar=updated_user["avatar"],
        createdAt=updated_user["createdAt"],
        updatedAt=updated_user["updatedAt"],
    )

# ==================== Chat Routes ====================
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        if not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required",
            )

        user_id = current_user["id"]
        conversation_id = request.conversationId

        # Create conversation if not exists
        if not conversation_id:
            conversation = storage.create_conversation(user_id)
            conversation_id = conversation["id"]
        else:
            conversation = storage.get_conversation(conversation_id)
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
            if conversation["userId"] != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )

        # Build conversation history
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation.get("messages", [])
        ]

        # Process message with agent
        result = process_message(
            user_message=request.message,
            user_id=user_id,
            conversation_history=conversation_history,
        )

        # Create response message
        response_message = ChatMessageModel(
            id=str(uuid.uuid4()),
            role="assistant",
            content=result["content"],
            timestamp=datetime.now().isoformat(),
            flightResults=result.get("flight_results", []),
            memoryContext=result.get("memory_context"),
        )

        # Add messages to conversation
        storage.add_message(conversation_id, {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat(),
        })
        storage.add_message(conversation_id, response_message.model_dump())

        return ChatResponse(
            message=response_message,
            conversationId=conversation_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )

@app.get("/api/conversations/{conversation_id}", response_model=ConversationModel)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conversation["userId"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return ConversationModel(**conversation)

@app.get("/api/conversations", response_model=list[ConversationModel])
async def list_conversations(current_user: dict = Depends(get_current_user)):
    conversations = storage.get_user_conversations(current_user["id"])
    return [ConversationModel(**conv) for conv in conversations]

# ==================== Run Server ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PYTHON_BACKEND_PORT,
        log_level="info",
    )
