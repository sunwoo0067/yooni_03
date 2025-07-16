"""
Encryption utilities for storing sensitive supplier API credentials.
Uses Django's built-in encryption capabilities with Fernet symmetric encryption.
"""
import base64
import json
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class CredentialEncryption:
    """Handles encryption and decryption of supplier API credentials."""
    
    def __init__(self):
        """Initialize the encryption handler with the encryption key."""
        self._cipher_suite = self._get_cipher_suite()
    
    def _get_cipher_suite(self) -> Fernet:
        """Get or create the Fernet cipher suite for encryption."""
        # Get encryption key from settings or generate from SECRET_KEY
        encryption_key = getattr(settings, 'SUPPLIER_ENCRYPTION_KEY', None)
        
        if not encryption_key:
            # Generate a key from Django's SECRET_KEY
            # This ensures the key is consistent across application restarts
            secret_key_bytes = settings.SECRET_KEY.encode()[:32]
            # Pad or truncate to exactly 32 bytes
            if len(secret_key_bytes) < 32:
                secret_key_bytes = secret_key_bytes.ljust(32, b'0')
            encryption_key = base64.urlsafe_b64encode(secret_key_bytes)
        
        try:
            return Fernet(encryption_key)
        except Exception as e:
            raise ImproperlyConfigured(
                f"Invalid SUPPLIER_ENCRYPTION_KEY. Please ensure it's a valid Fernet key: {str(e)}"
            )
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary of credentials.
        
        Args:
            credentials: Dictionary containing API credentials
            
        Returns:
            Encrypted string representation of the credentials
        """
        if not credentials:
            return ""
        
        # Convert to JSON string
        json_str = json.dumps(credentials, separators=(',', ':'))
        
        # Encrypt the JSON string
        encrypted_bytes = self._cipher_suite.encrypt(json_str.encode())
        
        # Return as base64 encoded string for storage
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt_credentials(self, encrypted_data: str) -> Optional[Dict[str, Any]]:
        """
        Decrypt an encrypted credentials string.
        
        Args:
            encrypted_data: Encrypted string containing credentials
            
        Returns:
            Dictionary of decrypted credentials or None if decryption fails
        """
        if not encrypted_data:
            return None
        
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt the data
            decrypted_bytes = self._cipher_suite.decrypt(encrypted_bytes)
            
            # Parse JSON
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            # Log the error in production, return None for now
            print(f"Failed to decrypt credentials: {str(e)}")
            return None


# Create a singleton instance
credential_encryption = CredentialEncryption()