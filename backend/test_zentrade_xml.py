#!/usr/bin/env python3
"""
젠트레이드 XML API 테스트
"""

import os
import sys
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()


def test_zentrade_xml():
    """젠트레이드 XML API 상세 테스트"""
    
    api_id = os.getenv('ZENTRADE_API_KEY')
    api_key = os.getenv('ZENTRADE_API_SECRET')
    
    print("젠트레이드 XML API 테스트")
    print("=" * 60)
    print(f"API ID: {api_id}")
    print(f"API Key: {api_key}")
    
    # API 호출
    url = "https://www.zentrade.co.kr/shop/proc/product_api.php"
    params = {
        'id': api_id,
        'm_skey': api_key
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/xml,application/xml',
    }
    
    print(f"\nURL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            # EUC-KR로 디코딩 시도
            try:
                content = response.content.decode('euc-kr')
                print("\n[✓] EUC-KR 디코딩 성공")
                
                # XML 파싱 시도
                try:
                    root = ET.fromstring(content)
                    print(f"[✓] XML 파싱 성공")
                    print(f"Root tag: {root.tag}")
                    print(f"Root attributes: {root.attrib}")
                    
                    # 상품 정보 추출
                    products = []
                    product_elements = root.findall('product')
                    
                    print(f"\n찾은 상품 수: {len(product_elements)}개")
                    
                    for idx, product in enumerate(product_elements[:5]):  # 처음 5개만
                        code = product.get('code')
                        
                        # 상품명
                        name_elem = product.find('prdtname')
                        name = name_elem.text.strip() if name_elem is not None and name_elem.text else 'N/A'
                        
                        # 가격
                        price_elem = product.find('price')
                        price = price_elem.get('buyprice', '0') if price_elem is not None else '0'
                        
                        # 상태
                        status_elem = product.find('status')
                        runout = status_elem.get('runout', '0') if status_elem is not None else '0'
                        
                        print(f"\n상품 {idx + 1}:")
                        print(f"  코드: {code}")
                        print(f"  이름: {name}")
                        print(f"  가격: {price}원")
                        print(f"  품절여부: {'품절' if runout == '1' else '정상'}")
                        
                        products.append({
                            'code': code,
                            'name': name,
                            'price': int(price) if price.isdigit() else 0,
                            'runout': runout
                        })
                    
                    return products
                    
                except ET.ParseError as e:
                    print(f"\n[✗] XML 파싱 오류: {e}")
                    print("\nXML 내용 (처음 1000자):")
                    print(content[:1000])
                    
            except UnicodeDecodeError:
                # UTF-8로 재시도
                try:
                    content = response.content.decode('utf-8')
                    print("\n[!] UTF-8 디코딩으로 재시도")
                    print(f"내용 (처음 500자): {content[:500]}")
                except:
                    print("\n[✗] 디코딩 실패")
                    print(f"Raw bytes (처음 200): {response.content[:200]}")
                    
        elif response.status_code == 400:
            print("\n[✗] 400 Bad Request - 요청이 차단되었습니다")
            print("HTML 응답:")
            print(response.text[:500])
            
    except Exception as e:
        print(f"\n[✗] 오류 발생: {e}")
        
    return []


def main():
    """메인 함수"""
    products = test_zentrade_xml()
    
    if products:
        print(f"\n\n총 {len(products)}개 상품 수집 성공!")
        
        # 결과 저장
        import json
        with open('zentrade_products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print("결과 파일: zentrade_products.json")
    else:
        print("\n\n상품 수집 실패")


if __name__ == "__main__":
    main()