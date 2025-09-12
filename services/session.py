import uuid
from cachetools import TTLCache
from config import Config, logger

class SessionManager:
    """
    Manages user sessions and their associated data.
    Implements a TTL cache to automatically expire sessions.
    """
    
    def __init__(self):
        """Initialize the session manager with a TTL cache."""
        self.sessions = TTLCache(maxsize=1024, ttl=Config.SESSION_TTL)
    
    def get_session_id(self, user_id: str) -> str:
        """
        Returns an existing session_id or creates a new one for the given user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            A session ID (UUID) as string
        """
        if user_id in self.sessions:
            return self.sessions[user_id]
        
        new_session_id = str(uuid.uuid4())
        self.sessions[user_id] = new_session_id
        logger.info(f"Created new session {new_session_id} for user {user_id}")
        return new_session_id
    
    def clear_session(self, user_id: str) -> None:
        """
        Clears a user's session if it exists.
        
        Args:
            user_id: The Discord user ID
        """
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")

# Global session manager instance
session_manager = SessionManager() 