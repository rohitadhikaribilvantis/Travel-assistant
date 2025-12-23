import os
import re
from typing import Optional, List, Dict, Literal
from datetime import datetime

from database import DatabaseStorage

# Memory Schema Types
PreferenceType = Literal["seat", "airline", "departure_time", "flight_type", "cabin_class", "red_eye", "baggage"]
MemoryCategory = Literal["preference", "travel_history", "route", "airline", "budget"]

_db_storage = DatabaseStorage()

class TravelMemory:
    """Standard schema for travel memories."""
    
    def __init__(
        self,
        user_id: str,
        category: MemoryCategory,
        content: str,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.user_id = user_id
        self.category = category
        self.content = content
        self.memory_type = memory_type
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
    
    def to_message_format(self) -> Dict:
        """Convert to mem0 message format."""
        return {
            "role": "user",
            "content": self.format_message()
        }
    
    def format_message(self) -> str:
        """Format memory as natural language for mem0."""
        if self.category == "preference":
            # Only show type if it's not "general" (general is unhelpful)
            if self.memory_type and self.memory_type != "general":
                return f"Travel Preference: {self.content} (Type: {self.memory_type})"
            else:
                return f"Travel Preference: {self.content}"
        elif self.category == "travel_history":
            return f"Travel History: {self.content}"
        elif self.category == "route":
            return f"Frequent Route: {self.content}"
        elif self.category == "airline":
            return f"Airline Experience: {self.content}"
        elif self.category == "budget":
            return f"Budget Preference: {self.content}"
        return f"{self.category.title()}: {self.content}"


class TravelMemoryManager:
    """Manages user travel preferences and history using mem0."""
    
    def __init__(self):
        self._memory = None
        self._initialized = False
    
    def _get_memory(self):
        """Lazy initialization of mem0 to avoid startup delays."""
        if not self._initialized:
            try:
                from mem0 import MemoryClient
                
                mem0_api_key = os.environ.get("MEM0_API_KEY")
                
                if not mem0_api_key:
                    print("Warning: MEM0_API_KEY not set in environment")
                    self._memory = None
                    self._initialized = True
                    return None
                
                self._memory = MemoryClient(api_key=mem0_api_key)
                self._initialized = True
            except Exception as e:
                print(f"Warning: Could not initialize mem0: {e}")
                self._memory = None
                self._initialized = True
        return self._memory
    
    def get_user_memories(self, user_id: str, query: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Retrieve user memories, optionally filtered by a search query.
        
        Args:
            user_id: The user identifier
            query: Optional search query to filter memories
            
        Returns:
            List of memory dictionaries
        """
        memory = self._get_memory()
        if not memory:
            print(f"[MEMORY] Memory client not initialized for user {user_id}")
            return []

        try:
            # MemoryClient requires filters parameter with user_id
            filters = {"user_id": user_id}

            if query:
                print(f"[MEMORY] Searching for '{query}' for user {user_id}")
                # Some mem0 client versions support a `limit`/`top_k` style argument.
                # Try to request more results to avoid only returning the top few hits.
                try:
                    results = memory.search(query, filters=filters, limit=limit)
                except TypeError:
                    results = memory.search(query, filters=filters)
            else:
                # If no query, search for generic terms to get all preferences
                print(f"[MEMORY] Getting all memories for user {user_id} via search")
                search_query = "preference flight cabin class time depart airline seat travel"
                try:
                    results = memory.search(search_query, filters=filters, limit=limit)
                except TypeError:
                    results = memory.search(search_query, filters=filters)

            print(f"[MEMORY] Search results: {results}")

            # MemoryClient.search() returns {"results": [memory_list]}
            if isinstance(results, dict):
                memories = results.get("results", [])
            else:
                memories = results if isinstance(results, list) else []

            # Filter out explicitly-marked "Type: General" wrapper text.
            # Do NOT filter on mem0's internal `type` field; some mem0 versions
            # label many/all memories as type="general", which would hide valid preferences.
            filtered_memories = [
                m for m in memories
                if not (isinstance(m, dict) and "Type: General" in str(m.get("memory", "")))
            ]

            # Clean up memory text by removing " for general" suffix
            for mem in filtered_memories:
                if isinstance(mem, dict) and "memory" in mem:
                    mem["memory"] = mem["memory"].replace(" for general", "").strip()

            print(f"[MEMORY] Retrieved {len(filtered_memories)} memories for user {user_id} (filtered from {len(memories)})")
            if filtered_memories:
                print(f"[MEMORY] Sample memory structure: {filtered_memories[0] if filtered_memories else 'None'}")
            return filtered_memories
        except Exception as e:
            print(f"[MEMORY ERROR] Error retrieving memories for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def add_memory(self, user_id: str, messages: List[Dict]) -> Dict:
        """
        Add new memories from conversation messages.
        
        Args:
            user_id: The user identifier
            messages: List of conversation messages
            
        Returns:
            Result of memory addition
        """
        memory = self._get_memory()
        if not memory:
            print(f"[MEMORY ERROR] mem0 not available, cannot add memory for user {user_id}")
            return {"error": "Memory system not available"}
        
        try:
            print(f"[MEMORY] Adding {len(messages)} message(s) to memory for user {user_id}")
            print(f"[MEMORY] Messages: {messages}")
            result = memory.add(messages, user_id=user_id)
            print(f"[MEMORY] Successfully added memory, result: {result}")
            print(f"[MEMORY] Result type: {type(result)}, Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
            return {"success": True, "result": result}
        except Exception as e:
            print(f"[MEMORY ERROR] Error adding memory for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def store_preference(self, user_id: str, preference_type: str, preference_value: str):
        """
        Store a specific travel preference.
        
        Args:
            user_id: The user identifier
            preference_type: Type of preference (seat, airline, time, flight_type, cabin_class, etc.)
            preference_value: The preference value
        """
        print(f"[MEMORY] Storing preference for user {user_id}: type={preference_type}, value={preference_value}")
        message = f"Preference: {preference_type} - {preference_value}"
        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"I've noted that you prefer {preference_value} for {preference_type}."}
        ]
        result = self.add_memory(user_id, messages)
        print(f"[MEMORY] Store preference result: {result}")
        return result
    
    def store_travel_history(self, user_id: str, flight_details: Dict):
        """
        Store a completed flight booking/travel.
        
        Args:
            user_id: The user identifier
            flight_details: Dictionary with flight booking information
        """
        message = f"Traveled: {flight_details.get('route', 'Unknown route')} on {flight_details.get('airline', 'Unknown airline')} on {flight_details.get('date', 'Unknown date')}"
        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"I've recorded your flight from {flight_details.get('origin')} to {flight_details.get('destination')} on {flight_details.get('date')}."}
        ]
        return self.add_memory(user_id, messages)
    
    def get_preferences_summary(self, user_id: str) -> str:
        """
        Get a formatted summary of user travel preferences.

        Args:
            user_id: The user identifier

        Returns:
            Formatted preference summary string
        """
        try:
            # Expanded query to include more potential preference keywords
            preference_memories = self.get_user_memories(
                user_id, query="travel preferences seat airline time cabin class red_eye baggage trip_type"
            )

            if not preference_memories:
                return "No preferences set."

            preference_parts = []
            for mem in preference_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if memory_text:
                    preference_parts.append(f"- {memory_text}")

            if preference_parts:
                return "Known user preferences and travel patterns:\n" + "\n".join(preference_parts)

            return "No preferences set."
        except Exception as e:
            print(f"Error getting preferences summary: {e}")
            return "Error retrieving preferences."
    
    def get_user_context(self, user_id: str) -> str:
        """
        Get comprehensive user context for agent decision-making.
        
        Returns formatted context about user preferences, history, and patterns.
        """
        try:
            # Get all memories
            memories = self.get_user_memories(user_id)
            print(f"[CONTEXT] Retrieved {len(memories)} memories for user {user_id}")
            
            if not memories:
                print(f"[CONTEXT] No memories found for user {user_id}")
                return ""
            
            preferences = []
            travel_history = []
            
            for mem in memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if not memory_text:
                    continue
                
                # Clean up " for general" suffix from memory text
                memory_text = memory_text.replace(" for general", "").strip()
                
                # Skip "general" type preferences
                if "Type: General" in memory_text or memory_text.startswith("Travel Preference Type:"):
                    print(f"[CONTEXT] Skipping general preference: '{memory_text}'")
                    continue
                    
                if "preference" in memory_text.lower() or any(word in memory_text.lower() for word in ["prefer", "like", "avoid", "hate", "always", "never"]):
                    preferences.append(memory_text)
                elif any(word in memory_text.lower() for word in ["traveled", "booked", "flight"]):
                    travel_history.append(memory_text)
                else:
                    preferences.append(memory_text)
            
            print(f"[CONTEXT] Found {len(preferences)} preferences and {len(travel_history)} travel history items")
            
            context_parts = []
            
            if preferences:
                context_parts.append("USER PREFERENCES AND PATTERNS:")
                context_parts.extend([f"- {p}" for p in preferences])
            
            if travel_history:
                context_parts.append("\nTRAVEL HISTORY:")
                context_parts.extend([f"- {h}" for h in travel_history])
            
            result = "\n".join(context_parts) if context_parts else ""
            print(f"[CONTEXT] Final context: {result}")
            return result
        except Exception as e:
            print(f"[CONTEXT ERROR] Error getting user context: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def extract_and_store_preferences(self, user_id: str, user_message: str, assistant_response: str):
        """
        Extract and store preferences from a conversation turn.
        
        Args:
            user_id: The user identifier
            user_message: The user's message
            assistant_response: The assistant's response
        """
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ]
        
        preference_keywords = [
            "prefer", "always", "never", "hate", "love", "like",
            "favorite", "usually", "avoid", "only", "direct flights",
            "business class", "economy", "premium economy", "first class",
            "window seat", "aisle seat", "middle seat", "exit row",
            "morning", "evening", "afternoon", "red-eye", "airline",
            "layover", "non-stop", "direct", "baggage", "solo", "family",
            "partner", "budget"
        ]
        
        should_store = any(kw in user_message.lower() for kw in preference_keywords)
        
        if should_store:
            self.add_memory(user_id, messages)
        
        return should_store
    
    def add_structured_memory(
        self,
        user_id: str,
        category: MemoryCategory,
        content: str,
        memory_type: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add a structured memory entry with consistent schema.
        
        Args:
            user_id: User identifier
            category: Category of memory (preference, travel_history, route, airline, budget)
            content: Memory content
            memory_type: Optional specific type (e.g., 'seat', 'airline' for preferences)
            metadata: Optional additional metadata
            
        Returns:
            Result of memory addition
        """
        memory = TravelMemory(user_id, category, content, memory_type, metadata)
        messages = [memory.to_message_format()]
        
        result = self.add_memory(user_id, messages)
        
        if result and "error" not in result:
            result["category"] = category
            result["memory_type"] = memory_type
            result["created_at"] = memory.created_at
        
        return result
    
    def get_preference_memories(self, user_id: str) -> List[Dict]:
        """Get all preference-related memories for a user."""
        return self.get_user_memories(user_id, query="travel preferences seat airline time cabin")
    
    def record_duration_preference(self, user_id: str, duration_hours: int, trip_type: str) -> Dict:
        """Record observed duration preferences from bookings."""
        try:
            duration_days = duration_hours / 24 if duration_hours else 0
            return self.add_structured_memory(
                user_id=user_id,
                category="travel_history",
                content=f"Preferred trip duration: {int(duration_days)} days for {trip_type} trips",
                memory_type="duration_preference",
                metadata={
                    "duration_hours": duration_hours,
                    "duration_days": duration_days,
                    "trip_type": trip_type,
                    "recorded_at": datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            print(f"Error recording duration preference: {e}")
            return {"error": str(e)}
    
    def get_travel_history(self, user_id: str) -> List[Dict]:
        """Get travel history memories for a user."""
        try:
            # Use a travel-history focused query and a higher limit so older bookings aren't dropped
            # due to the underlying semantic search returning only a small top set.
            memories = self.get_user_memories(
                user_id,
                query="travel history booked flight booking traveled journey",
                limit=100,
            )
            if not memories:
                return []
            
            # Filter to only include booked flights, not searches or other travel-related memories
            booked_flights: List[Dict] = []
            for m in memories:
                if not (m and isinstance(m, dict)):
                    continue

                memory_text = m.get("memory", "")
                memory_text_lower = memory_text.lower()

                # Accept common travel-history formats:
                # - Explicit "booked" keyword (new format)
                # - Route arrow format (e.g. "IAH → NRT")
                # - Natural language "from IAH to NRT" with airline mention (older memories)
                is_booked = "booked" in memory_text_lower
                has_route_arrow = "→" in memory_text
                is_from_to_airline = (
                    " from " in memory_text_lower
                    and " to " in memory_text_lower
                    and ("airline" in memory_text_lower or "airlines" in memory_text_lower)
                )

                if is_booked or has_route_arrow or is_from_to_airline:
                    booked_flights.append(m)
            return booked_flights
        except Exception as e:
            print(f"[ERROR] Error getting travel history: {e}")
            return []
    
    def get_favorite_routes(self, user_id: str) -> List[Dict]:
        """Get frequently traveled routes for a user."""
        return self.get_user_memories(user_id, query="route origin destination frequently")
    
    def get_airline_preferences(self, user_id: str) -> List[Dict]:
        """Get airline-specific memories and preferences."""
        return self.get_user_memories(user_id, query="airline carrier prefer avoid")
    
    def get_budget_preferences(self, user_id: str) -> List[Dict]:
        """Get budget and pricing preferences."""
        return self.get_user_memories(user_id, query="budget price cost expensive cheap")

    @staticmethod
    def _strip_preference_wrappers(memory_text: str) -> str:
        text = (memory_text or "").strip()
        # Remove common wrappers added by our own memory formatting.
        text = re.sub(r"^\s*(travel\s+preference|preference)\s*:\s*", "", text, flags=re.IGNORECASE)
        # Remove trailing type annotation wrapper.
        text = re.sub(r"\s*\(\s*type\s*:\s*[^)]+\)\s*$", "", text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def _canonicalize_preference_text(core_text: str) -> str:
        """Convert verbose/free-form preference sentences into canonical labels."""
        t = (core_text or "").strip()
        lower = t.lower()

        # Cabin class
        cabin = None
        if "premium economy" in lower or ("premium" in lower and "economy" in lower):
            cabin = "Premium Economy"
        elif "business" in lower:
            cabin = "Business"
        elif "first" in lower:
            cabin = "First"
        elif "economy" in lower:
            cabin = "Economy"
        if cabin and ("class" in lower or "cabin" in lower or "flights" in lower):
            return f"Cabin class: {cabin}"

        # Trip type
        if "one-way" in lower or "one way" in lower:
            return "Trip type: One-way"
        if "round trip" in lower or "round-trip" in lower or "return" in lower:
            return "Trip type: Round trip"

        # Stops / flight type
        if "nonstop" in lower or "non-stop" in lower or "direct" in lower:
            return "Stops: Direct only"
        if "layover" in lower or "stopover" in lower or "stops" in lower:
            if any(kw in lower for kw in ["avoid", "no ", "without", "hate"]):
                return "Stops: Avoid layovers"
            if any(kw in lower for kw in ["ok", "okay", "fine", "don't mind", "dont mind", "willing"]):
                return "Stops: Layovers OK"

        # Departure time
        negative = any(kw in lower for kw in ["hate", "avoid", "don't like", "dont like", "do not like", "no ", "never"])
        if "morning" in lower:
            return "Departure time: Avoid morning" if negative else "Departure time: Morning"
        if "afternoon" in lower:
            return "Departure time: Avoid afternoon" if negative else "Departure time: Afternoon"
        if "evening" in lower:
            return "Departure time: Avoid evening" if negative else "Departure time: Evening"

        # Red-eye
        if "red-eye" in lower or "red eye" in lower:
            if any(kw in lower for kw in ["avoid", "no ", "never", "hate"]):
                return "Red-eye: Avoid"
            return "Red-eye: Prefer to avoid"

        # Seats
        if "window" in lower:
            return "Seat: Window"
        if "aisle" in lower:
            return "Seat: Aisle"
        if "exit row" in lower:
            return "Seat: Exit row"
        if "middle" in lower or "center" in lower:
            if any(kw in lower for kw in ["avoid", "no ", "never", "hate", "don't like", "dont like"]):
                return "Seat: Avoid middle"

        # Baggage
        if "carry-on" in lower or "cabin baggage" in lower:
            return "Baggage: Carry-on only"
        if "checked" in lower:
            return "Baggage: Checked bag"
        if "extra baggage" in lower:
            return "Baggage: Extra baggage"

        # Passenger
        if "traveling alone" in lower or "travelling alone" in lower or "solo" in lower:
            return "Travel: Solo"
        if "with family" in lower or "kids" in lower or "children" in lower:
            return "Travel: With family"
        if "with partner" in lower or "spouse" in lower:
            return "Travel: With partner"

        # Airline: keep as-is (too many variations); just strip leading phrasing.
        t = re.sub(r"^\s*i\s+(prefer|like|love|want|need)\s+", "", t, flags=re.IGNORECASE).strip()
        return t
    
    def summarize_preferences(self, user_id: str, include_ids: bool = False) -> Dict:
        """
        Get a structured summary of all user preferences.
        
        Returns a dictionary with categorized preferences.
        If include_ids is True, returns objects with 'id', 'text', and 'memory' fields.
        """
        try:
            # Use a preference-focused query to avoid missing preferences due to
            # semantic search returning only a narrow top set.
            all_memories = self.get_user_memories(
                user_id,
                query=(
                    "travel preference preferences seat window aisle airline carrier "
                    "cabin class economy premium business first direct non-stop layover stops "
                    "departure time morning afternoon evening red-eye red eye redeye baggage luggage "
                    "one-way one way round trip round-trip"
                ),
                limit=150,
            )
            print(f"[MEMORY] Raw memories retrieved: {all_memories}")
            
            summary = {
                "seat": [],
                "airline": [],
                "departure_time": [],
                "flight_type": [],
                "cabin_class": [],
                "red_eye": [],
                "trip_type": [],
                "passenger": [],
                "baggage": [],
                "routes": [],
                "budget": [],
                "location": [],
                "other": []
            }
            
            seen_by_category: Dict[str, set] = {k: set() for k in summary.keys()}

            for mem in all_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if not memory_text:
                    continue
                
                # Clean up " for general" suffix
                memory_text = memory_text.replace(" for general", "").strip()
                
                # Skip "general" type preferences (old/confusing entries)
                if "Type: General" in memory_text or memory_text.startswith("Travel Preference Type:"):
                    print(f"[MEMORY] Skipping general preference: '{memory_text}'")
                    continue
                
                memory_id = mem.get("id", None) if isinstance(mem, dict) else None
                memory_lower = memory_text.lower()
                
                # IMPORTANT: Skip bookings and searches - they go in travel_history, not preferences!
                if "booked" in memory_lower or "user booked" in memory_lower:
                    print(f"[MEMORY] Skipping booking (not a preference): '{memory_text}'")
                    continue
                if "searched" in memory_lower or "user searched" in memory_lower:
                    print(f"[MEMORY] Skipping search (not a preference): '{memory_text}'")
                    continue
                if "traveled" in memory_lower or "user traveled" in memory_lower:
                    print(f"[MEMORY] Skipping travel history (not a preference): '{memory_text}'")
                    continue
                
                # Skip entries explicitly marked as travel history
                if "travel history entry" in memory_lower:
                    print(f"[MEMORY] Skipping travel history entry: '{memory_text}'")
                    continue
                
                # Skip memories that look like flight bookings (pattern: "from ABC to XYZ with AIRLINE in CLASS for CURRENCY PRICE")
                if re.search(r'from\s+[A-Z]{3}\s+to\s+[A-Z]{3}.*with\s+\w+.*(?:USD|EUR|GBP|\$)', memory_text, re.IGNORECASE):
                    print(f"[MEMORY] Skipping travel booking pattern (not a preference): '{memory_text}'")
                    continue
                
                # Skip entries with "flight from X to Y" pattern (another variant of flight booking)
                if re.search(r'flight\s+from\s+[A-Z]{3}\s+to\s+[A-Z]{3}', memory_text, re.IGNORECASE):
                    print(f"[MEMORY] Skipping flight booking format (flight from X to Y): '{memory_text}'")
                    continue
                
                # Skip memories that have arrow symbol with times/prices
                if ("→" in memory_text and ("pm" in memory_lower or "am" in memory_lower)) or (any(currency in memory_text for currency in ["USD", "EUR", "$", "GBP"]) and "→" in memory_text):
                    print(f"[MEMORY] Skipping flight booking pattern (not a preference): '{memory_text}'")
                    continue
                
                # Produce a canonical display string, but preserve the raw memory for deletion.
                core_text = self._strip_preference_wrappers(memory_text)
                display_text = self._canonicalize_preference_text(core_text)
                display_lower = display_text.lower()

                # Create entry (with or without ID)
                if include_ids:
                    entry = {"id": memory_id, "text": display_text, "memory": memory_text}
                else:
                    entry = display_text
                
                print(f"[MEMORY] Processing memory: '{memory_text}' (lower: '{memory_lower}')")
                
                # Categorize the memory - Check cabin class FIRST since it's most specific
                if any(word in display_lower for word in ["business", "economy", "premium", "first"]) and any(word in display_lower for word in ["class", "cabin"]):
                    print(f"  -> Categorized as CABIN CLASS")
                    if display_lower not in seen_by_category["cabin_class"]:
                        seen_by_category["cabin_class"].add(display_lower)
                        summary["cabin_class"].append(entry)
                elif any(word in display_lower for word in ["red-eye", "red eye", "red-eye:"]):
                    print(f"  -> Categorized as RED EYE")
                    if display_lower not in seen_by_category["red_eye"]:
                        seen_by_category["red_eye"].add(display_lower)
                        summary["red_eye"].append(entry)
                elif any(word in display_lower for word in ["round trip", "one-way", "round-trip", "one way", "trip type:"]):
                    print(f"  -> Categorized as TRIP TYPE")
                    if display_lower not in seen_by_category["trip_type"]:
                        seen_by_category["trip_type"].add(display_lower)
                        summary["trip_type"].append(entry)
                elif any(word in display_lower for word in ["direct", "non-stop", "layover", "stop", "stops:"]):
                    print(f"  -> Categorized as FLIGHT TYPE")
                    if display_lower not in seen_by_category["flight_type"]:
                        seen_by_category["flight_type"].add(display_lower)
                        summary["flight_type"].append(entry)
                elif any(word in display_lower for word in ["morning", "afternoon", "evening", "depart", "departure time:"]):
                    print(f"  -> Categorized as TIME")
                    if display_lower not in seen_by_category["departure_time"]:
                        seen_by_category["departure_time"].add(display_lower)
                        summary["departure_time"].append(entry)
                elif any(word in display_lower for word in ["traveling alone", "solo", "travel alone", "fly alone", "traveling with family", "traveling with kids", "traveling with children", "traveling with partner", "traveling with spouse", "family trip", "travel:"]):
                    print(f"  -> Categorized as PASSENGER")
                    if display_lower not in seen_by_category["passenger"]:
                        seen_by_category["passenger"].add(display_lower)
                        summary["passenger"].append(entry)
                elif any(word in display_lower for word in ["seat", "window", "aisle", "middle", "exit row", "seat:"]):
                    print(f"  -> Categorized as SEAT")
                    if display_lower not in seen_by_category["seat"]:
                        seen_by_category["seat"].add(display_lower)
                        summary["seat"].append(entry)
                elif any(word in display_lower for word in ["airline", "carrier", "united", "delta", "american", "southwest", "jetblue", "alaska", "spirit", "frontier"]):
                    print(f"  -> Categorized as AIRLINE")
                    if display_lower not in seen_by_category["airline"]:
                        seen_by_category["airline"].add(display_lower)
                        summary["airline"].append(entry)
                elif any(word in display_lower for word in ["baggage", "luggage", "bag", "carry-on", "checked", "baggage:"]):
                    print(f"  -> Categorized as BAGGAGE")
                    if display_lower not in seen_by_category["baggage"]:
                        seen_by_category["baggage"].add(display_lower)
                        summary["baggage"].append(entry)
                elif any(word in display_lower for word in ["budget", "price", "cost"]) and "general" not in display_lower and "budget-conscious" not in display_lower:
                    # Only add specific budget preferences (e.g., "max $500"), skip generic "budget-conscious"
                    print(f"  -> Categorized as BUDGET")
                    if display_lower not in seen_by_category["budget"]:
                        seen_by_category["budget"].add(display_lower)
                        summary["budget"].append(entry)
                elif any(word in memory_lower for word in ["live", "based", "from", "home"]) and any(word in memory_lower for word in ["houston", "newyork", "los angeles", "london", "paris", "tokyo", "delhi", "mumbai", "kathmandu", "beijing", "chicago", "miami", "seattle", "boston", "denver", "dallas", "austin", "sanfrancisco"]):
                    print(f"  -> Categorized as LOCATION")
                    if display_lower not in seen_by_category["location"]:
                        seen_by_category["location"].add(display_lower)
                        summary["location"].append(entry)
                else:
                    print(f"  -> Categorized as OTHER")
                    if display_lower not in seen_by_category["other"]:
                        seen_by_category["other"].add(display_lower)
                        summary["other"].append(entry)
            
            print(f"[MEMORY] Final summary: {summary}")

            # Merge DB-backed preferences so preference reads are deterministic.
            try:
                db_rows = _db_storage.list_preferences(user_id) or []
                latest_db_by_type: dict[str, dict] = {}
                for r in db_rows:
                    t = r.get("type") or "other"
                    if t not in latest_db_by_type:
                        latest_db_by_type[t] = r

                for r in db_rows:
                    pref_type = (r.get("type") or "other").strip() if isinstance(r.get("type"), str) else (r.get("type") or "other")

                    raw = (r.get("raw") or "").strip()
                    canonical = (r.get("canonical") or "").strip()
                    display_text = canonical or raw
                    display_lower = (display_text or "").strip().lower()
                    if not display_lower:
                        continue

                    # Remap untyped/"other" passenger-like DB prefs into passenger bucket to avoid duplicates.
                    if pref_type in {"other", "general", ""}:
                        if any(k in display_lower for k in ["travel: solo", "traveling alone", "travelling alone", "solo", "with family", "travel: with family", "with partner", "travel: with partner"]):
                            pref_type = "passenger"

                    if pref_type not in summary:
                        summary[pref_type] = []
                    if pref_type not in seen_by_category:
                        seen_by_category[pref_type] = set()

                    if display_lower in seen_by_category[pref_type]:
                        continue

                    if include_ids:
                        entry = {"id": r.get("id"), "text": display_text, "memory": raw or display_text}
                    else:
                        entry = display_text

                    summary[pref_type].append(entry)
                    seen_by_category[pref_type].add(display_lower)

                # Mutually exclusive types: overwrite with DB latest only.
                for t in ["cabin_class", "departure_time", "trip_type", "passenger"]:
                    row = latest_db_by_type.get(t)
                    if not row:
                        continue
                    raw = (row.get("raw") or "").strip()
                    canonical = (row.get("canonical") or "").strip()
                    display_text = canonical or raw
                    if not display_text:
                        continue
                    if include_ids:
                        summary[t] = [{"id": row.get("id"), "text": display_text, "memory": raw or display_text}]
                    else:
                        summary[t] = [display_text]
            except Exception as e:
                print(f"[MEMORY] Warning: failed to merge DB preferences: {e}")

            # De-confuse redundant "travel style" entries.
            # Keep Active Preferences focused on actionable flight-search constraints.
            def _entry_text(v: object) -> str:
                if isinstance(v, dict):
                    return str(v.get("text") or v.get("memory") or "")
                return str(v or "")

            # Always hide generic "luxury" preferences (they're ambiguous + not actionable).
            for key in ["other", "budget"]:
                items = summary.get(key) or []
                filtered_items = []
                for item in items:
                    txt = _entry_text(item).lower()
                    if "luxury" in txt:
                        continue
                    filtered_items.append(item)
                summary[key] = filtered_items

            # Remove empty categories
            return {k: v for k, v in summary.items() if v}
        except Exception as e:
            print(f"Error summarizing preferences: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def record_booked_flight(self, user_id: str, flight_data: Dict) -> Dict:
        """Record a booked flight to travel history."""
        try:
            origin = flight_data.get("origin", "")
            destination = flight_data.get("destination", "")
            airline_name = flight_data.get("airline_name", flight_data.get("airline", ""))
            departure_date = flight_data.get("departure_date", "")
            departure_time = flight_data.get("departure_time", "")
            arrival_time = flight_data.get("arrival_time", "")
            trip_type = flight_data.get("trip_type", "")

            return_origin = flight_data.get("return_origin", "")
            return_destination = flight_data.get("return_destination", "")
            return_date = flight_data.get("return_date", "")
            return_departure_time = flight_data.get("return_departure_time", "")
            return_arrival_time = flight_data.get("return_arrival_time", "")
            cabin_class = flight_data.get("cabin_class", "")
            price = flight_data.get("price", "")
            currency = flight_data.get("currency", "USD")
            
            # Build natural language content.
            # Include "Booked flight" keywords so travel history retrieval can reliably detect these.
            content = f"Booked flight: {airline_name} {origin} → {destination}"
            if departure_date:
                content += f" on {departure_date}"
            if departure_time and arrival_time:
                content += f" ({departure_time} - {arrival_time})"

            is_round_trip = bool(trip_type and "round" in str(trip_type).lower()) or bool(return_date)
            if is_round_trip:
                content += " • Round Trip"
                if return_origin and return_destination:
                    content += f" | Return {return_origin} → {return_destination}"
                if return_date:
                    content += f" on {return_date}"
                if return_departure_time and return_arrival_time:
                    content += f" ({return_departure_time} - {return_arrival_time})"
            elif trip_type:
                content += f" • {trip_type}"

            if cabin_class:
                content += f" • {cabin_class}"
            if price:
                content += f" • {currency} {int(float(price))}"
            
            print(f"[BOOKING] Recording new booked flight for user {user_id}: {content}")
            
            result = self.add_structured_memory(
                user_id=user_id,
                category="travel_history",
                content=content,
                memory_type="booked_flight",
                metadata={
                    "origin": origin,
                    "destination": destination,
                    "airline": airline_name,
                    "departure_date": departure_date,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "trip_type": trip_type,
                    "return_origin": return_origin,
                    "return_destination": return_destination,
                    "return_date": return_date,
                    "return_departure_time": return_departure_time,
                    "return_arrival_time": return_arrival_time,
                    "cabin_class": cabin_class,
                    "price": price,
                    "currency": currency,
                    "booked_at": datetime.utcnow().isoformat()
                }
            )
            
            print(f"[BOOKING] Successfully recorded booking, result: {result}")
            
            # Now retrieve all bookings to verify
            all_bookings = self.get_user_memories(user_id, query="booked flight booking")
            booked_flights = [
                m for m in all_bookings
                if isinstance(m, dict) and "booked" in m.get("memory", "").lower()
            ]
            print(f"[BOOKING] Total bookings after recording: {len(booked_flights)}")
            for i, booking in enumerate(booked_flights):
                print(f"[BOOKING] Booking {i+1}: {booking.get('memory', '')}")
            
            return result
        except Exception as e:
            print(f"Error recording booked flight: {e}")
            return {"error": str(e)}
    
    def delete_memory(self, user_id: str, memory_id: str) -> Dict:
        """
        Delete a specific memory by ID.
        
        Args:
            user_id: The user identifier
            memory_id: The ID of the memory to delete
            
        Returns:
            Result of deletion
        """
        memory = self._get_memory()
        if not memory:
            print(f"[MEMORY ERROR] mem0 not available, cannot delete memory for user {user_id}")
            return {"error": "Memory system not available"}
        
        try:
            print(f"[MEMORY] Deleting memory {memory_id} for user {user_id}")
            # mem0's MemoryClient.delete() method only takes memory_id
            result = memory.delete(memory_id)
            print(f"[MEMORY] Delete result: {result}")
            return {"success": True, "result": result}
        except Exception as e:
            print(f"[MEMORY ERROR] Error deleting memory {memory_id} for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def clear_all_preferences(self, user_id: str) -> Dict:
        """
        Clear all preference-type memories for a user, keeping only travel history.
        
        Args:
            user_id: The user identifier
            
        Returns:
            Result with count of deleted preferences
        """
        print(f"[MEMORY] Clearing all preferences for user {user_id}")
        memory = self._get_memory()
        if not memory:
            print(f"[MEMORY ERROR] mem0 not available")
            return {"error": "Memory system not available"}
        
        try:
            # Get all memories
            all_memories = self.get_user_memories(user_id)
            print(f"[MEMORY] Found {len(all_memories)} total memories for user {user_id}")
            
            deleted_count = 0
            skipped_count = 0
            
            for mem in all_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                memory_id = mem.get("id") if isinstance(mem, dict) else None
                memory_lower = memory_text.lower() if memory_text else ""
                
                # Only keep travel history - skip everything else
                is_travel_history = (
                    "booked" in memory_lower or
                    "traveled" in memory_lower or
                    ("departure" in memory_lower and "date" in memory_lower) or
                    ("departure" in memory_lower and "arrival" in memory_lower) or
                    ("flight" in memory_lower and ("→" in memory_text or "->" in memory_text))
                )
                
                if not is_travel_history and memory_id:
                    result = self.delete_memory(user_id, memory_id)
                    if "success" in result and result["success"]:
                        deleted_count += 1
                else:
                    # Keep travel history
                    skipped_count += 1
            
            print(f"[MEMORY] Preference deletion complete: {deleted_count} deleted, {skipped_count} kept")
            return {
                "success": True,
                "deleted": deleted_count,
                "kept": skipped_count,
                "method": "selective_deletion"
            }
        except Exception as e:
            print(f"[MEMORY ERROR] Error clearing preferences for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    
    def remove_preference(self, user_id: str, preference_text: str) -> Dict:
        """
        Remove a preference by matching its text.
        This is a workaround since mem0 doesn't have direct ID-based deletion.
        
        Args:
            user_id: The user identifier
            preference_text: The text of the preference to remove
            
        Returns:
            Result of removal
        """
        try:
            # Get all memories
            all_memories = self.get_user_memories(user_id)
            
            # Normalize search text
            search_text = preference_text.strip().lower()
            
            # Find matching memory - try multiple matching strategies
            target_mem = None
            
            for mem in all_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                memory_text_lower = memory_text.strip().lower()
                
                # Strategy 1: Exact match
                if search_text == memory_text_lower:
                    target_mem = mem
                    break
                
                # Strategy 2: Partial match (search_text in memory_text or vice versa)
                if search_text in memory_text_lower or memory_text_lower in search_text:
                    target_mem = mem
                    break
                
                # Strategy 3: Fuzzy match - check if most words match
                search_words = set(search_text.split())
                memory_words = set(memory_text_lower.split())
                if len(search_words & memory_words) >= max(1, len(search_words) - 1):
                    target_mem = mem
                    break
            
            if target_mem:
                memory_id = target_mem.get("id", None)
                if memory_id:
                    print(f"[MEMORY] Found preference to delete. ID: {memory_id}, Text: {target_mem.get('memory', '')}")
                    result = self.delete_memory(user_id, memory_id)
                    if result.get("success"):
                        return {"success": True, "deleted_id": memory_id, "deleted_text": target_mem.get("memory", "")}
                    else:
                        return result
            
            print(f"[MEMORY] Could not find preference matching: {preference_text}")
            print(f"[MEMORY] Available preferences: {[m.get('memory', '') for m in all_memories]}")
            return {"error": f"Preference '{preference_text}' not found"}
        except Exception as e:
            print(f"[MEMORY ERROR] Error removing preference for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def remove_preferences_by_type(self, user_id: str, preference_type: str) -> Dict:
        """Remove all preference memories matching a structured type.

        This is used by natural-language commands like "forget my cabin class preference".
        Since mem0 doesn't support server-side deletion filters, we scan the user's
        memories and delete matches by ID.
        """
        pref_type = (preference_type or "").strip().lower()
        if not pref_type:
            return {"error": "preference_type is required"}

        memory = self._get_memory()
        if not memory:
            return {"error": "Memory system not available"}

        # Map DB/memory types to canonical label prefixes.
        canonical_prefixes: dict[str, tuple[str, ...]] = {
            "cabin_class": ("cabin class:",),
            "departure_time": ("departure time:",),
            "trip_type": ("trip type:",),
            "red_eye": ("red-eye:", "red eye:"),
            "seat": ("seat:",),
            "baggage": ("baggage:",),
            "passenger": ("travel:",),
            # flight_type canonicalizes to "Stops: ..." sometimes.
            "flight_type": ("stops:",),
            "airline": (),
        }

        try:
            all_memories = self.get_user_memories(user_id, limit=200)
            deleted_ids: list[str] = []
            for mem in all_memories or []:
                if not (mem and isinstance(mem, dict)):
                    continue

                memory_id = mem.get("id")
                memory_text = (mem.get("memory") or "").strip()
                if not memory_id or not memory_text:
                    continue

                lower = memory_text.lower()

                # Strong match: our structured wrapper includes "(Type: <type>)".
                if f"type: {pref_type}" in lower:
                    res = self.delete_memory(user_id, memory_id)
                    if isinstance(res, dict) and res.get("success"):
                        deleted_ids.append(memory_id)
                    continue

                # Fallback: canonicalize and match prefix.
                core = self._strip_preference_wrappers(memory_text)
                canonical = self._canonicalize_preference_text(core).strip().lower()
                prefixes = canonical_prefixes.get(pref_type, ())
                if prefixes and any(canonical.startswith(p) for p in prefixes):
                    res = self.delete_memory(user_id, memory_id)
                    if isinstance(res, dict) and res.get("success"):
                        deleted_ids.append(memory_id)

            return {"success": True, "type": pref_type, "deleted": len(deleted_ids), "deleted_ids": deleted_ids}
        except Exception as e:
            print(f"[MEMORY ERROR] Error removing preference type '{pref_type}' for user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    def get_full_user_profile(self, user_id: str) -> Dict:
        """
        Get comprehensive user profile including all memories and preferences.
        
        Returns structured profile with all categories.
        """
        try:
            return {
                "user_id": user_id,
                "preferences": self.summarize_preferences(user_id),
                "travel_history": self.get_travel_history(user_id),
                "favorite_routes": self.get_favorite_routes(user_id),
                "airline_preferences": self.get_airline_preferences(user_id),
                "budget_preferences": self.get_budget_preferences(user_id),
                "last_updated": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error getting user profile: {e}")
            return {"user_id": user_id, "error": str(e)}


# Instantiate global memory manager
memory_manager = TravelMemoryManager()
