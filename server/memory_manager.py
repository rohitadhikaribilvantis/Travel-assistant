import os
import re
from typing import Optional, List, Dict, Literal
from datetime import datetime

# Memory Schema Types
PreferenceType = Literal["seat", "airline", "departure_time", "flight_type", "cabin_class", "red_eye", "baggage"]
MemoryCategory = Literal["preference", "travel_history", "route", "airline", "budget"]

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
    
    def get_user_memories(self, user_id: str, query: Optional[str] = None) -> List[Dict]:
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
            print(f"[MEMORY] mem0 not initialized for user {user_id}")
            return []
        
        try:
            # MemoryClient requires filters parameter with user_id
            filters = {"user_id": user_id}
            
            if query:
                print(f"[MEMORY] Searching for '{query}' for user {user_id}")
                results = memory.search(query, filters=filters)
            else:
                # If no query, search for generic terms to get all preferences
                print(f"[MEMORY] Getting all memories for user {user_id} via search")
                search_query = "preference flight cabin class time depart airline seat travel"
                results = memory.search(search_query, filters=filters)
            
            print(f"[MEMORY] Search results: {results}")
            
            # MemoryClient.search() returns {"results": [memory_list]}
            if isinstance(results, dict):
                memories = results.get("results", [])
            else:
                memories = results if isinstance(results, list) else []
            
            # Filter out "general" type memories (old/confusing ones we don't want to display)
            filtered_memories = [
                m for m in memories
                if not (isinstance(m, dict) and m.get("type") == "general")
                and not (isinstance(m, dict) and "Type: General" in str(m.get("memory", "")))
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
            # Search for preference-related memories
            preference_memories = self.get_user_memories(user_id, query="travel preferences seat airline time cabin class")
            
            if not preference_memories:
                return ""
            
            preference_parts = []
            for mem in preference_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if memory_text:
                    preference_parts.append(f"- {memory_text}")
            
            if preference_parts:
                return "Known user preferences and travel patterns:\n" + "\n".join(preference_parts)
            
            return ""
        except Exception as e:
            print(f"Error getting preferences summary: {e}")
            return ""
    
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
            "partner", "budget", "luxury"
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
            memories = self.get_user_memories(user_id, query="traveled booked flight journey trip")
            if not memories:
                return []
            
            # Filter to only include booked flights, not searches or other travel-related memories
            booked_flights = [
                m for m in memories 
                if m and isinstance(m, dict) and (
                    "booked" in m.get("memory", "").lower() or 
                    ("flight" in m.get("memory", "").lower() and "→" in m.get("memory", ""))
                )
            ]
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
    
    def summarize_preferences(self, user_id: str, include_ids: bool = False) -> Dict:
        """
        Get a structured summary of all user preferences.
        
        Returns a dictionary with categorized preferences.
        If include_ids is True, returns objects with 'id', 'text', and 'memory' fields.
        """
        try:
            all_memories = self.get_user_memories(user_id)
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
                
                # Create entry (with or without ID)
                if include_ids:
                    entry = {"id": memory_id, "text": memory_text, "memory": memory_text}
                else:
                    entry = memory_text
                
                print(f"[MEMORY] Processing memory: '{memory_text}' (lower: '{memory_lower}')")
                
                # Categorize the memory - Check cabin class FIRST since it's most specific
                if any(word in memory_lower for word in ["business", "economy", "premium", "first"]) and any(word in memory_lower for word in ["class", "cabin"]):
                    print(f"  -> Categorized as CABIN CLASS")
                    summary["cabin_class"].append(entry)
                elif any(word in memory_lower for word in ["red-eye", "red eye"]):
                    print(f"  -> Categorized as RED EYE")
                    summary["red_eye"].append(entry)
                elif any(word in memory_lower for word in ["round trip", "one-way", "round-trip", "one way"]):
                    print(f"  -> Categorized as TRIP TYPE")
                    summary["trip_type"].append(entry)
                elif any(word in memory_lower for word in ["direct", "non-stop", "layover", "stop"]):
                    print(f"  -> Categorized as FLIGHT TYPE")
                    summary["flight_type"].append(entry)
                elif any(word in memory_lower for word in ["morning", "afternoon", "evening", "depart"]):
                    print(f"  -> Categorized as TIME")
                    summary["departure_time"].append(entry)
                elif any(word in memory_lower for word in ["traveling alone", "solo", "travel alone", "fly alone", "traveling with family", "traveling with kids", "traveling with children", "traveling with partner", "traveling with spouse", "family trip"]):
                    print(f"  -> Categorized as PASSENGER")
                    summary["passenger"].append(entry)
                elif any(word in memory_lower for word in ["seat", "window", "aisle", "middle", "exit row"]):
                    print(f"  -> Categorized as SEAT")
                    summary["seat"].append(entry)
                elif any(word in memory_lower for word in ["airline", "carrier", "united", "delta", "american", "southwest", "jetblue"]):
                    print(f"  -> Categorized as AIRLINE")
                    summary["airline"].append(entry)
                elif any(word in memory_lower for word in ["baggage", "luggage", "bag", "carry-on", "checked"]):
                    print(f"  -> Categorized as BAGGAGE")
                    summary["baggage"].append(entry)
                elif any(word in memory_lower for word in ["budget", "price", "cost"]) and "general" not in memory_lower and "budget-conscious" not in memory_lower:
                    # Only add specific budget preferences (e.g., "max $500"), skip generic "budget-conscious"
                    print(f"  -> Categorized as BUDGET")
                    summary["budget"].append(entry)
                elif any(word in memory_lower for word in ["live", "based", "from", "home"]) and any(word in memory_lower for word in ["houston", "newyork", "los angeles", "london", "paris", "tokyo", "delhi", "mumbai", "kathmandu", "beijing", "chicago", "miami", "seattle", "boston", "denver", "dallas", "austin", "sanfrancisco"]):
                    print(f"  -> Categorized as LOCATION")
                    summary["location"].append(entry)
                else:
                    print(f"  -> Categorized as OTHER")
                    summary["other"].append(entry)
            
            print(f"[MEMORY] Final summary: {summary}")
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
            cabin_class = flight_data.get("cabin_class", "")
            price = flight_data.get("price", "")
            currency = flight_data.get("currency", "USD")
            
            # Build natural language content
            content = f"{airline_name} {origin} → {destination}"
            if departure_date:
                content += f" on {departure_date}"
            if departure_time and arrival_time:
                content += f" ({departure_time} - {arrival_time})"
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
                    "cabin_class": cabin_class,
                    "price": price,
                    "currency": currency,
                    "booked_at": datetime.utcnow().isoformat()
                }
            )
            
            print(f"[BOOKING] Successfully recorded booking, result: {result}")
            
            # Now retrieve all bookings to verify
            from main import app
            all_bookings = self.get_user_memories(user_id, query="booked flight booking")
            booked_flights = [m for m in all_bookings if isinstance(m, dict) and "booked" in m.get("memory", "").lower()]
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
