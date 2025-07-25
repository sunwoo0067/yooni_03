"""마케팅 자동화 서비스 패키지"""

from .campaign_manager import CampaignManager
from .email_service import EmailService
from .sms_service import SMSService
from .automation_engine import AutomationEngine
from .ab_testing_service import ABTestingService
from .personalization_engine import PersonalizationEngine
from .analytics_service import MarketingAnalyticsService
from .segmentation_service import SegmentationService
from .promotion_service import PromotionService
from .social_media_service import SocialMediaService
from .retargeting_service import RetargetingService

__all__ = [
    "CampaignManager",
    "EmailService",
    "SMSService",
    "AutomationEngine",
    "ABTestingService",
    "PersonalizationEngine",
    "MarketingAnalyticsService",
    "SegmentationService",
    "PromotionService",
    "SocialMediaService",
    "RetargetingService"
]