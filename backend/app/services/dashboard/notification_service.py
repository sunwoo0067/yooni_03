"""
알림 서비스
실시간 알림 생성 및 관리
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import asyncio
from enum import Enum

from app.models.notification import Notification
from app.models.user import User
from app.services.cache_service import CacheService
from app.core.logging import logger


class NotificationType(Enum):
    """알림 타입"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CELEBRATION = "celebration"
    AI = "ai"
    OPPORTUNITY = "opportunity"


class NotificationPriority(Enum):
    """알림 우선순위"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationService:
    """알림 서비스"""
    
    def __init__(self):
        self.cache = CacheService()
        
    async def create_notification(
        self,
        user_id: int,
        notification_data: Dict[str, Any],
        db: Session
    ) -> Notification:
        """알림 생성"""
        try:
            # 알림 객체 생성
            notification = Notification(
                user_id=user_id,
                type=notification_data.get("type", NotificationType.INFO.value),
                title=notification_data.get("title"),
                message=notification_data.get("message"),
                priority=notification_data.get("priority", NotificationPriority.MEDIUM.value),
                data=notification_data.get("data", {}),
                action=notification_data.get("action"),
                is_read=False,
                created_at=datetime.now()
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # 캐시 업데이트
            await self._update_notification_cache(user_id, notification)
            
            # 알림 집계 업데이트
            await self._update_notification_stats(user_id)
            
            logger.info(f"알림 생성 완료: user_id={user_id}, notification_id={notification.id}")
            
            return notification
            
        except Exception as e:
            logger.error(f"알림 생성 실패: {str(e)}")
            db.rollback()
            raise
            
    async def get_notifications(
        self,
        db: Session,
        user_id: int,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
        priority: Optional[str] = None,
        notification_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """알림 목록 조회"""
        try:
            # 기본 쿼리
            query = db.query(Notification).filter(
                Notification.user_id == user_id
            )
            
            # 필터 적용
            if unread_only:
                query = query.filter(Notification.is_read == False)
                
            if priority:
                query = query.filter(Notification.priority == priority)
                
            if notification_type:
                query = query.filter(Notification.type == notification_type)
                
            # 전체 개수
            total_count = query.count()
            
            # 정렬 및 페이징
            notifications = query.order_by(
                desc(Notification.created_at)
            ).limit(limit).offset(offset).all()
            
            # 미읽음 개수
            unread_count = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).count()
            
            # 우선순위별 개수
            priority_counts = self._get_priority_counts(db, user_id)
            
            return {
                "notifications": [self._serialize_notification(n) for n in notifications],
                "total_count": total_count,
                "unread_count": unread_count,
                "priority_counts": priority_counts,
                "has_more": offset + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"알림 목록 조회 실패: {str(e)}")
            raise
            
    async def mark_as_read(
        self,
        db: Session,
        user_id: int,
        notification_ids: List[int]
    ) -> int:
        """알림 읽음 처리"""
        try:
            # 알림 업데이트
            updated = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids),
                Notification.is_read == False
            ).update(
                {
                    "is_read": True,
                    "read_at": datetime.now()
                },
                synchronize_session=False
            )
            
            db.commit()
            
            # 캐시 업데이트
            if updated > 0:
                await self._update_notification_stats(user_id)
                
            logger.info(f"알림 읽음 처리: user_id={user_id}, count={updated}")
            
            return updated
            
        except Exception as e:
            logger.error(f"알림 읽음 처리 실패: {str(e)}")
            db.rollback()
            raise
            
    async def mark_all_as_read(
        self,
        db: Session,
        user_id: int
    ) -> int:
        """모든 알림 읽음 처리"""
        try:
            # 모든 미읽음 알림 업데이트
            updated = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).update(
                {
                    "is_read": True,
                    "read_at": datetime.now()
                },
                synchronize_session=False
            )
            
            db.commit()
            
            # 캐시 업데이트
            if updated > 0:
                await self._update_notification_stats(user_id)
                
            logger.info(f"모든 알림 읽음 처리: user_id={user_id}, count={updated}")
            
            return updated
            
        except Exception as e:
            logger.error(f"모든 알림 읽음 처리 실패: {str(e)}")
            db.rollback()
            raise
            
    async def delete_notifications(
        self,
        db: Session,
        user_id: int,
        notification_ids: List[int]
    ) -> int:
        """알림 삭제"""
        try:
            # 알림 삭제
            deleted = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids)
            ).delete(synchronize_session=False)
            
            db.commit()
            
            # 캐시 업데이트
            if deleted > 0:
                await self._update_notification_stats(user_id)
                
            logger.info(f"알림 삭제: user_id={user_id}, count={deleted}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"알림 삭제 실패: {str(e)}")
            db.rollback()
            raise
            
    async def get_notification_settings(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """알림 설정 조회"""
        try:
            # 사용자 설정 조회
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
                
            # 기본 설정
            default_settings = {
                "email_notifications": True,
                "push_notifications": True,
                "sms_notifications": False,
                "notification_types": {
                    "order": True,
                    "inventory": True,
                    "price": True,
                    "sales": True,
                    "ai_insights": True,
                    "market_trends": True
                },
                "quiet_hours": {
                    "enabled": False,
                    "start": "22:00",
                    "end": "08:00"
                },
                "priority_filter": {
                    "low": True,
                    "medium": True,
                    "high": True,
                    "critical": True
                }
            }
            
            # 사용자 설정과 병합
            user_settings = user.notification_settings or {}
            settings = {**default_settings, **user_settings}
            
            return settings
            
        except Exception as e:
            logger.error(f"알림 설정 조회 실패: {str(e)}")
            raise
            
    async def update_notification_settings(
        self,
        db: Session,
        user_id: int,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """알림 설정 업데이트"""
        try:
            # 사용자 조회
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError(f"사용자를 찾을 수 없습니다: {user_id}")
                
            # 설정 업데이트
            user.notification_settings = settings
            db.commit()
            
            logger.info(f"알림 설정 업데이트: user_id={user_id}")
            
            return settings
            
        except Exception as e:
            logger.error(f"알림 설정 업데이트 실패: {str(e)}")
            db.rollback()
            raise
            
    async def create_bulk_notifications(
        self,
        db: Session,
        notifications: List[Dict[str, Any]]
    ) -> List[Notification]:
        """대량 알림 생성"""
        try:
            created_notifications = []
            
            for notif_data in notifications:
                notification = Notification(
                    user_id=notif_data.get("user_id"),
                    type=notif_data.get("type", NotificationType.INFO.value),
                    title=notif_data.get("title"),
                    message=notif_data.get("message"),
                    priority=notif_data.get("priority", NotificationPriority.MEDIUM.value),
                    data=notif_data.get("data", {}),
                    action=notif_data.get("action"),
                    is_read=False,
                    created_at=datetime.now()
                )
                db.add(notification)
                created_notifications.append(notification)
                
            db.commit()
            
            # 사용자별 캐시 업데이트
            user_ids = list(set(n.user_id for n in created_notifications))
            for user_id in user_ids:
                await self._update_notification_stats(user_id)
                
            logger.info(f"대량 알림 생성 완료: count={len(created_notifications)}")
            
            return created_notifications
            
        except Exception as e:
            logger.error(f"대량 알림 생성 실패: {str(e)}")
            db.rollback()
            raise
            
    async def get_notification_summary(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """알림 요약 정보"""
        try:
            # 캐시 확인
            cache_key = f"notifications:summary:{user_id}"
            cached_summary = await self.cache.get(cache_key)
            if cached_summary:
                return cached_summary
                
            # 미읽음 알림 수
            unread_count = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).count()
            
            # 최근 알림 (최대 5개)
            recent_notifications = db.query(Notification).filter(
                Notification.user_id == user_id
            ).order_by(
                desc(Notification.created_at)
            ).limit(5).all()
            
            # 우선순위별 미읽음 수
            priority_counts = self._get_priority_counts(db, user_id, unread_only=True)
            
            # 타입별 미읽음 수
            type_counts = self._get_type_counts(db, user_id, unread_only=True)
            
            summary = {
                "unread_count": unread_count,
                "recent_notifications": [
                    self._serialize_notification(n) for n in recent_notifications
                ],
                "priority_breakdown": priority_counts,
                "type_breakdown": type_counts,
                "has_critical": priority_counts.get("critical", 0) > 0
            }
            
            # 캐시 저장
            await self.cache.set(cache_key, summary, ttl=60)
            
            return summary
            
        except Exception as e:
            logger.error(f"알림 요약 조회 실패: {str(e)}")
            raise
            
    def _get_priority_counts(
        self,
        db: Session,
        user_id: int,
        unread_only: bool = False
    ) -> Dict[str, int]:
        """우선순위별 알림 수"""
        try:
            query = db.query(Notification).filter(
                Notification.user_id == user_id
            )
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
                
            counts = {}
            for priority in NotificationPriority:
                count = query.filter(
                    Notification.priority == priority.value
                ).count()
                counts[priority.value] = count
                
            return counts
            
        except Exception as e:
            logger.error(f"우선순위별 알림 수 조회 실패: {str(e)}")
            return {}
            
    def _get_type_counts(
        self,
        db: Session,
        user_id: int,
        unread_only: bool = False
    ) -> Dict[str, int]:
        """타입별 알림 수"""
        try:
            query = db.query(Notification).filter(
                Notification.user_id == user_id
            )
            
            if unread_only:
                query = query.filter(Notification.is_read == False)
                
            counts = {}
            for notif_type in NotificationType:
                count = query.filter(
                    Notification.type == notif_type.value
                ).count()
                counts[notif_type.value] = count
                
            return counts
            
        except Exception as e:
            logger.error(f"타입별 알림 수 조회 실패: {str(e)}")
            return {}
            
    def _serialize_notification(self, notification: Notification) -> Dict[str, Any]:
        """알림 직렬화"""
        return {
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority,
            "data": notification.data,
            "action": notification.action,
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "created_at": notification.created_at.isoformat()
        }
        
    async def _update_notification_cache(
        self,
        user_id: int,
        notification: Notification
    ) -> None:
        """알림 캐시 업데이트"""
        try:
            # 최근 알림 캐시 업데이트
            cache_key = f"notifications:recent:{user_id}"
            recent = await self.cache.get(cache_key) or []
            
            recent.insert(0, self._serialize_notification(notification))
            recent = recent[:10]  # 최근 10개만 유지
            
            await self.cache.set(cache_key, recent, ttl=300)
            
        except Exception as e:
            logger.error(f"알림 캐시 업데이트 실패: {str(e)}")
            
    async def _update_notification_stats(self, user_id: int) -> None:
        """알림 통계 캐시 업데이트"""
        try:
            # 요약 정보 캐시 삭제 (다음 조회 시 재생성)
            cache_key = f"notifications:summary:{user_id}"
            await self.cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"알림 통계 캐시 업데이트 실패: {str(e)}")
            
    async def cleanup_old_notifications(
        self,
        db: Session,
        days: int = 30
    ) -> int:
        """오래된 알림 정리"""
        try:
            # 삭제 기준 날짜
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 읽은 알림 중 오래된 것 삭제
            deleted = db.query(Notification).filter(
                Notification.is_read == True,
                Notification.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            db.commit()
            
            logger.info(f"오래된 알림 정리 완료: deleted={deleted}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"오래된 알림 정리 실패: {str(e)}")
            db.rollback()
            raise