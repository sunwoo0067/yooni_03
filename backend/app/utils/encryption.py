"""
Enhanced encryption utilities for secure storage of sensitive data like API keys
Supports multi-layer encryption, key rotation, and audit logging
"""
import base64
import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Enhanced encryption manager with multi-layer security and key rotation"""
    
    def __init__(self, master_key: Optional[str] = None, enable_key_rotation: bool = True):
        """
        Initialize encryption manager with master key
        
        Args:
            master_key: Master key for encryption. If None, uses environment variable
            enable_key_rotation: Enable automatic key rotation capabilities
        """
        self._master_key = master_key or os.getenv("ENCRYPTION_MASTER_KEY")
        if not self._master_key:
            raise ValueError("Encryption master key not provided")
        
        self._enable_key_rotation = enable_key_rotation
        self._current_key_id = "key_v1"
        self._key_cache = {}
        self._audit_log = []
        
        # Initialize encryption keys
        self._init_encryption_keys()
        
        # Initialize RSA key pair for asymmetric encryption
        self._init_rsa_keys()
    
    def _init_encryption_keys(self):
        """Initialize multiple encryption keys for rotation"""
        # Generate multiple keys for rotation
        keys = []
        for i in range(3):  # Keep 3 keys for rotation
            key_id = f"key_v{i+1}"
            salt = hashlib.sha256(f"{self._master_key}_{key_id}".encode()).digest()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            derived_key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
            fernet_key = Fernet(derived_key)
            keys.append(fernet_key)
            self._key_cache[key_id] = fernet_key
        
        # Use MultiFernet for automatic key rotation
        self._multifernet = MultiFernet(keys)
        self._current_fernet = keys[0]  # Current encryption key
    
    def _init_rsa_keys(self):
        """Initialize RSA key pair for asymmetric encryption"""
        try:
            # Try to load existing keys first
            private_key_path = os.getenv("RSA_PRIVATE_KEY_PATH", "/tmp/rsa_private.pem")
            public_key_path = os.getenv("RSA_PUBLIC_KEY_PATH", "/tmp/rsa_public.pem")
            
            if os.path.exists(private_key_path) and os.path.exists(public_key_path):
                with open(private_key_path, "rb") as f:
                    self._rsa_private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=default_backend()
                    )
                with open(public_key_path, "rb") as f:
                    self._rsa_public_key = serialization.load_pem_public_key(
                        f.read(), backend=default_backend()
                    )
            else:
                # Generate new RSA key pair
                self._rsa_private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                self._rsa_public_key = self._rsa_private_key.public_key()
                
                # Save keys if paths are provided
                try:
                    os.makedirs(os.path.dirname(private_key_path), exist_ok=True)
                    with open(private_key_path, "wb") as f:
                        f.write(self._rsa_private_key.private_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PrivateFormat.PKCS8,
                            encryption_algorithm=serialization.NoEncryption()
                        ))
                    
                    with open(public_key_path, "wb") as f:
                        f.write(self._rsa_public_key.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        ))
                except Exception as e:
                    logger.warning(f"Could not save RSA keys: {e}")
        
        except Exception as e:
            logger.error(f"Failed to initialize RSA keys: {e}")
            self._rsa_private_key = None
            self._rsa_public_key = None
    
    def encrypt(self, plaintext: str, use_rsa: bool = False) -> str:
        """
        Encrypt plaintext string with enhanced security
        
        Args:
            plaintext: String to encrypt
            use_rsa: Use RSA encryption for extra security (for small data)
            
        Returns:
            Base64 encoded encrypted string with metadata
        """
        if not plaintext:
            return ""
        
        try:
            timestamp = datetime.utcnow().isoformat()
            
            if use_rsa and self._rsa_public_key and len(plaintext.encode()) <= 190:
                # RSA encryption for small sensitive data
                encrypted_bytes = self._rsa_public_key.encrypt(
                    plaintext.encode(),
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Wrap with metadata
                encrypted_data = {
                    "method": "rsa",
                    "data": base64.urlsafe_b64encode(encrypted_bytes).decode(),
                    "key_id": "rsa_v1",
                    "timestamp": timestamp
                }
            else:
                # Fernet encryption for general use
                encrypted_bytes = self._current_fernet.encrypt(plaintext.encode())
                
                # Wrap with metadata
                encrypted_data = {
                    "method": "fernet",
                    "data": base64.urlsafe_b64encode(encrypted_bytes).decode(),
                    "key_id": self._current_key_id,
                    "timestamp": timestamp
                }
            
            # Log encryption event
            self._log_crypto_event("encrypt", len(plaintext), encrypted_data["method"])
            
            # Return as JSON string
            return base64.urlsafe_b64encode(
                json.dumps(encrypted_data).encode()
            ).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted string with automatic method detection
        
        Args:
            encrypted_text: Base64 encoded encrypted string with metadata
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return ""
        
        try:
            # Try to parse as new format with metadata
            try:
                metadata_json = base64.urlsafe_b64decode(encrypted_text.encode()).decode()
                encrypted_data = json.loads(metadata_json)
                
                method = encrypted_data.get("method")
                data = encrypted_data.get("data")
                key_id = encrypted_data.get("key_id")
                
                if method == "rsa":
                    # RSA decryption
                    if not self._rsa_private_key:
                        raise ValueError("RSA private key not available")
                    
                    encrypted_bytes = base64.urlsafe_b64decode(data.encode())
                    decrypted_bytes = self._rsa_private_key.decrypt(
                        encrypted_bytes,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    result = decrypted_bytes.decode()
                    
                elif method == "fernet":
                    # Fernet decryption with key rotation support
                    encrypted_bytes = base64.urlsafe_b64decode(data.encode())
                    
                    # Try current keys first, then fall back to MultiFernet
                    try:
                        if key_id in self._key_cache:
                            result = self._key_cache[key_id].decrypt(encrypted_bytes).decode()
                        else:
                            result = self._multifernet.decrypt(encrypted_bytes).decode()
                    except Exception:
                        # Fallback to MultiFernet for key rotation
                        result = self._multifernet.decrypt(encrypted_bytes).decode()
                else:
                    raise ValueError(f"Unknown encryption method: {method}")
                
                # Log decryption event
                self._log_crypto_event("decrypt", len(result), method)
                return result
                
            except (json.JSONDecodeError, KeyError):
                # Fallback to legacy format (direct Fernet encryption)
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
                result = self._multifernet.decrypt(encrypted_bytes).decode()
                self._log_crypto_event("decrypt", len(result), "fernet_legacy")
                return result
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_dict(self, data: dict) -> dict:
        """
        Encrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary containing sensitive data
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        sensitive_fields = {
            'api_key', 'api_secret', 'access_token', 'refresh_token',
            'client_secret', 'secret_key', 'password'
        }
        
        encrypted_data = data.copy()
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """
        Decrypt sensitive fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted sensitive data
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        sensitive_fields = {
            'api_key', 'api_secret', 'access_token', 'refresh_token',
            'client_secret', 'secret_key', 'password'
        }
        
        decrypted_data = data.copy()
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(str(decrypted_data[field]))
                except ValueError:
                    # If decryption fails, field might not be encrypted
                    logger.warning(f"Failed to decrypt field {field}, keeping original value")
        
        return decrypted_data
    
    def _log_crypto_event(self, operation: str, data_size: int, method: str):
        """Log cryptographic operations for audit"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "method": method,
            "data_size": data_size,
            "key_id": self._current_key_id
        }
        
        self._audit_log.append(event)
        
        # Keep only last 1000 events
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def rotate_encryption_key(self) -> bool:
        """Rotate to next encryption key"""
        try:
            if not self._enable_key_rotation:
                logger.warning("Key rotation is disabled")
                return False
            
            # Generate new key
            current_version = int(self._current_key_id.split("_v")[1])
            new_version = current_version + 1
            new_key_id = f"key_v{new_version}"
            
            # Create new Fernet key
            salt = hashlib.sha256(f"{self._master_key}_{new_key_id}".encode()).digest()
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            derived_key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
            new_fernet = Fernet(derived_key)
            
            # Update key cache and current key
            self._key_cache[new_key_id] = new_fernet
            self._current_key_id = new_key_id
            self._current_fernet = new_fernet
            
            # Update MultiFernet with new key set
            keys = list(self._key_cache.values())[-3:]  # Keep last 3 keys
            self._multifernet = MultiFernet(keys)
            
            logger.info(f"Encryption key rotated to {new_key_id}")
            self._log_crypto_event("key_rotation", 0, "key_rotation")
            
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return False
    
    def encrypt_platform_credentials(
        self,
        platform_type: str,
        credentials: Dict[str, Any],
        use_enhanced_security: bool = True
    ) -> Dict[str, Any]:
        """Encrypt platform credentials with enhanced security
        
        Args:
            platform_type: Platform type
            credentials: Platform credentials
            use_enhanced_security: Use RSA for critical fields
            
        Returns:
            Encrypted credentials
        """
        encrypted_creds = credentials.copy()
        
        # Define critical fields that should use RSA encryption
        critical_fields = {"secret_key", "client_secret", "api_secret"}
        sensitive_fields = {
            'api_key', 'api_secret', 'access_token', 'refresh_token',
            'client_secret', 'secret_key', 'password'
        }
        
        for field in sensitive_fields:
            if field in encrypted_creds and encrypted_creds[field]:
                use_rsa = use_enhanced_security and field in critical_fields
                encrypted_creds[field] = self.encrypt(
                    str(encrypted_creds[field]),
                    use_rsa=use_rsa
                )
        
        # Add encryption metadata
        encrypted_creds["_encryption_metadata"] = {
            "platform": platform_type,
            "encrypted_at": datetime.utcnow().isoformat(),
            "encryption_version": "v2_enhanced",
            "key_id": self._current_key_id
        }
        
        return encrypted_creds
    
    def decrypt_platform_credentials(self, encrypted_credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt platform credentials with automatic format detection"""
        decrypted_creds = encrypted_credentials.copy()
        
        # Remove metadata
        metadata = decrypted_creds.pop("_encryption_metadata", {})
        
        sensitive_fields = {
            'api_key', 'api_secret', 'access_token', 'refresh_token',
            'client_secret', 'secret_key', 'password'
        }
        
        for field in sensitive_fields:
            if field in decrypted_creds and decrypted_creds[field]:
                try:
                    decrypted_creds[field] = self.decrypt(str(decrypted_creds[field]))
                except ValueError as e:
                    logger.warning(f"Failed to decrypt field {field}: {e}")
                    # Keep original value if decryption fails
        
        return decrypted_creds
    
    def validate_encryption_integrity(self, encrypted_data: str) -> Dict[str, Any]:
        """Validate encryption integrity and metadata"""
        validation = {
            "valid": False,
            "format": "unknown",
            "metadata": {},
            "issues": []
        }
        
        try:
            # Try to parse metadata
            metadata_json = base64.urlsafe_b64decode(encrypted_data.encode()).decode()
            encrypted_metadata = json.loads(metadata_json)
            
            validation["format"] = "enhanced"
            validation["metadata"] = {
                "method": encrypted_metadata.get("method"),
                "key_id": encrypted_metadata.get("key_id"),
                "timestamp": encrypted_metadata.get("timestamp")
            }
            
            # Check if we can decrypt (without actually decrypting)
            method = encrypted_metadata.get("method")
            key_id = encrypted_metadata.get("key_id")
            
            if method == "rsa" and not self._rsa_private_key:
                validation["issues"].append("RSA private key not available")
            elif method == "fernet" and key_id not in self._key_cache:
                validation["issues"].append(f"Encryption key {key_id} not available")
            else:
                validation["valid"] = True
                
        except (json.JSONDecodeError, ValueError):
            # Might be legacy format
            try:
                base64.urlsafe_b64decode(encrypted_data.encode())
                validation["format"] = "legacy"
                validation["valid"] = True
            except Exception:
                validation["issues"].append("Invalid base64 encoding")
        
        return validation
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption usage statistics"""
        return {
            "current_key_id": self._current_key_id,
            "available_keys": list(self._key_cache.keys()),
            "rsa_available": self._rsa_private_key is not None,
            "key_rotation_enabled": self._enable_key_rotation,
            "audit_log_size": len(self._audit_log),
            "recent_operations": self._audit_log[-10:] if self._audit_log else []
        }
    
    def secure_compare(self, a: str, b: str) -> bool:
        """Secure string comparison to prevent timing attacks"""
        return secrets.compare_digest(a.encode(), b.encode())
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    def hash_sensitive_data(self, data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash sensitive data with salt
        
        Args:
            data: Data to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hash, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        hash_obj = hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000)
        return hash_obj.hex(), salt


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_sensitive_data(data: str) -> str:
    """Convenience function to encrypt sensitive data"""
    return get_encryption_manager().encrypt(data)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Convenience function to decrypt sensitive data"""
    return get_encryption_manager().decrypt(encrypted_data)


def encrypt_data(data: str) -> str:
    """Alias for encrypt_sensitive_data for backward compatibility"""
    return encrypt_sensitive_data(data)


def decrypt_data(encrypted_data: str) -> str:
    """Alias for decrypt_sensitive_data for backward compatibility"""
    return decrypt_sensitive_data(encrypted_data)


def validate_platform_credentials(platform_type: str, credentials: dict) -> bool:
    """
    Validate platform-specific credentials format
    
    Args:
        platform_type: Platform type (coupang, naver, 11st)
        credentials: Dictionary containing platform credentials
        
    Returns:
        True if credentials are valid for the platform
    """
    platform_requirements = {
        'coupang': {'access_key', 'secret_key', 'vendor_id'},
        'naver': {'client_id', 'client_secret', 'store_id'},
        '11st': {'api_key', 'secret_key', 'seller_id'},
        'gmarket': {'api_key', 'secret_key', 'seller_id'},
        'auction': {'api_key', 'secret_key', 'seller_id'},
        'tmon': {'api_key', 'secret_key', 'seller_id'},
        'wemakeprice': {'api_key', 'secret_key', 'seller_id'},
        'interpark': {'api_key', 'secret_key', 'seller_id'}
    }
    
    required_fields = platform_requirements.get(platform_type.lower())
    if not required_fields:
        logger.warning(f"Unknown platform type: {platform_type}")
        return False
    
    # Check if all required fields are present and not empty
    for field in required_fields:
        if field not in credentials or not credentials[field]:
            logger.warning(f"Missing or empty required field '{field}' for platform '{platform_type}'")
            return False
    
    return True


def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """
    Mask sensitive value for logging/display purposes
    
    Args:
        value: Sensitive value to mask
        show_chars: Number of characters to show at the end
        
    Returns:
        Masked value
    """
    if not value or len(value) <= show_chars:
        return "*" * len(value) if value else ""
    
    return "*" * (len(value) - show_chars) + value[-show_chars:]


def generate_audit_log_entry(
    user_id: str,
    action: str,
    platform_account_id: str,
    details: dict = None
) -> dict:
    """
    Generate audit log entry for platform account operations
    
    Args:
        user_id: ID of user performing the action
        action: Action being performed (create, update, delete, etc.)
        platform_account_id: ID of platform account being modified
        details: Additional details about the action
        
    Returns:
        Audit log entry dictionary
    """
    from datetime import datetime
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'action': action,
        'resource_type': 'platform_account',
        'resource_id': platform_account_id,
        'details': details or {},
        'ip_address': None,  # To be filled by request context
        'user_agent': None   # To be filled by request context
    }