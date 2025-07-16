"""
Views for the orchestration app.
"""
import json
from typing import Dict, Any

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Workflow, WorkflowExecution, WorkflowSchedule
from .serializers import (
    WorkflowSerializer, WorkflowExecutionSerializer, 
    WorkflowScheduleSerializer
)
from .engine import WorkflowEngine
from .workflows import WORKFLOW_TEMPLATES, create_workflow_from_template


class WorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for Workflow model."""
    
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter workflows based on query parameters."""
        queryset = super().get_queryset()
        
        workflow_type = self.request.query_params.get('type')
        status_filter = self.request.query_params.get('status')
        
        if workflow_type:
            queryset = queryset.filter(workflow_type=workflow_type)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WorkflowExecution model (read-only)."""
    
    queryset = WorkflowExecution.objects.all()
    serializer_class = WorkflowExecutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter executions based on query parameters."""
        queryset = super().get_queryset()
        
        workflow_id = self.request.query_params.get('workflow')
        status_filter = self.request.query_params.get('status')
        
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


class WorkflowScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for WorkflowSchedule model."""
    
    queryset = WorkflowSchedule.objects.all()
    serializer_class = WorkflowScheduleSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_workflow(request, workflow_id):
    """Execute a workflow by ID."""
    try:
        workflow = get_object_or_404(Workflow, id=workflow_id)
        
        # Get input data from request
        input_data = request.data.get('input_data', {})
        
        # Create engine and execute
        engine = WorkflowEngine()
        
        try:
            execution = engine.execute_workflow(
                workflow=workflow,
                input_data=input_data,
                triggered_by=request.user,
                trigger_type='api'
            )
            
            return Response({
                'success': True,
                'execution_id': execution.execution_id,
                'status': execution.status,
                'workflow_name': workflow.name
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        finally:
            engine.shutdown()
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_workflow_by_code(request, workflow_code):
    """Execute a workflow by code."""
    try:
        workflow = get_object_or_404(Workflow, code=workflow_code)
        
        # Get input data from request
        input_data = request.data.get('input_data', {})
        
        # Create engine and execute
        engine = WorkflowEngine()
        
        try:
            execution = engine.execute_workflow(
                workflow=workflow,
                input_data=input_data,
                triggered_by=request.user,
                trigger_type='api'
            )
            
            return Response({
                'success': True,
                'execution_id': execution.execution_id,
                'status': execution.status,
                'workflow_name': workflow.name
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        finally:
            engine.shutdown()
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workflow_templates(request):
    """Get available workflow templates."""
    templates = []
    
    for template_name, template_class in WORKFLOW_TEMPLATES.items():
        templates.append({
            'name': template_name,
            'type': template_class.get_workflow_type(),
            'description': template_class.get_description(),
            'steps_count': len(template_class.get_steps_config())
        })
    
    return Response({'templates': templates})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_from_template(request, template_name):
    """Create a workflow from a template."""
    try:
        # Get parameters
        name = request.data.get('name')
        description = request.data.get('description', '')
        
        if not name:
            return Response({
                'success': False,
                'error': 'Workflow name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create workflow
        workflow = create_workflow_from_template(
            template_name=template_name,
            name=name,
            description=description,
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'workflow_id': workflow.id,
            'workflow_code': workflow.code,
            'workflow_name': workflow.name,
            'steps_created': workflow.steps.count()
        })
    
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workflow_stats(request):
    """Get workflow statistics."""
    try:
        # Overall stats
        total_workflows = Workflow.objects.count()
        active_workflows = Workflow.objects.filter(status='active').count()
        total_executions = WorkflowExecution.objects.count()
        running_executions = WorkflowExecution.objects.filter(status='running').count()
        
        # Success rate
        completed_executions = WorkflowExecution.objects.filter(status='completed').count()
        failed_executions = WorkflowExecution.objects.filter(status='failed').count()
        
        success_rate = 0
        if total_executions > 0:
            success_rate = (completed_executions / total_executions) * 100
        
        # Workflow type breakdown
        workflow_types = {}
        for workflow in Workflow.objects.all():
            wtype = workflow.workflow_type
            if wtype not in workflow_types:
                workflow_types[wtype] = {
                    'count': 0,
                    'executions': 0,
                    'success_rate': 0
                }
            workflow_types[wtype]['count'] += 1
            workflow_types[wtype]['executions'] += workflow.total_executions
            
            if workflow.total_executions > 0:
                workflow_types[wtype]['success_rate'] = (
                    workflow.successful_executions / workflow.total_executions
                ) * 100
        
        # Recent executions
        recent_executions = WorkflowExecution.objects.order_by('-created_at')[:10]
        recent_data = []
        
        for execution in recent_executions:
            recent_data.append({
                'execution_id': execution.execution_id,
                'workflow_name': execution.workflow.name,
                'status': execution.status,
                'created_at': execution.created_at.isoformat(),
                'duration_seconds': execution.duration_seconds
            })
        
        return Response({
            'total_workflows': total_workflows,
            'active_workflows': active_workflows,
            'total_executions': total_executions,
            'running_executions': running_executions,
            'completed_executions': completed_executions,
            'failed_executions': failed_executions,
            'success_rate': round(success_rate, 2),
            'workflow_types': workflow_types,
            'recent_executions': recent_data
        })
    
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """Health check endpoint."""
    try:
        # Check database connectivity
        workflow_count = Workflow.objects.count()
        
        return Response({
            'status': 'healthy',
            'workflows_count': workflow_count,
            'timestamp': timezone.now().isoformat()
        })
    
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
