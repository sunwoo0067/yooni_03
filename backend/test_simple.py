"""
Simple test to verify basic functionality
"""
import pytest
from app.utils.encryption import EncryptionManager
from app.utils.product_utils import calculate_margin, format_price


def test_encryption():
    """Test encryption"""
    manager = EncryptionManager()
    data = "test_data"
    encrypted = manager.encrypt(data)
    decrypted = manager.decrypt(encrypted)
    assert decrypted == data
    print("✓ Encryption test passed")


def test_product_utils():
    """Test product utilities"""
    margin = calculate_margin(cost=1000, price=1500)
    assert margin == 33.33
    
    formatted = format_price(1234567, currency="KRW")
    assert formatted == "₩1,234,567"
    print("✓ Product utils test passed")


def test_imports():
    """Test critical imports"""
    from app.core.config import settings
    from app.models.base import BaseModel
    from app.services.ai import AIManager
    print("✓ Import test passed")


if __name__ == "__main__":
    test_encryption()
    test_product_utils()
    test_imports()
    print("\n✅ All basic tests passed!")