import hashlib
import time
import json
import os
import logging
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self):
        self.token_file = 'tokens.json'
        self.logger = logging.getLogger(__name__)
        self.tokens = {"active_tokens": {}}
        self.load_tokens()
        
    def load_tokens(self):
        """Load tokens from file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    self.tokens = json.load(f)
            else:
                self.save_tokens()  # Create new tokens file
        except Exception as e:
            self.logger.error(f"Error loading tokens: {str(e)}")

    def save_tokens(self):
        """Save tokens to file"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump(self.tokens, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving tokens: {str(e)}")

    def generate_token(self, user_id: str, usage_count: int = 10) -> str:
        """Generate a new token"""
        timestamp = int(time.time())
        token_base = f"PRB-{user_id}-{timestamp}-{usage_count}"
        token_hash = hashlib.sha256(token_base.encode()).hexdigest()[:8]
        token = f"{token_base}-{token_hash}"
        
        self.tokens["active_tokens"][token] = {
            "user_id": user_id,
            "created_at": timestamp,
            "uses_remaining": usage_count,
            "is_active": True
        }
        self.save_tokens()
        return token

    def validate_token(self, token: str) -> bool:
        """Validate a token"""
        return token in self.tokens["active_tokens"]

    def validate_token_with_usage(self, token: str, record_usage: bool = True) -> dict:
        """
        Validate a token and record its usage
        
        Returns:
        - dict: Validation result with status and message
        """
        if token not in self.tokens["active_tokens"]:
            return {"valid": False, "message": "Invalid token"}
            
        token_data = self.tokens["active_tokens"][token]
        
        # Check expiration
        if time.time() > token_data["expires_at"]:
            return {"valid": False, "message": "Token expired"}
            
        # Check if active
        if not token_data["is_active"]:
            return {"valid": False, "message": "Token revoked"}
            
        # Check usage count
        if token_data["uses_remaining"] <= 0:
            return {"valid": False, "message": "No uses remaining"}
            
        if record_usage:
            # Record usage
            current_time = int(time.time())
            token_data["uses_remaining"] -= 1
            token_data["last_used"] = current_time
            token_data["usage_history"].append({
                "timestamp": current_time,
                "remaining_uses": token_data["uses_remaining"]
            })
            
            self.save_tokens()
            
        return {
            "valid": True,
            "message": "Token valid",
            "uses_remaining": token_data["uses_remaining"]
        } 