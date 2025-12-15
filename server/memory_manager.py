import os
from typing import Optional

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
    
    def get_user_memories(self, user_id: str, query: Optional[str] = None) -> list:
        """
        Retrieve user memories, optionally filtered by a search query.
        
        Args:
            user_id: The user identifier
            query: Optional search query to filter memories
        """
        memory = self._get_memory()
        if not memory:
            return []
        
        try:
            if query:
                results = memory.search(query, user_id=user_id)
                return results.get("results", [])
            else:
                all_memories = memory.get_all(user_id=user_id)
                return all_memories.get("results", []) if isinstance(all_memories, dict) else all_memories
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []
    
    def add_memory(self, user_id: str, messages: list) -> dict:
        """
        Add new memories from conversation messages.
        
        Args:
            user_id: The user identifier
            messages: List of conversation messages
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
    
    def get_preferences_summary(self, user_id: str) -> str:
        """
        Get a formatted summary of user travel preferences.
        
        Args:
            user_id: The user identifier
        """
        memories = self.get_user_memories(user_id)
        
        if not memories:
            return ""
        
        preference_parts = []
        for mem in memories:
            memory_text = mem.get("memory", "") if isinstance(mem, dict) else str(mem)
            if memory_text:
                preference_parts.append(f"- {memory_text}")
        
        if preference_parts:
            return "User preferences and history:\n" + "\n".join(preference_parts)
        
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
            "business class", "economy", "window seat", "aisle seat",
            "morning", "evening", "red-eye", "airline"
        ]
        
        should_store = any(kw in user_message.lower() for kw in preference_keywords)
        
        if should_store:
            self.add_memory(user_id, messages)
        
        return should_store


memory_manager = TravelMemoryManager()
