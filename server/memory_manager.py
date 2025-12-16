import os
from typing import Optional, List, Dict, Literal
from datetime import datetime

# Memory Schema Types
PreferenceType = Literal["seat", "airline", "departure_time", "flight_type", "cabin_class", "red_eye", "baggage", "general"]
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
            return f"Travel Preference: {self.content} (Type: {self.memory_type})"
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
                from mem0 import Memory
                
                mem0_api_key = os.environ.get("MEM0_API_KEY")
                openai_api_key = os.environ.get("OPENAI_API_KEY")
                
                if not mem0_api_key:
                    print("Warning: MEM0_API_KEY not set in environment")
                    self._memory = None
                    self._initialized = True
                    return None
                
                self._memory = Memory(
                    api_key=mem0_api_key,
                    config={
                        "llm": {
                            "provider": "openai",
                            "config": {
                                "model": "gpt-4o",
                                "api_key": openai_api_key
                            }
                        }
                    }
                )
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
            if query:
                print(f"[MEMORY] Searching for '{query}' for user {user_id}")
                results = memory.search(query, user_id=user_id)
                memories = results.get("results", []) if isinstance(results, dict) else results
            else:
                print(f"[MEMORY] Getting all memories for user {user_id}")
                all_memories = memory.get_all(user_id=user_id)
                memories = all_memories.get("results", []) if isinstance(all_memories, dict) else (all_memories if isinstance(all_memories, list) else [])
            
            print(f"[MEMORY] Retrieved {len(memories)} memories for user {user_id}: {memories}")
            return memories
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
            return result
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
        message = f"Preference: {preference_type} - {preference_value}"
        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": f"I've noted that you prefer {preference_value} for {preference_type}."}
        ]
        return self.add_memory(user_id, messages)
    
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
    
    def get_travel_history(self, user_id: str) -> List[Dict]:
        """Get travel history memories for a user."""
        return self.get_user_memories(user_id, query="traveled booked flight journey trip")
    
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
            
            summary = {
                "seat_preferences": [],
                "airline_preferences": [],
                "time_preferences": [],
                "flight_type_preferences": [],
                "cabin_class_preferences": [],
                "routes": [],
                "budget_info": [],
                "other_preferences": []
            }
            
            for mem in all_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if not memory_text:
                    continue
                
                memory_id = mem.get("id", None) if isinstance(mem, dict) else None
                memory_lower = memory_text.lower()
                
                # Create entry (with or without ID)
                if include_ids:
                    entry = {"id": memory_id, "text": memory_text, "memory": memory_text}
                else:
                    entry = memory_text
                
                # Categorize the memory
                if any(word in memory_lower for word in ["seat", "window", "aisle", "middle", "exit row"]):
                    summary["seat_preferences"].append(entry)
                elif any(word in memory_lower for word in ["airline", "carrier", "united", "delta", "american"]):
                    summary["airline_preferences"].append(entry)
                elif any(word in memory_lower for word in ["morning", "evening", "afternoon", "time", "depart", "red-eye"]):
                    summary["time_preferences"].append(entry)
                elif any(word in memory_lower for word in ["direct", "non-stop", "layover", "stop"]):
                    summary["flight_type_preferences"].append(entry)
                elif any(word in memory_lower for word in ["business", "economy", "premium", "first class", "cabin"]):
                    summary["cabin_class_preferences"].append(entry)
                elif any(word in memory_lower for word in ["budget", "price", "cost", "cheap", "expensive"]):
                    summary["budget_info"].append(entry)
                elif any(word in memory_lower for word in ["route", "traveled", "booked", "flight"]):
                    summary["routes"].append(entry)
                else:
                    summary["other_preferences"].append(entry)
            
            # Remove empty categories
            return {k: v for k, v in summary.items() if v}
        except Exception as e:
            print(f"Error summarizing preferences: {e}")
            return {}
    
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
            # mem0 doesn't have a direct delete by ID, so we'll search and identify
            # For now, we'll store this as a soft delete indicator
            # In practice, you'd need to use mem0's API more directly
            result = memory.delete(memory_id, user_id=user_id) if hasattr(memory, 'delete') else {"error": "Delete not supported"}
            print(f"[MEMORY] Delete result: {result}")
            return result
        except Exception as e:
            print(f"[MEMORY ERROR] Error deleting memory {memory_id} for user {user_id}: {e}")
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
            
            # Find and remove matching memory
            for mem in all_memories:
                memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
                if preference_text.strip().lower() == memory_text.strip().lower():
                    memory_id = mem.get("id", None)
                    if memory_id:
                        return self.delete_memory(user_id, memory_id)
            
            return {"error": "Preference not found"}
        except Exception as e:
            print(f"[MEMORY ERROR] Error removing preference for user {user_id}: {e}")
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
