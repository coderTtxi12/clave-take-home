"""
Session management for coding agent conversations
Stores conversation history in Redis with 24h expiration
"""
import json
from typing import List, Optional
try:
    import redis
except ImportError:
    redis = None  # type: ignore
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Redis connection configuration
SESSION_EXPIRY = 86400  # 24 hours in seconds
SESSION_PREFIX = "coding_agent_session:"


class SessionManager:
    """Manages conversation sessions using Redis"""
    
    def __init__(self):
        """Initialize Redis connection"""
        if redis is None:
            raise ImportError("redis package is not installed. Install it with: pip install redis")
        
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,  # Automatically decode responses to strings
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for session management")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_key(self, session_id: str) -> str:
        """Generate Redis key for session"""
        return f"{SESSION_PREFIX}{session_id}"
    
    def get_messages(self, session_id: str) -> List[dict]:
        """
        Retrieve conversation history for a session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of message dictionaries, empty list if session not found
        """
        try:
            key = self._get_key(session_id)
            data = self.redis_client.get(key)
            
            if data is None:
                logger.info(f"No session found for {session_id}, starting new session")
                return []
            
            messages = json.loads(data)
            logger.info(f"Retrieved {len(messages)} messages for session {session_id}")
            return messages
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode session data for {session_id}: {e}")
            return []
        except redis.RedisError as e:
            logger.error(f"Redis error retrieving session {session_id}: {e}")
            return []
    
    def save_messages(self, session_id: str, messages: List[dict]) -> bool:
        """
        Save conversation history for a session
        
        Args:
            session_id: Unique session identifier
            messages: List of message dictionaries to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(session_id)
            data = json.dumps(messages)
            
            # Save with 24h expiration
            self.redis_client.setex(key, SESSION_EXPIRY, data)
            
            logger.info(f"Saved {len(messages)} messages for session {session_id} (expires in 24h)")
            return True
            
        except (TypeError, ValueError, redis.RedisError) as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its conversation history
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(session_id)
            result = self.redis_client.delete(key)
            
            if result > 0:
                logger.info(f"Deleted session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False
                
        except redis.RedisError as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def get_session_ttl(self, session_id: str) -> Optional[int]:
        """
        Get remaining time-to-live for a session in seconds
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            TTL in seconds, None if session doesn't exist or error
        """
        try:
            key = self._get_key(session_id)
            ttl = self.redis_client.ttl(key)
            
            if ttl < 0:
                # -2 means key doesn't exist, -1 means no expiration set
                return None
            
            return ttl
            
        except redis.RedisError as e:
            logger.error(f"Failed to get TTL for session {session_id}: {e}")
            return None
    
    def extend_session(self, session_id: str) -> bool:
        """
        Extend session expiration by another 24 hours
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_key(session_id)
            result = self.redis_client.expire(key, SESSION_EXPIRY)
            
            if result:
                logger.info(f"Extended session {session_id} by 24h")
                return True
            else:
                logger.warning(f"Failed to extend session {session_id} (may not exist)")
                return False
                
        except redis.RedisError as e:
            logger.error(f"Failed to extend session {session_id}: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get or create the global session manager instance
    
    Returns:
        SessionManager instance
    """
    global _session_manager
    
    if _session_manager is None:
        _session_manager = SessionManager()
    
    return _session_manager

