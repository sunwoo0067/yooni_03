#!/usr/bin/env python3
"""
빠른 API 테스트
"""

import requests
import json

BASE_URL = "http://localhost:8003"

print("Quick API Test")
print("=" * 40)

# 1. Health Check
print("\n1. Health Check:")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=3)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# 2. Root endpoint
print("\n2. Root endpoint:")
try:
    response = requests.get(BASE_URL, timeout=3)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# 3. Products
print("\n3. Products:")
try:
    response = requests.get(f"{BASE_URL}/api/v1/products", timeout=3)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        products = response.json()
        print(f"Number of products: {len(products)}")
except Exception as e:
    print(f"Error: {e}")

# 4. Dashboard Stats
print("\n4. Dashboard Stats:")
try:
    response = requests.get(f"{BASE_URL}/api/v1/dashboard/stats", timeout=3)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"Stats: {json.dumps(stats, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 40)
print("Test completed!")
print("\nNOTE: 서버가 실행 중이어야 합니다.")
print("서버 실행: cd backend && python simple_main.py")