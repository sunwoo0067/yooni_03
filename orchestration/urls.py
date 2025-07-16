"""
URL patterns for the orchestration app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'orchestration'

# API router
router = DefaultRouter()
router.register(r'workflows', views.WorkflowViewSet)
router.register(r'executions', views.WorkflowExecutionViewSet)
router.register(r'schedules', views.WorkflowScheduleViewSet)

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Workflow execution endpoints
    path('api/workflows/<int:workflow_id>/execute/', 
         views.execute_workflow, name='execute_workflow'),
    path('api/workflows/execute/<str:workflow_code>/', 
         views.execute_workflow_by_code, name='execute_workflow_by_code'),
    
    # Template endpoints
    path('api/templates/', views.workflow_templates, name='workflow_templates'),
    path('api/templates/<str:template_name>/create/', 
         views.create_from_template, name='create_from_template'),
    
    # Monitoring endpoints
    path('api/stats/', views.workflow_stats, name='workflow_stats'),
    path('api/health/', views.health_check, name='health_check'),
]