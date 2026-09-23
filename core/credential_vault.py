"""
Credential Vault — Part 4.3: OS keychain/local vault for secrets.
Never stores raw credentials in plaintext config files or audit logs.
"""
import os
import json
import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

from actions._api import _load_env

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_VAULT_FILE = _DATA_DIR / "credentials.enc"
_KEY_FILE = _DATA_DIR / ".vault_key"

_load_env()

class CredentialVault:
    """Encrypted local vault for API keys, tokens, secrets."""
    
    def __init__(self):
        self._cipher: Optional[Fernet] = None
        self._keyring_available = KEYRING_AVAILABLE
        self._init_cipher()
        
    def _init_cipher(self):
        """Initialize or load encryption key."""
        if _VAULT_FILE.exists() and _KEY_FILE.exists():
            try:
                with open(_KEY_FILE, "rb") as f:
                    key = f.read()
                self._cipher = Fernet(key)
                return
            except Exception:
                pass
                
        # Generate new key from master password or env
        password = os.environ.get("JARVIS_VAULT_PASSWORD", "").encode()
        if not password:
            # Generate a random key for first run
            key = Fernet.generate_key()
        else:
            # Derive key from password
            salt = b'jarvis_vault_salt_v1'  # In production, use random salt per user
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
        self._cipher = Fernet(key)
        
        # Save key file (in production, use keyring)
        if self._keyring_available:
            try:
                keyring.set_password("jarvis", "vault_key", key.decode())
            except Exception:
                pass
        else:
            _KEY_FILE.write_bytes(key)
            
    def encrypt(self, data: str) -> str:
        """Encrypt a string."""
        if not self._cipher:
            raise RuntimeError("Cipher not initialized")
        return self._cipher.encrypt(data.encode()).decode()
        
    def decrypt(self, encrypted: str) -> str:
        """Decrypt a string."""
        if not self._cipher:
            raise RuntimeError("Cipher not initialized")
        return self._cipher.decrypt(encrypted.encode()).decode()
        
    def store(self, key: str, value: str, metadata: Dict = None):
        """Store a credential."""
        vault = self._load_vault()
        vault[key] = {
            "value": self.encrypt(value),
            "metadata": metadata or {},
            "created": datetime.now(timezone.utc).isoformat()
        }
        self._save_vault(vault)
        
    def get(self, key: str) -> Optional[str]:
        """Retrieve and decrypt a credential."""
        vault = self._load_vault()
        if key not in vault:
            return None
        try:
            return self.decrypt(vault[key]["value"])
        except Exception:
            return None
            
    def get_metadata(self, key: str) -> Optional[Dict]:
        vault = self._load_vault()
        return vault.get(key, {}).get("metadata")
        
    def delete(self, key: str) -> bool:
        vault = self._load_vault()
        if key in vault:
            del vault[key]
            self._save_vault(vault)
            return True
        return False
        
    def list_keys(self) -> list:
        vault = self._load_vault()
        return list(vault.keys())
        
    def _load_vault(self) -> Dict:
        if _VAULT_FILE.exists():
            try:
                return json.loads(_VAULT_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}
        
    def _save_vault(self, vault: Dict):
        _VAULT_FILE.write_text(json.dumps(vault, indent=2), encoding="utf-8")
        
    def store_in_keyring(self, service: str, username: str, password: str):
        """Store in OS keyring if available."""
        if self._keyring_available:
            keyring.set_password(service, username, password)
            
    def get_from_keyring(self, service: str, username: str) -> Optional[str]:
        if self._keyring_available:
            try:
                return keyring.get_password(service, username)
            except Exception:
                return None
        return None

# Global singleton
_vault: Optional[CredentialVault] = None

def get_vault() -> CredentialVault:
    global _vault
    if _vault is None:
        _vault = CredentialVault()
    return _vault

def store_credential(key: str, value: str, metadata: Dict = None):
    get_vault().store(key, value, metadata)

def get_credential(key: str) -> Optional[str]:
    return get_vault().get(key)

def delete_credential(key: str) -> bool:
    return get_vault().delete(key)

def list_credentials() -> list:
    return get_vault().list_keys()