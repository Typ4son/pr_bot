import json
import time
import hashlib
import logging
import os

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

    def validate_token(self, token: str) -> bool:
        """Validate a token"""
        return token in self.tokens["active_tokens"]

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