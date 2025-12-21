import os
import re
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

from agent import process_message, _infer_preference_memory_type
from database import DatabaseStorage

# ==================== Configuration ====================
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 7 * 24  # 7 days

# Prefer the conventional PORT (used by many hosts), fallback to legacy PYTHON_BACKEND_PORT.
_port_raw = os.getenv("PORT") or os.getenv("PYTHON_BACKEND_PORT") or "8000"
try:
    PYTHON_BACKEND_PORT = int(_port_raw)
except Exception:
    PYTHON_BACKEND_PORT = 8000

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
    appliedPrefs: Optional[str] = None
    travelHistory: Optional[list] = None

class ChatRequest(BaseModel):
    message: str
    conversationId: Optional[str] = None
    userId: Optional[str] = None
    currentPreferences: Optional[dict] = None

class ChatResponse(BaseModel):
    message: ChatMessageModel
    conversationId: str

class ConversationModel(BaseModel):
    id: str
    userId: str
    title: str
    messages: list
    archived: bool
    createdAt: str
    updatedAt: str

class DeleteAllConversationsRequest(BaseModel):
    deletePreferences: bool = False

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

        # Load user memories before processing (this will be included in system prompt)
        # The agent's get_system_prompt_with_memory already handles this
        
        # Process message with agent
        result = process_message(
            user_message=request.message,
            user_id=user_id,
            conversation_history=conversation_history,
            current_preferences=request.currentPreferences or {},
            username=current_user.get("username"),
        )

        # Extract preferences from the conversation
        extracted_preferences = result.get("extracted_preferences", [])

        # Avoid persisting ephemeral request phrasing as long-lived preferences.
        # Example: "cheap flights" should influence the current search, but shouldn't
        # permanently store a "budget conscious" preference unless the user expresses
        # it as a stable constraint.
        msg_lower = (request.message or "").lower()
        filtered_extracted: list[str] = []
        for pref in extracted_preferences or []:
            if not isinstance(pref, str) or not pref.strip():
                continue

            pref_lower = pref.strip().lower()
            if pref_lower == "budget conscious":
                stable_budget = bool(
                    re.search(
                        r"\b(on\s+a\s+budget|tight\s+budget|budget[-\s]?friendly|budget[-\s]?conscious|as\s+cheap\s+as\s+possible|cheapest\s+possible)\b",
                        msg_lower,
                    )
                )
                if not stable_budget:
                    continue

            filtered_extracted.append(pref)

        extracted_preferences = filtered_extracted
        
        # Store extracted preferences in mem0 if any were found
        from memory_manager import memory_manager
        if extracted_preferences:
            for pref in extracted_preferences:
                pref_type = _infer_preference_memory_type(pref)

                # Always persist to DB for deterministic Active Preferences.
                try:
                    canonical = memory_manager._canonicalize_preference_text(
                        memory_manager._strip_preference_wrappers(pref)
                    )
                    storage.add_preference(user_id, pref_type, pref, canonical)
                except Exception as e:
                    print(f"[PREFS] Warning: failed to persist extracted preference to DB: {e}")

                if pref_type:
                    try:
                        memory_manager.add_structured_memory(
                            user_id=user_id,
                            category="preference",
                            content=pref,
                            memory_type=pref_type,
                            metadata={"extracted_at": datetime.now().isoformat(), "source": "chat_extraction"},
                        )
                    except Exception as e:
                        print(f"[PREFS] Warning: failed to persist extracted preference to mem0: {e}")
                else:
                    try:
                        memory_manager.store_preference(user_id, "general", pref)
                    except Exception as e:
                        print(f"[PREFS] Warning: failed to store general preference to mem0: {e}")
        
        response_message = ChatMessageModel(
            id=str(uuid.uuid4()),
            role="assistant",
            content=result["content"],
            timestamp=datetime.now().isoformat(),
            flightResults=result.get("flight_results", []),
            memoryContext=result.get("memory_context"),
            appliedPrefs=result.get("applied_prefs_summary"),
            travelHistory=result.get("travel_history"),
        )

        # Add messages to conversation
        storage.add_message(conversation_id, {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat(),
        })
        storage.add_message(conversation_id, response_message.model_dump())

        return JSONResponse(
            status_code=200,
            content={
                "message": response_message.model_dump(),
                "conversationId": conversation_id,
                "extractedPreferences": extracted_preferences
            }
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

@app.put("/api/conversations/{conversation_id}/rename")
async def rename_conversation(conversation_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_title = body.get("title", "")
    if not new_title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    
    updated = storage.rename_conversation(conversation_id, new_title)
    return ConversationModel(**updated)

@app.put("/api/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    archived = body.get("archived", False)
    updated = storage.archive_conversation(conversation_id, archived)
    return ConversationModel(**updated)

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    conversation = storage.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    storage.delete_conversation(conversation_id)
    return {"message": "Conversation deleted"}

@app.delete("/api/conversations")
async def delete_all_conversations(request_body: DeleteAllConversationsRequest, current_user: dict = Depends(get_current_user)):
    """Delete all conversations for the current user and optionally their preferences."""
    from memory_manager import memory_manager
    try:
        user_id = current_user["id"]
        delete_preferences = request_body.deletePreferences
        
        print(f"\n[DELETE ALL] Starting deletion for user {user_id}")
        print(f"[DELETE ALL] deletePreferences flag: {delete_preferences}")
        
        # Get all conversations for this user
        conversations = storage.get_user_conversations(user_id)
        print(f"[DELETE ALL] Found {len(conversations)} conversations to delete")
        
        # Delete each conversation
        deleted_count = 0
        for conv in conversations:
            conv_id = conv.get("id") if isinstance(conv, dict) else conv.id
            print(f"[DELETE ALL] Deleting conversation {conv_id}")
            result = storage.delete_conversation(conv_id)
            if result:
                deleted_count += 1
            else:
                print(f"[DELETE ALL] Failed to delete conversation {conv_id}")
        
        print(f"[DELETE ALL] Successfully deleted {deleted_count} conversations")
        
        # Optionally delete all preferences
        if delete_preferences:
            try:
                print(f"[DELETE ALL] Clearing all preferences for user {user_id}")
                # 1) Clear DB-backed preferences (Active Preferences source of truth)
                db_rows = storage.list_preferences(user_id) or []
                db_deleted = 0
                for r in db_rows:
                    # Delete by both raw and canonical forms (if present)
                    raw = (r.get("raw") or "").strip()
                    canonical = (r.get("canonical") or "").strip()
                    for txt in [raw, canonical]:
                        if not txt:
                            continue
                        try:
                            res = storage.delete_preference(user_id, txt)
                            if isinstance(res, dict) and res.get("success"):
                                db_deleted += int(res.get("deleted") or 0)
                        except Exception as e:
                            print(f"[DELETE ALL] Warning: failed to delete DB pref '{txt}': {e}")

                print(f"[DELETE ALL] Deleted {db_deleted} DB preference row(s)")

                # 2) Best-effort clear mem0 preferences (fallback memory layer)
                result = memory_manager.clear_all_preferences(user_id)
                print(f"[DELETE ALL] Clear mem0 preferences result: {result}")
            except Exception as e:
                print(f"[CLEANUP ERROR] Error deleting preferences for user {user_id}: {e}")
                import traceback
                traceback.print_exc()
        
        response_msg = f"Deleted {deleted_count} conversations"
        if delete_preferences:
            response_msg += " and all preferences"
        
        print(f"[DELETE ALL] Completed: {response_msg}\n")
        
        return {
            "success": True,
            "message": response_msg,
            "deleted_count": deleted_count
        }
    except Exception as e:
        print(f"[DELETE ALL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error deleting conversations: {str(e)}")

# ==================== Memory/Preferences API ====================
@app.get("/api/memory/preferences")
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    """Get user's stored travel preferences."""
    from memory_manager import memory_manager
    try:
        user_id = current_user["id"]
        preferences = memory_manager.summarize_preferences(user_id, include_ids=True) or {}

        # Always merge DB preferences in so Active Preferences is deterministic.
        try:
            db_rows = storage.list_preferences(user_id)
            latest_db_by_type: dict[str, dict] = {}
            for r in db_rows or []:
                t = r.get("type") or "other"
                if t not in latest_db_by_type:
                    latest_db_by_type[t] = r

            for r in db_rows:
                raw = r.get("raw")
                canonical = r.get("canonical") or raw
                pref_type = r.get("type")
                key = pref_type or "other"

                preferences.setdefault(key, [])
                existing = preferences.get(key) or []

                def _to_text(x):
                    if isinstance(x, str):
                        return x
                    if isinstance(x, dict):
                        return x.get("text") or x.get("memory")
                    return str(x)

                existing_texts = {(_to_text(x) or "").strip().lower() for x in existing}
                candidate_texts = {(canonical or "").strip().lower(), (raw or "").strip().lower()}
                if any(t and t in existing_texts for t in candidate_texts):
                    continue

                existing.append({"id": r.get("id"), "text": canonical, "memory": raw})
                preferences[key] = existing
        except Exception as e:
            print(f"[PREFS] DB merge failed: {e}")

        # Mutually exclusive preference types: DB latest wins (single item)
        try:
            for t in ["cabin_class", "departure_time", "trip_type", "passenger"]:
                row = None
                try:
                    row = latest_db_by_type.get(t)  # type: ignore[name-defined]
                except Exception:
                    row = None
                if row:
                    raw = row.get("raw")
                    canonical = row.get("canonical") or raw
                    preferences[t] = [{"id": row.get("id"), "text": canonical, "memory": raw}]
                else:
                    # If no DB value, at least avoid showing multiple conflicting values.
                    if isinstance(preferences.get(t), list) and len(preferences.get(t) or []) > 1:
                        preferences[t] = [preferences[t][0]]
        except Exception as e:
            print(f"[PREFS] Warning: failed to normalize exclusive preferences: {e}")
        
        # Filter out "general" type preferences (they shouldn't exist with new code, but clean up old ones)
        if "general" in preferences:
            preferences.pop("general", None)

        # Keep Active Preferences actionable and non-redundant.
        # - Hide & cleanup generic "luxury" travel-style entries.
        # - Avoid duplicate passenger prefs by moving them out of "other".
        def _pref_text(x) -> str:
            if isinstance(x, str):
                return x
            if isinstance(x, dict):
                return (x.get("text") or x.get("memory") or "")
            return str(x)

        passenger_markers = [
            "travel: solo",
            "traveling alone",
            "travelling alone",
            "solo",
            "with family",
            "travel: with family",
            "with partner",
            "travel: with partner",
        ]

        # First, drop luxury anywhere it appears.
        # Also proactively delete from DB so it won't come back.
        luxury_candidates: list[str] = []
        try:
            for r in (db_rows or []):
                raw = (r.get("raw") or "")
                canonical = (r.get("canonical") or "")
                if "luxury" in raw.lower():
                    luxury_candidates.append(raw)
                if canonical and "luxury" in canonical.lower():
                    luxury_candidates.append(canonical)
        except Exception:
            luxury_candidates = []

        if luxury_candidates:
            # Deduplicate while preserving order
            seen_lux = set()
            unique_lux = []
            for t in luxury_candidates:
                tl = (t or "").strip().lower()
                if not tl or tl in seen_lux:
                    continue
                seen_lux.add(tl)
                unique_lux.append(t)

            print(f"[PREFS CLEANUP] Removing {len(unique_lux)} luxury preference(s) from DB/mem0")
            for txt in unique_lux:
                try:
                    storage.delete_preference(user_id, txt)
                except Exception as e:
                    print(f"[PREFS CLEANUP] DB delete failed for '{txt}': {e}")
                try:
                    memory_manager.remove_preference(user_id, txt)
                except Exception:
                    pass

        for k in list(preferences.keys()):
            items = preferences.get(k) or []
            filtered = []
            for item in items:
                t = _pref_text(item).strip().lower()
                if "luxury" in t:
                    continue
                filtered.append(item)
            preferences[k] = filtered
            if not preferences[k]:
                preferences.pop(k, None)

        # Then, move passenger-like entries out of "other".
        other_items = preferences.get("other") or []
        if other_items:
            passenger_bucket = preferences.get("passenger") or []
            passenger_texts = {_pref_text(x).strip().lower() for x in passenger_bucket}
            kept_other = []
            for item in other_items:
                t = _pref_text(item).strip().lower()
                if any(m in t for m in passenger_markers):
                    if t and t not in passenger_texts:
                        passenger_bucket.append(item)
                        passenger_texts.add(t)
                    continue
                kept_other.append(item)
            if passenger_bucket:
                preferences["passenger"] = passenger_bucket
            preferences["other"] = kept_other
            if not preferences["other"]:
                preferences.pop("other", None)
        
        return {
            "userId": current_user["id"],
            "preferences": preferences,
            "count": sum(len(v) for v in preferences.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving preferences: {str(e)}")

@app.post("/api/memory/preferences/merged")
async def get_merged_preferences(
    body: dict,
    current_user: dict = Depends(get_current_user)
):
    """Get merged preferences (stored + current UI state) - shows what the AI actually uses."""
    from memory_manager import memory_manager
    from agent import _merge_preferences
    try:
        # Get stored preferences from mem0
        stored_prefs = memory_manager.summarize_preferences(current_user["id"], include_ids=True)
        
        # Get current UI preferences from request
        current_prefs = body.get("currentPreferences", {})
        
        # Merge them (this is what the AI sees)
        merged = _merge_preferences(stored_prefs, current_prefs)
        
        return {
            "userId": current_user["id"],
            "merged": merged,
            "stored": stored_prefs,
            "current": current_prefs,
            "count": sum(len(v) for v in merged.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error merging preferences: {str(e)}")

@app.get("/api/memory/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get comprehensive user profile including all memories and preferences."""
    from memory_manager import memory_manager
    try:
        profile = memory_manager.get_full_user_profile(current_user["id"])
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")

@app.post("/api/memory/add-preference")
async def add_preference(request: dict, current_user: dict = Depends(get_current_user)):
    """Add a new preference entry to user's memory."""
    from memory_manager import memory_manager
    try:
        user_id = current_user["id"]
        category = request.get("category", "preference")
        content = request.get("content")
        memory_type = request.get("type")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # mem0 is best-effort; DB persistence is the source of truth for UI.
        result: dict = {}
        try:
            result = memory_manager.add_structured_memory(
                user_id=user_id,
                category=category,
                content=content,
                memory_type=memory_type,
                metadata=request.get("metadata")
            )
        except Exception as e:
            print(f"[PREFS] Warning: failed to persist preference to mem0: {e}")

        # Always persist to DB so Active Preferences is deterministic.
        canonical = memory_manager._canonicalize_preference_text(
            memory_manager._strip_preference_wrappers(content)
        )
        db_row = storage.add_preference(user_id, memory_type, content, canonical)
        if isinstance(db_row, dict) and db_row.get("error"):
            raise HTTPException(status_code=500, detail=db_row.get("error"))
        
        return {
            "success": True,
            "memory_id": result.get("id"),
            "db_id": (db_row or {}).get("id") if isinstance(db_row, dict) else None,
            "content": content,
            "category": category,
            "type": memory_type
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding preference: {str(e)}")

@app.delete("/api/memory/preferences/{preference_text}")
async def delete_preference(preference_text: str, current_user: dict = Depends(get_current_user)):
    """Delete a user's preference by text."""
    from memory_manager import memory_manager
    try:
        user_id = current_user["id"]
        print(f"[DELETE PREF] Attempting to delete preference: '{preference_text}' for user {user_id}")
        canonical = memory_manager._canonicalize_preference_text(
            memory_manager._strip_preference_wrappers(preference_text)
        )

        db_deleted = False
        try:
            db_result = storage.delete_preference(user_id, preference_text)
            if db_result.get("success"):
                db_deleted = True
            if canonical and canonical != preference_text:
                db_result2 = storage.delete_preference(user_id, canonical)
                if db_result2.get("success"):
                    db_deleted = True
        except Exception as e:
            print(f"[PREFS] Warning: failed to delete preference from DB: {e}")

        mem0_deleted = False
        mem0_result: dict = {}
        try:
            mem0_result = memory_manager.remove_preference(user_id, preference_text)
            mem0_deleted = bool(mem0_result.get("success"))
        except Exception as e:
            print(f"[PREFS] Warning: failed to delete preference from mem0: {e}")

        if db_deleted or mem0_deleted:
            deleted_id = mem0_result.get("deleted_id") if isinstance(mem0_result, dict) else None
            print(f"[DELETE PREF] Successfully deleted preference: '{preference_text}' (db={db_deleted}, mem0={mem0_deleted})")
            return {
                "success": True,
                "message": f"Preference removed successfully",
                "deletedPreference": preference_text,
                "deletedId": deleted_id
            }
        else:
            raise HTTPException(status_code=404, detail="Preference not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE PREF] Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting preference: {str(e)}")

# ==================== Travel History ====================
@app.post("/api/memory/record-booking")
async def record_booking(request: dict, current_user: dict = Depends(get_current_user)):
    """Record a booked flight."""
    from memory_manager import memory_manager
    try:
        # 1) Persist deterministically to DB so travel history always shows all bookings.
        try:
            storage.add_booking(current_user["id"], request)
        except Exception as e:
            # Don't fail booking recording if DB persistence fails; mem0 still acts as a fallback.
            print(f"[BOOKING] Warning: failed to persist booking to DB: {e}")

        # 2) Also record to mem0 for preference/memory features.
        result = memory_manager.record_booked_flight(current_user["id"], request)
        return {"success": "error" not in result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording booking: {str(e)}")

@app.get("/api/memory/travel-history")
async def get_travel_history(current_user: dict = Depends(get_current_user)):
    """Get user's travel history."""
    from memory_manager import memory_manager
    try:
        # Prefer DB-backed travel history (complete, ordered), fallback to mem0 if empty.
        history = storage.list_bookings(current_user["id"]) or memory_manager.get_travel_history(current_user["id"])
        print(f"[HISTORY] Retrieved {len(history)} travel history items")
        for i, booking in enumerate(history):
            print(f"[HISTORY] Booking {i+1}: {booking.get('memory', '')}")
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

# ==================== Run Server ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PYTHON_BACKEND_PORT,
        log_level="info",
    )
