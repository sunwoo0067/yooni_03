from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from .models import SourceData, DataLineage


@admin.register(SourceData)
class SourceDataAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'source_type_colored', 
        'source_system', 
        'source_id', 
        'processing_status_colored', 
        'version',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'source_type',
        'source_system',
        'processing_status',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'source_id',
        'source_system',
        'workflow_id'
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'formatted_raw_data',
        'formatted_normalized_data',
        'formatted_market_data',
        'formatted_ai_data'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'id',
                'source_type',
                'source_system',
                'source_id',
                'version'
            )
        }),
        ('처리 상태', {
            'fields': (
                'processing_status',
                'workflow_id'
            )
        }),
        ('원본 데이터', {
            'fields': ('formatted_raw_data',),
            'classes': ('collapse',)
        }),
        ('정규화 데이터', {
            'fields': ('formatted_normalized_data',),
            'classes': ('collapse',)
        }),
        ('마켓 데이터', {
            'fields': ('formatted_market_data',),
            'classes': ('collapse',)
        }),
        ('AI 처리 데이터', {
            'fields': ('formatted_ai_data',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def source_type_colored(self, obj):
        colors = {
            'supplier_product': '#3B82F6',  # blue
            'market_listing': '#10B981',    # green
            'order': '#F59E0B',             # amber
            'inventory': '#8B5CF6',         # violet
            'pricing': '#EF4444',           # red
            'customer': '#EC4899',          # pink
            'analytics': '#6B7280',         # gray
        }
        color = colors.get(obj.source_type, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_source_type_display()
        )
    source_type_colored.short_description = '소스 타입'
    
    def processing_status_colored(self, obj):
        colors = {
            'raw': '#6B7280',        # gray
            'processing': '#3B82F6',  # blue
            'processed': '#10B981',   # green
            'error': '#EF4444',      # red
            'archived': '#9CA3AF',   # light gray
        }
        color = colors.get(obj.processing_status, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_processing_status_display()
        )
    processing_status_colored.short_description = '처리 상태'
    
    def formatted_raw_data(self, obj):
        return self._format_json_field(obj.raw_data)
    formatted_raw_data.short_description = '원본 데이터 (JSON)'
    
    def formatted_normalized_data(self, obj):
        return self._format_json_field(obj.normalized_data)
    formatted_normalized_data.short_description = '정규화 데이터 (JSON)'
    
    def formatted_market_data(self, obj):
        return self._format_json_field(obj.market_data)
    formatted_market_data.short_description = '마켓 데이터 (JSON)'
    
    def formatted_ai_data(self, obj):
        return self._format_json_field(obj.ai_data)
    formatted_ai_data.short_description = 'AI 처리 데이터 (JSON)'
    
    def _format_json_field(self, data):
        if not data:
            return '-'
        
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        # HTML로 변환하고 스타일 적용
        html = f'''
        <div style="background-color: #f3f4f6; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; max-height: 400px; overflow-y: auto;">
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">{formatted}</pre>
        </div>
        '''
        return mark_safe(html)
    
    class Media:
        css = {
            'all': ('admin/css/source_data.css',)
        }


@admin.register(DataLineage)
class DataLineageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'parent_info',
        'child_info',
        'transformation_type',
        'created_at'
    ]
    
    list_filter = [
        'transformation_type',
        'created_at'
    ]
    
    search_fields = [
        'parent__source_id',
        'child__source_id',
        'transformation_type'
    ]
    
    readonly_fields = [
        'created_at',
        'formatted_transformation_metadata'
    ]
    
    def parent_info(self, obj):
        return f"{obj.parent.source_system} - {obj.parent.source_id}"
    parent_info.short_description = '부모 데이터'
    
    def child_info(self, obj):
        return f"{obj.child.source_system} - {obj.child.source_id}"
    child_info.short_description = '자식 데이터'
    
    def formatted_transformation_metadata(self, obj):
        if not obj.transformation_metadata:
            return '-'
        
        formatted = json.dumps(obj.transformation_metadata, indent=2, ensure_ascii=False)
        return mark_safe(f'<pre>{formatted}</pre>')
    formatted_transformation_metadata.short_description = '변환 메타데이터'