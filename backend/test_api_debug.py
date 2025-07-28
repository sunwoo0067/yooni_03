#!/usr/bin/env python3
"""
API 디버깅을 위한 상세 테스트
"""

import os
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def test_ownerclan_detailed():
    """오너클랜 상세 테스트"""
    print("\n" + "=" * 60)
    print("오너클랜 API 상세 테스트")
    print("=" * 60)
    
    username = os.getenv('OWNERCLAN_USERNAME')
    password = os.getenv('OWNERCLAN_PASSWORD')
    
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'None'}")
    
    # Production URL 테스트
    print("\n[1] Production URL 테스트")
    auth_url = 'https://auth.ownerclan.com/auth'
    
    auth_data = {
        "service": "ownerclan",
        "userType": "seller",
        "username": username,
        "password": password
    }
    
    print(f"URL: {auth_url}")
    print(f"Data: {auth_data}")
    
    try:
        response = requests.post(auth_url, json=auth_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Raw response
        print(f"\nRaw Response (first 1000 chars):")
        print(response.text[:1000])
        
        # Try to parse JSON
        try:
            data = response.json()
            print(f"\nParsed JSON: {data}")
        except:
            print("\nFailed to parse as JSON")
            
    except Exception as e:
        print(f"Error: {e}")
    
    # Sandbox URL 테스트
    print("\n[2] Sandbox URL 테스트")
    auth_url = 'https://auth-sandbox.ownerclan.com/auth'
    
    print(f"URL: {auth_url}")
    
    try:
        response = requests.post(auth_url, json=auth_data, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        print(f"\nRaw Response (first 1000 chars):")
        print(response.text[:1000])
        
        try:
            data = response.json()
            print(f"\nParsed JSON: {data}")
        except:
            print("\nFailed to parse as JSON")
            
    except Exception as e:
        print(f"Error: {e}")


def test_domeggook_detailed():
    """도매꾹 상세 테스트"""
    print("\n" + "=" * 60)
    print("도매꾹 API 상세 테스트")
    print("=" * 60)
    
    api_key = os.getenv('DOMEGGOOK_API_KEY')
    print(f"API Key: {api_key}")
    
    # 카테고리 API 테스트
    print("\n[1] 카테고리 API 테스트")
    url = "https://openapi.domeggook.com/api/category/list"
    params = {
        'version': '1.0',
        'api_key': api_key
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        print(f"\nRaw Response (first 1000 chars):")
        print(response.text[:1000])
        
    except Exception as e:
        print(f"Error: {e}")
    
    # 다른 가능한 URL들 테스트
    print("\n[2] 대체 URL 테스트")
    
    alternate_urls = [
        "https://api.domeggook.com/category/list",
        "https://www.domeggook.com/api/category/list",
        "http://openapi.domeggook.com/api/category/list"
    ]
    
    for alt_url in alternate_urls:
        print(f"\nTrying: {alt_url}")
        try:
            response = requests.get(alt_url, params=params, timeout=5)
            print(f"Status Code: {response.status_code}")
            if response.status_code != 404:
                print("Found working URL!")
                print(response.text[:500])
        except Exception as e:
            print(f"Error: {e}")


def test_zentrade_detailed():
    """젠트레이드 상세 테스트"""
    print("\n" + "=" * 60)
    print("젠트레이드 API 상세 테스트")
    print("=" * 60)
    
    api_id = os.getenv('ZENTRADE_API_KEY')
    api_secret = os.getenv('ZENTRADE_API_SECRET')
    
    print(f"API ID: {api_id}")
    print(f"API Secret: {api_secret}")
    
    # 상품 API 테스트
    print("\n[1] 상품 API 테스트")
    url = "https://www.zentrade.co.kr/shop/proc/product_api.php"
    
    params = {
        'id': api_id,
        'm_skey': api_secret
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Encoding: {response.encoding}")
        
        print(f"\nRaw Response (first 1000 chars):")
        # Try different encodings
        try:
            content = response.content.decode('euc-kr')
            print("Successfully decoded as EUC-KR")
            print(content[:1000])
        except:
            try:
                content = response.text
                print("Using default encoding")
                print(content[:1000])
            except:
                print("Failed to decode response")
                print(response.content[:1000])
                
    except Exception as e:
        print(f"Error: {e}")


def main():
    """메인 함수"""
    print("API 디버깅 테스트 시작")
    
    # 각 API별 상세 테스트
    test_ownerclan_detailed()
    test_domeggook_detailed()
    test_zentrade_detailed()
    
    print("\n테스트 완료")


if __name__ == "__main__":
    main()