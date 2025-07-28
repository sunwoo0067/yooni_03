# Operations Dashboard Guide

## Overview

The Operations Dashboard is a comprehensive real-time monitoring and analytics platform for the dropshipping system. It provides insights into business performance, system health, and operational metrics.

## Features

### 1. Real-time Metrics Visualization
- **Live Updates**: WebSocket-based real-time data streaming
- **Interactive Charts**: Responsive charts with Chart.js
- **Performance Indicators**: Key metrics displayed in cards with trend indicators

### 2. System Health Monitoring
- **Service Status**: Monitor all internal and external services
- **Resource Usage**: CPU, Memory, Disk, and Network monitoring
- **Database Health**: Connection pool stats and response times
- **External API Status**: Monitor third-party service availability

### 3. Business Metrics
- **Revenue Analytics**: Daily revenue trends and growth rates
- **Order Analytics**: Order status distribution and trends
- **Customer Insights**: Repeat rate, conversion rate, customer lifetime value
- **Platform Performance**: Compare performance across different marketplaces

### 4. Performance Metrics
- **Response Times**: Track API response times with percentiles
- **Throughput**: Monitor requests per minute by service
- **Error Rates**: Track and alert on error rate increases
- **Resource Optimization**: Identify performance bottlenecks

### 5. Alert Management
- **Real-time Alerts**: Instant notifications for critical issues
- **Alert Categories**: System errors, performance degradation, business metrics
- **Alert Actions**: Acknowledge and resolve alerts with notes
- **Alert History**: Track all past alerts and resolutions

### 6. Log Aggregation
- **Centralized Logs**: View logs from all services in one place
- **Advanced Filtering**: Filter by service, level, and search terms
- **Real-time Updates**: Auto-scrolling log viewer
- **Export Capability**: Export logs for analysis

### 7. Export Functionality
- **Multiple Formats**: CSV, Excel, JSON export options
- **Date Range Selection**: Export data for specific periods
- **Data Types**: Orders, Products, Revenue, All Metrics
- **Secure Downloads**: Time-limited download links

## Technical Architecture

### Backend Components

1. **API Endpoints** (`backend/app/api/v1/endpoints/operations_dashboard.py`)
   - `/api/v1/dashboard/metrics` - Dashboard metrics
   - `/api/v1/dashboard/health` - System health
   - `/api/v1/dashboard/business-metrics` - Business analytics
   - `/api/v1/dashboard/performance` - Performance metrics
   - `/api/v1/dashboard/alerts` - Alert management
   - `/api/v1/dashboard/logs` - Log aggregation
   - `/api/v1/dashboard/export` - Data export
   - `/api/v1/dashboard/ws/{user_id}` - WebSocket endpoint

2. **Services**
   - `OperationsDashboardService` - Main dashboard business logic
   - `HealthChecker` - System health monitoring
   - `AlertManager` - Alert creation and management
   - `MetricsCollector` - Metrics aggregation

3. **WebSocket Manager**
   - Real-time data streaming
   - Channel-based subscriptions
   - Automatic reconnection with exponential backoff
   - Heartbeat monitoring

### Frontend Components

1. **Main Dashboard** (`frontend/src/pages/Dashboard/OperationsDashboard.tsx`)
   - Responsive layout with navigation drawer
   - Tab-based navigation
   - Real-time connection status indicator

2. **Component Library**
   - `MetricsOverview` - Key metrics and trends
   - `SystemHealthMonitor` - Service health visualization
   - `BusinessMetrics` - Business analytics charts
   - `PerformanceMetrics` - Performance monitoring
   - `AlertsPanel` - Alert management interface
   - `LogViewer` - Real-time log streaming
   - `ExportDialog` - Data export interface
   - `RealtimeChart` - Real-time chart component

3. **Custom Hooks**
   - `useWebSocket` - WebSocket connection management
   - `useDashboardData` - Dashboard data fetching and caching

## Usage Guide

### Accessing the Dashboard

1. Navigate to `/dashboard` in your application
2. The dashboard will automatically connect to WebSocket for real-time updates
3. Use the navigation drawer to switch between different views

### Understanding Metrics

#### Overview Metrics
- **Total Revenue**: Sum of all completed orders
- **Total Orders**: Count of all orders in the selected period
- **Active Products**: Products currently available for sale
- **API Performance**: Average response time and requests per minute

#### System Health Indicators
- 🟢 **Healthy**: All systems operational
- 🟡 **Degraded**: Some issues but functional
- 🔴 **Unhealthy**: Critical issues requiring attention

### Managing Alerts

1. **View Alerts**: Click the notification bell icon
2. **Filter Alerts**: Use severity and status filters
3. **Acknowledge**: Mark alert as seen
4. **Resolve**: Mark alert as fixed with resolution notes

### Exporting Data

1. Click the "Export Data" button
2. Select data type (Orders, Products, Revenue, All Metrics)
3. Choose format (CSV, Excel, JSON)
4. Select date range
5. Click "Export" to generate download link

### Performance Optimization Tips

1. **Monitor Error Rates**: Keep error rate below 1%
2. **Watch Response Times**: Target < 200ms average
3. **Check Resource Usage**: Keep CPU < 80%, Memory < 85%
4. **Review Slow Queries**: Optimize database queries > 100ms

## Alert Rules

The system automatically creates alerts based on these conditions:

| Alert Type | Condition | Severity |
|------------|-----------|----------|
| High Error Rate | Error rate > 5% | Critical |
| Slow Response Time | Avg response > 1s | Warning |
| Low Stock | > 10 products low stock | Warning |
| DB Connection Limit | Connections > 90% of max | Warning |
| High Memory Usage | Memory > 85% | Warning |
| API Failures | > 5 failures | Critical |

## Best Practices

1. **Regular Monitoring**
   - Check dashboard daily for trends
   - Review alerts promptly
   - Monitor resource usage during peak times

2. **Proactive Maintenance**
   - Address warnings before they become critical
   - Schedule maintenance during low-traffic periods
   - Keep services updated

3. **Data Analysis**
   - Export data weekly/monthly for trend analysis
   - Compare metrics across different periods
   - Identify seasonal patterns

4. **Alert Management**
   - Don't ignore repeated alerts
   - Document resolution steps
   - Update alert rules based on patterns

## Troubleshooting

### WebSocket Connection Issues
- Check network connectivity
- Verify authentication token
- Look for CORS errors in browser console

### Missing Data
- Verify backend services are running
- Check Redis connection
- Review API response in Network tab

### Performance Issues
- Reduce data point frequency
- Limit chart animations
- Use pagination for large datasets

## Security Considerations

1. **Authentication**: All dashboard endpoints require authentication
2. **Data Privacy**: Sensitive data is encrypted in transit
3. **Export Security**: Download links expire after 1 hour
4. **WebSocket Security**: Connections use secure tokens

## Future Enhancements

- Machine learning-based anomaly detection
- Predictive analytics for inventory management
- Custom dashboard layouts
- Mobile application
- Integration with external monitoring tools