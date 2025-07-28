"""
Integration test to verify all components work together
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Running integration tests...")

# Test 1: Configuration
try:
    from app.core.config import settings
    print("[OK] Configuration loaded successfully")
    print(f"  - Environment: {settings.ENVIRONMENT}")
    print(f"  - Debug mode: {settings.DEBUG}")
except Exception as e:
    print(f"[FAIL] Configuration failed: {e}")

# Test 2: Database Models
try:
    from app.models import User, Product, Order
    print("[OK] Database models imported successfully")
except Exception as e:
    print(f"[FAIL] Database models failed: {e}")

# Test 3: Services
try:
    from app.services.ai import AIManager
    from app.services.platforms.platform_manager import PlatformManager
    print("[OK] Core services imported successfully")
except Exception as e:
    print(f"[FAIL] Services import failed: {e}")

# Test 4: API Endpoints
try:
    from app.api.v1 import router
    print("[OK] API endpoints loaded successfully")
except Exception as e:
    print(f"[FAIL] API endpoints failed: {e}")

# Test 5: Utilities
try:
    from app.utils.validators import validate_email
    from app.utils.text_utils import slugify
    print("[OK] Utilities imported successfully")
except Exception as e:
    print(f"[FAIL] Utilities failed: {e}")

print("\nIntegration test completed!")
print("=" * 50)

# Run pytest on available tests
import subprocess
print("\nRunning pytest on test_utils...")
result = subprocess.run([sys.executable, "-m", "pytest", "tests/test_utils/", "-v", "--tb=short", "-q"], 
                       capture_output=True, text=True)
print(f"Test result: {result.returncode}")
if result.returncode == 0:
    print("[SUCCESS] All utility tests passed!")
else:
    print("[ERROR] Some tests failed")
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)