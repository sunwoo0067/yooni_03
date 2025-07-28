"""
Dashboard Schemas
"""
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum

class MetricPeriod(str, Enum):
    HOUR_1 = "1h"
    HOURS_24 = "24h"
    DAYS_7 = "7d"
    DAYS_30 = "30d"

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"

class OrderMetrics(BaseModel):
    total: int
    by_status: Dict[str, int]
    growth_rate: float
    pending: int
    processing: int
    shipped: int
    delivered: int
    cancelled: int

class ProductMetrics(BaseModel):
    active: int
    new: int
    out_of_stock: int
    low_stock: int
    total: int

class RevenueMetrics(BaseModel):
    total: float
    average_order_value: float
    growth_rate: float
    currency: str = "KRW"

class PlatformMetrics(BaseModel):
    orders: int
    revenue: float
    active_accounts: Optional[int] = None

class AIUsageMetrics(BaseModel):
    total_calls: int
    total_tokens: int
    by_service: Dict[str, Dict[str, Any]]

class InventoryMetrics(BaseModel):
    total_value: float
    total_skus: int
    currency: str = "KRW"

class APIPerformanceMetrics(BaseModel):
    avg_response_time: float
    uptime: float
    requests_per_minute: int

class DashboardMetrics(BaseModel):
    period: str
    timestamp: datetime
    orders: OrderMetrics
    products: ProductMetrics
    revenue: RevenueMetrics
    platforms: Dict[str, PlatformMetrics]
    ai_usage: AIUsageMetrics
    inventory: InventoryMetrics
    error_rate: float
    api_performance: APIPerformanceMetrics
    alerts_count: int

class ServiceHealth(BaseModel):
    name: str
    status: str
    response_time: Optional[float] = None
    error_rate: Optional[float] = None
    last_check: datetime

class DatabaseHealth(BaseModel):
    status: str
    connections: int
    max_connections: int
    response_time: float

class RedisHealth(BaseModel):
    status: str
    memory_usage: float
    connected_clients: int
    response_time: float

class ExternalAPIHealth(BaseModel):
    name: str
    status: str
    response_time: Optional[float] = None
    last_success: Optional[datetime] = None

class SystemHealth(BaseModel):
    status: str
    services: List[ServiceHealth]
    database: DatabaseHealth
    redis: RedisHealth
    external_apis: List[ExternalAPIHealth]
    last_check: datetime

class DailyMetric(BaseModel):
    date: str
    orders: int
    revenue: float

class CategoryMetric(BaseModel):
    category: str
    orders: int
    revenue: float

class CustomerMetrics(BaseModel):
    total_customers: int
    repeat_rate: float
    new_customers: int

class BusinessMetrics(BaseModel):
    daily_revenue: List[DailyMetric]
    top_categories: List[CategoryMetric]
    customer_metrics: CustomerMetrics
    conversion_rate: float

class ResponseTimeMetric(BaseModel):
    timestamp: datetime
    value: float
    service: Optional[str] = None

class ResourceUsage(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]

class PerformanceMetrics(BaseModel):
    response_times: List[ResponseTimeMetric]
    error_rates: Dict[str, float]
    throughput: Dict[str, int]
    resource_usage: ResourceUsage
    service_specific: Optional[Dict[str, Any]] = None

class AlertResponse(BaseModel):
    id: str
    type: str
    severity: AlertSeverity
    message: str
    source: str
    status: AlertStatus
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    service: str
    level: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class ExportRequest(BaseModel):
    data_type: str = Field(..., description="Type of data to export: orders, products, revenue")
    format: ExportFormat
    start_date: datetime
    end_date: datetime

class RealtimeMetrics(BaseModel):
    timestamp: datetime
    requests_per_minute: int
    active_users: int
    recent_orders: int
    error_rate: float
    system_status: str

class ChartDataPoint(BaseModel):
    timestamp: str
    value: float

class TopProduct(BaseModel):
    id: int
    name: str
    sku: str
    category: str
    price: float
    orders: int
    revenue: float

class RevenueBreakdown(BaseModel):
    by_platform: List[Dict[str, Any]]
    by_category: List[Dict[str, Any]]
    period: str