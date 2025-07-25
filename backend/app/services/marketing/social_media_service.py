"""
소셜미디어 마케팅 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import httpx
import asyncio
import json

from app.models.marketing import SocialMediaPost, MarketingCampaign
from app.core.config import settings
from app.core.exceptions import BusinessException
from app.services.ai.ai_manager import AIManager


class SocialMediaService:
    """소셜미디어 자동 포스팅 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
        self.platform_configs = {
            'facebook': {
                'api_url': 'https://graph.facebook.com/v18.0',
                'token': settings.FACEBOOK_ACCESS_TOKEN,
                'page_id': settings.FACEBOOK_PAGE_ID
            },
            'instagram': {
                'api_url': 'https://graph.facebook.com/v18.0',
                'token': settings.INSTAGRAM_ACCESS_TOKEN,
                'account_id': settings.INSTAGRAM_ACCOUNT_ID
            },
            'twitter': {
                'api_url': 'https://api.twitter.com/2',
                'bearer_token': settings.TWITTER_BEARER_TOKEN
            }
        }
    
    async def create_social_post(self, post_data: Dict[str, Any]) -> SocialMediaPost:
        """소셜미디어 게시물 생성"""
        try:
            post = SocialMediaPost(
                platform=post_data['platform'],
                post_type=post_data.get('post_type', 'text'),
                content=post_data['content'],
                media_urls=post_data.get('media_urls', []),
                hashtags=post_data.get('hashtags', []),
                mentions=post_data.get('mentions', []),
                scheduled_at=post_data.get('scheduled_at'),
                status='draft' if not post_data.get('scheduled_at') else 'scheduled'
            )
            
            # 캠페인 연결
            if 'campaign_id' in post_data:
                post.campaign_id = post_data['campaign_id']
            
            # AI를 통한 콘텐츠 최적화
            if post_data.get('optimize_content'):
                post.content = await self._optimize_content_with_ai(
                    post.content, 
                    post.platform,
                    post.hashtags
                )
            
            self.db.add(post)
            self.db.commit()
            self.db.refresh(post)
            
            # 즉시 게시인 경우
            if post_data.get('publish_now'):
                await self.publish_post(post.id)
            
            return post
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"소셜미디어 게시물 생성 실패: {str(e)}")
    
    async def publish_post(self, post_id: int) -> Dict[str, Any]:
        """게시물 발행"""
        try:
            post = self.db.query(SocialMediaPost).filter(
                SocialMediaPost.id == post_id
            ).first()
            
            if not post:
                raise BusinessException("게시물을 찾을 수 없습니다")
            
            if post.status == 'published':
                raise BusinessException("이미 발행된 게시물입니다")
            
            # 플랫폼별 게시
            result = await self._publish_to_platform(post)
            
            if result['success']:
                post.status = 'published'
                post.published_at = datetime.utcnow()
                post.platform_post_id = result.get('post_id')
                
                self.db.commit()
                
                # 초기 참여 지표 수집 (비동기)
                asyncio.create_task(self._collect_initial_metrics(post.id))
                
                return {
                    'success': True,
                    'post_id': post.id,
                    'platform_post_id': result.get('post_id'),
                    'url': result.get('url')
                }
            else:
                post.status = 'failed'
                self.db.commit()
                
                return {
                    'success': False,
                    'error': result.get('error', '게시 실패')
                }
                
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"게시물 발행 실패: {str(e)}")
    
    async def schedule_posts(self, posts_data: List[Dict[str, Any]]) -> List[SocialMediaPost]:
        """대량 게시물 스케줄링"""
        try:
            scheduled_posts = []
            
            for post_data in posts_data:
                # 스케줄 시간 설정
                if not post_data.get('scheduled_at'):
                    # 자동 스케줄링 (최적 시간대 활용)
                    post_data['scheduled_at'] = await self._get_optimal_posting_time(
                        post_data['platform']
                    )
                
                post = await self.create_social_post(post_data)
                scheduled_posts.append(post)
            
            return scheduled_posts
            
        except Exception as e:
            raise BusinessException(f"게시물 스케줄링 실패: {str(e)}")
    
    async def update_post_metrics(self, post_id: int) -> SocialMediaPost:
        """게시물 지표 업데이트"""
        try:
            post = self.db.query(SocialMediaPost).filter(
                SocialMediaPost.id == post_id
            ).first()
            
            if not post:
                raise BusinessException("게시물을 찾을 수 없습니다")
            
            if post.status != 'published' or not post.platform_post_id:
                return post
            
            # 플랫폼에서 지표 가져오기
            metrics = await self._fetch_platform_metrics(post)
            
            # 지표 업데이트
            post.likes_count = metrics.get('likes', 0)
            post.comments_count = metrics.get('comments', 0)
            post.shares_count = metrics.get('shares', 0)
            post.reach_count = metrics.get('reach', 0)
            
            # 참여율 계산
            if post.reach_count > 0:
                total_engagement = post.likes_count + post.comments_count + post.shares_count
                post.engagement_rate = (total_engagement / post.reach_count) * 100
            
            post.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(post)
            
            return post
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"지표 업데이트 실패: {str(e)}")
    
    async def generate_content_variations(self, base_content: str, 
                                        platforms: List[str],
                                        count: int = 3) -> List[Dict[str, Any]]:
        """AI를 활용한 콘텐츠 변형 생성"""
        try:
            variations = []
            
            for platform in platforms:
                # 플랫폼별 특성 고려
                platform_context = {
                    'platform': platform,
                    'character_limit': self._get_character_limit(platform),
                    'hashtag_limit': self._get_hashtag_limit(platform),
                    'style': self._get_platform_style(platform)
                }
                
                # AI를 통한 변형 생성
                for i in range(count):
                    variation = await self.ai_manager.generate_social_content(
                        base_content=base_content,
                        context=platform_context,
                        variation_index=i
                    )
                    
                    variations.append({
                        'platform': platform,
                        'content': variation['content'],
                        'hashtags': variation.get('hashtags', []),
                        'estimated_engagement': variation.get('engagement_score', 0)
                    })
            
            return variations
            
        except Exception as e:
            raise BusinessException(f"콘텐츠 변형 생성 실패: {str(e)}")
    
    async def analyze_competitor_posts(self, competitor_accounts: List[str],
                                     days: int = 7) -> Dict[str, Any]:
        """경쟁사 게시물 분석"""
        try:
            analysis = {
                'competitors': [],
                'top_performing_content': [],
                'posting_patterns': {},
                'content_themes': [],
                'recommendations': []
            }
            
            # 각 경쟁사 분석
            for account in competitor_accounts:
                competitor_data = await self._analyze_competitor_account(account, days)
                analysis['competitors'].append(competitor_data)
            
            # 통합 인사이트 생성
            analysis['insights'] = self._generate_competitive_insights(analysis['competitors'])
            
            return analysis
            
        except Exception as e:
            raise BusinessException(f"경쟁사 분석 실패: {str(e)}")
    
    async def get_social_media_calendar(self, start_date: datetime,
                                      end_date: datetime) -> Dict[str, Any]:
        """소셜미디어 캘린더 조회"""
        try:
            posts = self.db.query(SocialMediaPost).filter(
                SocialMediaPost.scheduled_at.between(start_date, end_date)
            ).order_by(SocialMediaPost.scheduled_at).all()
            
            # 날짜별 그룹화
            calendar = {}
            for post in posts:
                date_key = post.scheduled_at.date().isoformat() if post.scheduled_at else 'unscheduled'
                
                if date_key not in calendar:
                    calendar[date_key] = []
                
                calendar[date_key].append({
                    'id': post.id,
                    'platform': post.platform,
                    'type': post.post_type,
                    'content_preview': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                    'scheduled_time': post.scheduled_at.time().isoformat() if post.scheduled_at else None,
                    'status': post.status
                })
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'calendar': calendar,
                'statistics': {
                    'total_posts': len(posts),
                    'by_platform': self._count_by_platform(posts),
                    'by_status': self._count_by_status(posts)
                }
            }
            
        except Exception as e:
            raise BusinessException(f"캘린더 조회 실패: {str(e)}")
    
    async def _publish_to_platform(self, post: SocialMediaPost) -> Dict[str, Any]:
        """플랫폼별 게시 처리"""
        try:
            if post.platform == 'facebook':
                return await self._publish_to_facebook(post)
            elif post.platform == 'instagram':
                return await self._publish_to_instagram(post)
            elif post.platform == 'twitter':
                return await self._publish_to_twitter(post)
            else:
                raise BusinessException(f"지원하지 않는 플랫폼: {post.platform}")
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _publish_to_facebook(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Facebook 게시"""
        try:
            config = self.platform_configs['facebook']
            
            # 게시물 데이터 준비
            post_data = {
                'message': self._format_content_for_platform(post, 'facebook'),
                'access_token': config['token']
            }
            
            # 이미지/비디오 추가
            if post.media_urls and post.post_type in ['image', 'video']:
                if post.post_type == 'image':
                    post_data['url'] = post.media_urls[0]
                else:
                    # 비디오 업로드는 별도 처리 필요
                    pass
            
            # API 호출
            async with httpx.AsyncClient() as client:
                if post.post_type == 'image' and post.media_urls:
                    endpoint = f"{config['api_url']}/{config['page_id']}/photos"
                else:
                    endpoint = f"{config['api_url']}/{config['page_id']}/feed"
                
                response = await client.post(endpoint, data=post_data)
                
                if response.status_code == 200:
                    result = response.json()
                    return {
                        'success': True,
                        'post_id': result.get('id'),
                        'url': f"https://www.facebook.com/{result.get('id')}"
                    }
                else:
                    return {
                        'success': False,
                        'error': response.text
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _publish_to_instagram(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Instagram 게시"""
        try:
            config = self.platform_configs['instagram']
            
            # Instagram은 이미지/비디오 필수
            if not post.media_urls:
                return {
                    'success': False,
                    'error': 'Instagram은 이미지 또는 비디오가 필요합니다'
                }
            
            # 미디어 컨테이너 생성
            container_data = {
                'image_url': post.media_urls[0],
                'caption': self._format_content_for_platform(post, 'instagram'),
                'access_token': config['token']
            }
            
            async with httpx.AsyncClient() as client:
                # 1. 미디어 컨테이너 생성
                container_response = await client.post(
                    f"{config['api_url']}/{config['account_id']}/media",
                    params=container_data
                )
                
                if container_response.status_code != 200:
                    return {
                        'success': False,
                        'error': container_response.text
                    }
                
                container_id = container_response.json().get('id')
                
                # 2. 미디어 게시
                publish_data = {
                    'creation_id': container_id,
                    'access_token': config['token']
                }
                
                publish_response = await client.post(
                    f"{config['api_url']}/{config['account_id']}/media_publish",
                    params=publish_data
                )
                
                if publish_response.status_code == 200:
                    result = publish_response.json()
                    return {
                        'success': True,
                        'post_id': result.get('id'),
                        'url': f"https://www.instagram.com/p/{result.get('id')}"
                    }
                else:
                    return {
                        'success': False,
                        'error': publish_response.text
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _publish_to_twitter(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Twitter 게시"""
        try:
            config = self.platform_configs['twitter']
            
            # 트윗 데이터 준비
            tweet_data = {
                'text': self._format_content_for_platform(post, 'twitter')
            }
            
            # 미디어 업로드 (별도 처리 필요)
            if post.media_urls:
                # Twitter 미디어 업로드 API 사용
                pass
            
            headers = {
                'Authorization': f'Bearer {config["bearer_token"]}',
                'Content-Type': 'application/json'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config['api_url']}/tweets",
                    headers=headers,
                    json=tweet_data
                )
                
                if response.status_code == 201:
                    result = response.json()
                    tweet_id = result['data']['id']
                    return {
                        'success': True,
                        'post_id': tweet_id,
                        'url': f"https://twitter.com/i/web/status/{tweet_id}"
                    }
                else:
                    return {
                        'success': False,
                        'error': response.text
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_content_for_platform(self, post: SocialMediaPost, platform: str) -> str:
        """플랫폼별 콘텐츠 포맷팅"""
        content = post.content
        
        # 해시태그 추가
        if post.hashtags:
            hashtag_text = ' '.join([f'#{tag}' for tag in post.hashtags])
            content = f"{content}\n\n{hashtag_text}"
        
        # 멘션 추가
        if post.mentions:
            if platform == 'twitter':
                mention_text = ' '.join([f'@{mention}' for mention in post.mentions])
            else:
                mention_text = ' '.join([f'@{mention}' for mention in post.mentions])
            content = f"{mention_text} {content}"
        
        # 플랫폼별 글자 수 제한
        char_limit = self._get_character_limit(platform)
        if len(content) > char_limit:
            content = content[:char_limit-3] + '...'
        
        return content
    
    async def _fetch_platform_metrics(self, post: SocialMediaPost) -> Dict[str, Any]:
        """플랫폼에서 지표 가져오기"""
        try:
            if post.platform == 'facebook':
                return await self._fetch_facebook_metrics(post)
            elif post.platform == 'instagram':
                return await self._fetch_instagram_metrics(post)
            elif post.platform == 'twitter':
                return await self._fetch_twitter_metrics(post)
            else:
                return {}
                
        except Exception as e:
            print(f"지표 가져오기 실패: {str(e)}")
            return {}
    
    async def _fetch_facebook_metrics(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Facebook 지표 가져오기"""
        try:
            config = self.platform_configs['facebook']
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config['api_url']}/{post.platform_post_id}",
                    params={
                        'fields': 'likes.summary(true),comments.summary(true),shares,reactions.summary(true)',
                        'access_token': config['token']
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'likes': data.get('likes', {}).get('summary', {}).get('total_count', 0),
                        'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
                        'shares': data.get('shares', {}).get('count', 0),
                        'reactions': data.get('reactions', {}).get('summary', {}).get('total_count', 0)
                    }
                    
        except Exception as e:
            print(f"Facebook 지표 가져오기 실패: {str(e)}")
            
        return {}
    
    async def _fetch_instagram_metrics(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Instagram 지표 가져오기"""
        try:
            config = self.platform_configs['instagram']
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config['api_url']}/{post.platform_post_id}",
                    params={
                        'fields': 'like_count,comments_count,impressions,reach',
                        'access_token': config['token']
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'likes': data.get('like_count', 0),
                        'comments': data.get('comments_count', 0),
                        'reach': data.get('reach', 0),
                        'impressions': data.get('impressions', 0)
                    }
                    
        except Exception as e:
            print(f"Instagram 지표 가져오기 실패: {str(e)}")
            
        return {}
    
    async def _fetch_twitter_metrics(self, post: SocialMediaPost) -> Dict[str, Any]:
        """Twitter 지표 가져오기"""
        try:
            config = self.platform_configs['twitter']
            
            headers = {
                'Authorization': f'Bearer {config["bearer_token"]}'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{config['api_url']}/tweets/{post.platform_post_id}",
                    headers=headers,
                    params={
                        'tweet.fields': 'public_metrics'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    metrics = data.get('data', {}).get('public_metrics', {})
                    return {
                        'likes': metrics.get('like_count', 0),
                        'comments': metrics.get('reply_count', 0),
                        'shares': metrics.get('retweet_count', 0),
                        'impressions': metrics.get('impression_count', 0)
                    }
                    
        except Exception as e:
            print(f"Twitter 지표 가져오기 실패: {str(e)}")
            
        return {}
    
    async def _optimize_content_with_ai(self, content: str, platform: str,
                                      hashtags: List[str]) -> str:
        """AI를 통한 콘텐츠 최적화"""
        try:
            optimized = await self.ai_manager.optimize_social_content(
                content=content,
                platform=platform,
                existing_hashtags=hashtags,
                tone='professional_friendly'
            )
            
            return optimized.get('content', content)
            
        except Exception as e:
            print(f"AI 최적화 실패: {str(e)}")
            return content
    
    async def _get_optimal_posting_time(self, platform: str) -> datetime:
        """최적 게시 시간 계산"""
        # 플랫폼별 최적 시간대 (한국 기준)
        optimal_hours = {
            'facebook': [12, 14, 19, 20],  # 점심, 오후 2시, 저녁 7-8시
            'instagram': [11, 13, 19, 21],  # 오전 11시, 점심, 저녁
            'twitter': [8, 12, 17, 21]      # 출근, 점심, 퇴근, 밤
        }
        
        # 다음 최적 시간 찾기
        now = datetime.now()
        platform_hours = optimal_hours.get(platform, [12, 19])
        
        for hour in platform_hours:
            target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target_time > now:
                return target_time
        
        # 모든 시간이 지났으면 다음날 첫 시간
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=platform_hours[0], minute=0, second=0, microsecond=0)
    
    async def _collect_initial_metrics(self, post_id: int):
        """초기 지표 수집 (비동기)"""
        # 1시간 후 첫 지표 수집
        await asyncio.sleep(3600)
        await self.update_post_metrics(post_id)
    
    def _get_character_limit(self, platform: str) -> int:
        """플랫폼별 글자 수 제한"""
        limits = {
            'facebook': 63206,
            'instagram': 2200,
            'twitter': 280
        }
        return limits.get(platform, 1000)
    
    def _get_hashtag_limit(self, platform: str) -> int:
        """플랫폼별 해시태그 제한"""
        limits = {
            'facebook': 30,
            'instagram': 30,
            'twitter': 10
        }
        return limits.get(platform, 10)
    
    def _get_platform_style(self, platform: str) -> str:
        """플랫폼별 콘텐츠 스타일"""
        styles = {
            'facebook': 'informative_engaging',
            'instagram': 'visual_storytelling',
            'twitter': 'concise_timely'
        }
        return styles.get(platform, 'general')
    
    async def _analyze_competitor_account(self, account: str, days: int) -> Dict[str, Any]:
        """경쟁사 계정 분석"""
        # 실제 구현에서는 각 플랫폼 API를 통해 데이터 수집
        return {
            'account': account,
            'posts_count': 42,
            'avg_engagement_rate': 3.5,
            'top_posts': [],
            'posting_frequency': 'daily',
            'content_types': ['image', 'video', 'carousel']
        }
    
    def _generate_competitive_insights(self, competitors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """경쟁 분석 인사이트 생성"""
        return {
            'average_engagement': 3.2,
            'best_posting_times': ['14:00', '20:00'],
            'trending_hashtags': ['#드랍쉬핑', '#온라인쇼핑', '#할인'],
            'content_recommendations': [
                '비디오 콘텐츠 비중을 늘리세요',
                '사용자 생성 콘텐츠를 활용하세요',
                '스토리 기능을 더 활용하세요'
            ]
        }
    
    def _count_by_platform(self, posts: List[SocialMediaPost]) -> Dict[str, int]:
        """플랫폼별 게시물 수 계산"""
        counts = {}
        for post in posts:
            counts[post.platform] = counts.get(post.platform, 0) + 1
        return counts
    
    def _count_by_status(self, posts: List[SocialMediaPost]) -> Dict[str, int]:
        """상태별 게시물 수 계산"""
        counts = {}
        for post in posts:
            counts[post.status] = counts.get(post.status, 0) + 1
        return counts