from django.shortcuts import render
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from source_data.models import SourceData
from context_management.models import ConversationContext, WorkflowContext


def dashboard(request):
    """메인 대시보드 뷰"""
    
    # 현재 시간 기준 통계
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # 소스 데이터 통계
    source_stats = {
        'total_count': SourceData.objects.count(),
        'today_count': SourceData.objects.filter(created_at__date=today).count(),
        'processing_count': SourceData.objects.filter(processing_status='processing').count(),
        'error_count': SourceData.objects.filter(processing_status='error').count(),
    }
    
    # 소스 타입별 통계
    source_by_type = SourceData.objects.values('source_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 시스템별 통계
    source_by_system = SourceData.objects.values('source_system').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 처리 상태별 통계
    processing_stats = SourceData.objects.values('processing_status').annotate(
        count=Count('id')
    )
    
    # 최근 데이터
    recent_data = SourceData.objects.order_by('-created_at')[:10]
    
    # 워크플로우 통계
    workflow_stats = {
        'total_executions': WorkflowContext.objects.count(),
        'today_executions': WorkflowContext.objects.filter(created_at__date=today).count(),
        'week_executions': WorkflowContext.objects.filter(created_at__gte=week_ago).count(),
    }
    
    # 워크플로우별 실행 횟수
    workflow_by_name = WorkflowContext.objects.values('workflow_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # AI 대화 통계
    conversation_stats = {
        'total_conversations': ConversationContext.objects.count(),
        'active_conversations': ConversationContext.objects.filter(is_active=True).count(),
        'today_conversations': ConversationContext.objects.filter(created_at__date=today).count(),
    }
    
    # 대화 타입별 통계
    conversation_by_type = ConversationContext.objects.values('context_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 시간대별 데이터 생성 추이 (최근 7일)
    daily_trend = []
    for i in range(7):
        date = now - timedelta(days=i)
        count = SourceData.objects.filter(
            created_at__date=date.date()
        ).count()
        daily_trend.append({
            'date': date.date(),
            'count': count
        })
    daily_trend.reverse()
    
    context = {
        'source_stats': source_stats,
        'source_by_type': source_by_type,
        'source_by_system': source_by_system,
        'processing_stats': processing_stats,
        'recent_data': recent_data,
        'workflow_stats': workflow_stats,
        'workflow_by_name': workflow_by_name,
        'conversation_stats': conversation_stats,
        'conversation_by_type': conversation_by_type,
        'daily_trend': daily_trend,
        'now': now,
    }
    
    return render(request, 'dashboard.html', context)