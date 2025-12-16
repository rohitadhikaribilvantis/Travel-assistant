import os
from typing import Optional, List, Dict
from datetime import datetime

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
            return []
        
        try:
            if query:
                results = memory.search(query, user_id=user_id)
                return results.get("results", []) if isinstance(results, dict) else results
            else:
                all_memories = memory.get_all(user_id=user_id)
                return all_memories.get("results", []) if isinstance(all_memories, dict) else (all_memories if isinstance(all_memories, list) else [])
        except Exception as e:
            print(f"Error retrieving memories: {e}")
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
            return {"error": "Memory system not available"}
        
        try:
            result = memory.add(messages, user_id=user_id)
            return result
        except Exception as e:
            print(f"Error adding memory: {e}")
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
            
            if not memories:
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
            
            context_parts = []
            
            if preferences:
                context_parts.append("USER PREFERENCES AND PATTERNS:")
                context_parts.extend([f"- {p}" for p in preferences])
            
            if travel_history:
                context_parts.append("\nTRAVEL HISTORY:")
                context_parts.extend([f"- {h}" for h in travel_history])
            
            return "\n".join(context_parts) if context_parts else ""
        except Exception as e:
            print(f"Error getting user context: {e}")
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


memory_manager = TravelMemoryManager()
