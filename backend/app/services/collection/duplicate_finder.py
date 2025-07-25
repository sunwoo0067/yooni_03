"""중복 상품 검색 엔진"""
import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ...models.product import Product
from ...models.dropshipping import DuplicateProductGroup, DuplicateProduct
from ...crud.base import CRUDBase


class DuplicateFinder:
    """중복 상품 검색 엔진"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.vectorizer = None
        self._initialize_vectorizer()
        
    def _initialize_vectorizer(self):
        """TF-IDF 벡터라이저 초기화"""
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=5000,
            lowercase=True
        )
        
    def find_duplicates(
        self,
        product: Product,
        threshold: float = 0.7,
        max_candidates: int = 50
    ) -> List[Tuple[Product, float]]:
        """상품의 중복 후보를 찾아 반환"""
        candidates = []
        
        # 1. 상품명 유사도 검색
        name_candidates = self._find_by_name_similarity(
            product,
            threshold=threshold,
            max_results=max_candidates
        )
        candidates.extend(name_candidates)
        
        # 2. 키워드 기반 검색
        keyword_candidates = self._find_by_keywords(
            product,
            max_results=max_candidates // 2
        )
        
        # 3. 모델명/SKU 기반 검색
        if product.model_name or product.sku:
            model_candidates = self._find_by_model(
                product,
                max_results=max_candidates // 3
            )
            keyword_candidates.extend(model_candidates)
            
        # 중복 제거 및 점수 재계산
        unique_candidates = self._merge_candidates(
            candidates + keyword_candidates,
            product
        )
        
        # 최종 점수 기준 정렬
        unique_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return unique_candidates[:max_candidates]
        
    def _find_by_name_similarity(
        self,
        product: Product,
        threshold: float = 0.7,
        max_results: int = 50
    ) -> List[Tuple[Product, float]]:
        """상품명 유사도 기반 검색"""
        # 같은 카테고리의 활성 상품들 조회
        query = self.db.query(Product).filter(
            Product.id != product.id,
            Product.is_active == True
        )
        
        if product.category_id:
            query = query.filter(Product.category_id == product.category_id)
            
        candidates = query.limit(1000).all()
        
        if not candidates:
            return []
            
        # 상품명 전처리
        product_name = self._preprocess_name(product.name)
        candidate_names = [self._preprocess_name(c.name) for c in candidates]
        
        # TF-IDF 벡터화
        all_names = candidate_names + [product_name]
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_names)
            
            # 코사인 유사도 계산
            similarities = cosine_similarity(
                tfidf_matrix[-1:],
                tfidf_matrix[:-1]
            ).flatten()
            
            # 임계값 이상인 상품 선택
            results = []
            for i, similarity in enumerate(similarities):
                if similarity >= threshold:
                    results.append((candidates[i], float(similarity)))
                    
            # 유사도 순으로 정렬
            results.sort(key=lambda x: x[1], reverse=True)
            
            return results[:max_results]
            
        except Exception as e:
            self.logger.error(f"TF-IDF 벡터화 실패: {str(e)}")
            return []
            
    def _find_by_keywords(
        self,
        product: Product,
        max_results: int = 25
    ) -> List[Tuple[Product, float]]:
        """키워드 기반 검색"""
        # 상품명에서 키워드 추출
        keywords = self._extract_keywords(product.name)
        
        if not keywords:
            return []
            
        # 키워드를 포함하는 상품 검색
        query = self.db.query(Product).filter(
            Product.id != product.id,
            Product.is_active == True
        )
        
        # OR 조건으로 키워드 검색
        keyword_conditions = []
        for keyword in keywords[:5]:  # 상위 5개 키워드만 사용
            keyword_conditions.append(Product.name.ilike(f'%{keyword}%'))
            
        query = query.filter(or_(*keyword_conditions))
        
        if product.category_id:
            query = query.filter(Product.category_id == product.category_id)
            
        candidates = query.limit(max_results * 2).all()
        
        # 키워드 매칭 점수 계산
        results = []
        for candidate in candidates:
            score = self._calculate_keyword_score(
                keywords,
                self._extract_keywords(candidate.name)
            )
            if score > 0.3:
                results.append((candidate, score))
                
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:max_results]
        
    def _find_by_model(
        self,
        product: Product,
        max_results: int = 20
    ) -> List[Tuple[Product, float]]:
        """모델명/SKU 기반 검색"""
        conditions = []
        
        if product.model_name:
            conditions.append(Product.model_name == product.model_name)
            
        if product.sku:
            conditions.append(Product.sku == product.sku)
            
        if not conditions:
            return []
            
        query = self.db.query(Product).filter(
            Product.id != product.id,
            Product.is_active == True,
            or_(*conditions)
        )
        
        candidates = query.limit(max_results).all()
        
        # 모델명/SKU 일치는 높은 점수 부여
        results = []
        for candidate in candidates:
            score = 0.9  # 기본 높은 점수
            
            # 상품명도 유사하면 점수 추가
            name_similarity = self._calculate_simple_similarity(
                product.name,
                candidate.name
            )
            score = min(1.0, score + name_similarity * 0.1)
            
            results.append((candidate, score))
            
        return results
        
    def _merge_candidates(
        self,
        candidates: List[Tuple[Product, float]],
        original_product: Product
    ) -> List[Tuple[Product, float]]:
        """중복 제거 및 최종 점수 계산"""
        unique_products = {}
        
        for product, score in candidates:
            if product.id not in unique_products:
                # 추가 특징 비교로 점수 조정
                final_score = self._calculate_final_score(
                    original_product,
                    product,
                    score
                )
                unique_products[product.id] = (product, final_score)
            else:
                # 더 높은 점수로 업데이트
                _, existing_score = unique_products[product.id]
                if score > existing_score:
                    final_score = self._calculate_final_score(
                        original_product,
                        product,
                        score
                    )
                    unique_products[product.id] = (product, final_score)
                    
        return list(unique_products.values())
        
    def _calculate_final_score(
        self,
        product1: Product,
        product2: Product,
        base_score: float
    ) -> float:
        """최종 유사도 점수 계산"""
        score = base_score
        
        # 가격 유사도 (20% 이내면 보너스)
        if product1.price and product2.price:
            price_ratio = min(product1.price, product2.price) / max(product1.price, product2.price)
            if price_ratio > 0.8:
                score += 0.1
                
        # 같은 도매처면 보너스
        if product1.wholesaler_id == product2.wholesaler_id:
            score += 0.05
            
        # 브랜드가 같으면 보너스
        if product1.brand and product2.brand:
            if product1.brand.lower() == product2.brand.lower():
                score += 0.1
                
        return min(1.0, score)
        
    def _preprocess_name(self, name: str) -> str:
        """상품명 전처리"""
        # 소문자 변환
        name = name.lower()
        
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        name = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', name)
        
        # 연속된 공백 제거
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()
        
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 전처리
        text = self._preprocess_name(text)
        
        # 단어 분리
        words = text.split()
        
        # 불용어 제거
        stopwords = {'은', '는', '이', '가', '을', '를', '의', '에', '와', '과', '도', '로', '으로', '만', '라', '하'}
        
        keywords = []
        for word in words:
            # 2글자 이상, 불용어 아닌 단어
            if len(word) >= 2 and word not in stopwords:
                keywords.append(word)
                
        # 빈도순 정렬 (중복 제거)
        keyword_counts = {}
        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
        sorted_keywords = sorted(
            keyword_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [k for k, _ in sorted_keywords]
        
    def _calculate_keyword_score(
        self,
        keywords1: List[str],
        keywords2: List[str]
    ) -> float:
        """키워드 매칭 점수 계산"""
        if not keywords1 or not keywords2:
            return 0.0
            
        # 공통 키워드 개수
        common_keywords = set(keywords1) & set(keywords2)
        
        # Jaccard 유사도
        all_keywords = set(keywords1) | set(keywords2)
        
        if not all_keywords:
            return 0.0
            
        return len(common_keywords) / len(all_keywords)
        
    def _calculate_simple_similarity(self, text1: str, text2: str) -> float:
        """간단한 문자열 유사도 계산"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
    async def save_duplicate_group(
        self,
        products: List[Product],
        group_name: Optional[str] = None
    ) -> DuplicateProductGroup:
        """중복 상품 그룹 저장"""
        # 그룹 생성
        group = DuplicateProductGroup(
            group_name=group_name or f"중복그룹_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            matching_criteria={
                'method': 'similarity_search',
                'threshold': 0.7,
                'product_count': len(products)
            }
        )
        self.db.add(group)
        self.db.flush()
        
        # 상품들을 그룹에 추가
        for i, product in enumerate(products):
            duplicate_product = DuplicateProduct(
                group_id=group.id,
                product_id=product.id,
                similarity_score=1.0 if i == 0 else 0.8,  # 첫 번째 상품을 기준으로
                is_primary=i == 0
            )
            self.db.add(duplicate_product)
            
        self.db.commit()
        self.db.refresh(group)
        
        return group
        
    def find_all_duplicate_groups(
        self,
        threshold: float = 0.7,
        batch_size: int = 100
    ) -> List[DuplicateProductGroup]:
        """전체 상품에서 중복 그룹 찾기"""
        groups = []
        processed_ids = set()
        
        # 배치 단위로 상품 처리
        offset = 0
        while True:
            products = self.db.query(Product).filter(
                Product.is_active == True,
                ~Product.id.in_(processed_ids) if processed_ids else True
            ).offset(offset).limit(batch_size).all()
            
            if not products:
                break
                
            for product in products:
                if product.id in processed_ids:
                    continue
                    
                # 중복 찾기
                duplicates = self.find_duplicates(
                    product,
                    threshold=threshold,
                    max_candidates=20
                )
                
                if duplicates:
                    # 중복 그룹 생성
                    group_products = [product] + [dup[0] for dup in duplicates]
                    group = self.save_duplicate_group(group_products)
                    groups.append(group)
                    
                    # 처리된 상품 ID 추가
                    processed_ids.update([p.id for p in group_products])
                else:
                    processed_ids.add(product.id)
                    
            offset += batch_size
            
        self.logger.info(f"총 {len(groups)}개의 중복 그룹을 찾았습니다")
        
        return groups
        
    def get_duplicate_stats(self) -> Dict[str, Any]:
        """중복 통계 정보"""
        total_groups = self.db.query(DuplicateProductGroup).count()
        
        # 그룹별 상품 수 통계
        group_sizes = self.db.query(
            DuplicateProduct.group_id,
            self.db.func.count(DuplicateProduct.id).label('count')
        ).group_by(DuplicateProduct.group_id).all()
        
        size_distribution = {}
        for _, size in group_sizes:
            size_key = f"{size}개"
            size_distribution[size_key] = size_distribution.get(size_key, 0) + 1
            
        # 중복으로 인한 예상 절감액 (최저가 기준)
        potential_savings = 0
        for group in self.db.query(DuplicateProductGroup).all():
            products = self.db.query(Product).join(
                DuplicateProduct,
                Product.id == DuplicateProduct.product_id
            ).filter(
                DuplicateProduct.group_id == group.id
            ).all()
            
            if products:
                prices = [p.price for p in products if p.price]
                if len(prices) > 1:
                    potential_savings += max(prices) - min(prices)
                    
        return {
            'total_groups': total_groups,
            'size_distribution': size_distribution,
            'potential_savings': potential_savings,
            'average_group_size': sum(size for _, size in group_sizes) / len(group_sizes) if group_sizes else 0
        }