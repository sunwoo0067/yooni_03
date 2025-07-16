# Celery Configuration and Setup

This document describes the Celery configuration and task setup for the Django project.

## Overview

The project uses Celery for asynchronous task processing with Redis as the message broker. Tasks are organized into different queues for better resource management and monitoring.

## Architecture

### Task Queues

- **suppliers** - Supplier data synchronization tasks
- **marketplaces** - Marketplace data synchronization tasks  
- **workflows** - Workflow execution tasks
- **ai_processing** - AI agent processing tasks
- **analytics** - Analytics and reporting tasks
- **maintenance** - System maintenance and cleanup tasks

### Components

1. **Celery Workers** - Process tasks from queues
2. **Celery Beat** - Scheduler for periodic tasks
3. **Flower** - Web-based monitoring interface
4. **Redis** - Message broker and result backend

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install and start Redis:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   
   # macOS
   brew install redis
   brew services start redis
   ```

3. Run database migrations:
   ```bash
   python manage.py migrate
   ```

4. Set up periodic tasks:
   ```bash
   python manage.py setup_celery_beat
   ```

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Settings

Celery configuration is defined in `config/settings.py` and `config/celery.py`.

## Running Celery

### Using the Startup Script (Recommended)

```bash
# Start all services
./start_celery.sh start

# Check status
./start_celery.sh status

# Stop all services
./start_celery.sh stop

# Restart all services
./start_celery.sh restart
```

### Manual Commands

Start workers for specific queues:
```bash
# Supplier tasks
celery -A config worker --queues=suppliers --concurrency=2 --loglevel=info

# Marketplace tasks
celery -A config worker --queues=marketplaces --concurrency=3 --loglevel=info

# Workflow tasks
celery -A config worker --queues=workflows --concurrency=2 --loglevel=info

# AI processing tasks
celery -A config worker --queues=ai_processing --concurrency=1 --loglevel=info

# Analytics tasks
celery -A config worker --queues=analytics --concurrency=1 --loglevel=info

# Maintenance tasks
celery -A config worker --queues=maintenance --concurrency=1 --loglevel=info
```

Start Beat scheduler:
```bash
celery -A config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
```

Start Flower monitoring:
```bash
celery -A config flower --port=5555
```

## Available Tasks

### Supplier Tasks

- `suppliers.tasks.sync_all_suppliers` - Sync all active suppliers
- `suppliers.tasks.sync_supplier_products` - Sync products from specific supplier
- `suppliers.tasks.test_supplier_connection` - Test supplier API connection
- `suppliers.tasks.update_supplier_inventory` - Update inventory levels
- `suppliers.tasks.cleanup_supplier_data` - Clean up old supplier data

### Marketplace Tasks

- `marketplaces.tasks.sync_all_marketplace_orders` - Sync orders from all marketplaces
- `marketplaces.tasks.sync_all_marketplace_inventory` - Sync inventory to all marketplaces
- `marketplaces.tasks.sync_marketplace_listings` - Sync listings from specific marketplace
- `marketplaces.tasks.sync_marketplace_orders` - Sync orders from specific marketplace
- `marketplaces.tasks.fulfill_marketplace_order` - Mark order as fulfilled

### Workflow Tasks

- `orchestration.tasks.execute_workflow` - Execute a workflow
- `orchestration.tasks.schedule_workflow_executions` - Check for scheduled workflows
- `orchestration.tasks.retry_failed_workflow_execution` - Retry failed execution
- `orchestration.tasks.cleanup_old_executions` - Clean up old executions

### AI Agent Tasks

- `ai_agents.tasks.process_ai_task` - Process AI task
- `ai_agents.tasks.analyze_product_descriptions` - Analyze product descriptions
- `ai_agents.tasks.generate_marketplace_listings` - Generate optimized listings
- `ai_agents.tasks.analyze_customer_feedback` - Analyze customer sentiment

### Analytics Tasks

- `analytics.tasks.generate_daily_reports` - Generate daily reports
- `analytics.tasks.generate_supplier_performance_report` - Supplier performance report
- `analytics.tasks.generate_marketplace_performance_report` - Marketplace performance report
- `analytics.tasks.calculate_profitability_metrics` - Calculate profitability

### Core Maintenance Tasks

- `core.tasks.system_health_check` - System health monitoring
- `core.tasks.cleanup_system_logs` - Clean up log files
- `core.tasks.database_maintenance` - Database maintenance
- `core.tasks.backup_database` - Create database backup

## Management Commands

### Check Celery Status

```bash
python manage.py celery_status
python manage.py celery_status --format=json --detailed
```

### Run Tasks Manually

```bash
# List available tasks
python manage.py run_task --list-tasks

# Run task synchronously
python manage.py run_task system_health_check

# Run task asynchronously
python manage.py run_task sync_all_suppliers --async

# Run task with arguments
python manage.py run_task sync_supplier_products --args "[1]" --kwargs '{"force_full_sync": true}'
```

### Monitor Tasks

```bash
# Monitor for 60 seconds with 5-second intervals
python manage.py celery_monitor --duration=60 --interval=5

# Save monitoring data to file
python manage.py celery_monitor --output-file=monitoring.json

# Monitor specific workers
python manage.py celery_monitor --workers=suppliers,marketplaces
```

### Set Up Periodic Tasks

```bash
# Create default periodic tasks
python manage.py setup_celery_beat

# List current tasks
python manage.py setup_celery_beat --list

# Reset and recreate tasks
python manage.py setup_celery_beat --reset

# Enable/disable all tasks
python manage.py setup_celery_beat --enable-all
python manage.py setup_celery_beat --disable-all
```

## Monitoring

### Flower Web Interface

Access the Flower monitoring interface at: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Queue monitoring
- Resource usage graphs

### Logging

Celery logs are stored in the `logs/` directory:
- `celery_<queue_name>.log` - Worker logs for each queue
- `celery_beat.log` - Beat scheduler logs
- `flower.log` - Flower monitoring logs

### Health Checks

System health checks run every 5 minutes and monitor:
- Database connectivity
- Redis/Cache connectivity
- Disk space usage
- Memory usage
- CPU usage
- Celery worker status
- Log file sizes

## Scheduled Tasks

Default periodic tasks:

| Task | Schedule | Description |
|------|----------|-------------|
| Sync All Suppliers | Every hour | Synchronize supplier data |
| Sync Marketplace Orders | Every 15 minutes | Check for new orders |
| Sync Marketplace Inventory | Every 30 minutes | Update inventory levels |
| System Health Check | Every 5 minutes | Monitor system health |
| Generate Daily Reports | Daily at midnight | Create analytics reports |
| Clean Up Old Executions | Daily at 2 AM | Remove old workflow data |
| Database Maintenance | Weekly Sunday 3 AM | Optimize database |
| System Log Cleanup | Weekly Sunday 4 AM | Clean up log files |
| Database Backup | Daily at 3 AM | Create database backup |
| AI Session Cleanup | Daily at 1 AM | Clean up AI chat sessions |

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check if Redis is running
   redis-cli ping
   
   # Start Redis if not running
   sudo systemctl start redis-server
   ```

2. **No Workers Found**
   ```bash
   # Check worker status
   python manage.py celery_status
   
   # Start workers
   ./start_celery.sh start
   ```

3. **Task Failures**
   ```bash
   # Check logs
   tail -f logs/celery_suppliers.log
   
   # Monitor tasks
   python manage.py celery_monitor
   ```

4. **High Memory Usage**
   ```bash
   # Restart workers to clear memory
   ./start_celery.sh restart
   
   # Reduce worker concurrency
   celery -A config worker --queues=suppliers --concurrency=1
   ```

### Performance Tuning

1. **Adjust Concurrency**
   - CPU-bound tasks: concurrency = CPU cores
   - I/O-bound tasks: concurrency = 2-4 × CPU cores

2. **Queue Configuration**
   - Separate queues for different task types
   - Prioritize critical tasks

3. **Memory Management**
   - Set `worker_max_tasks_per_child` to prevent memory leaks
   - Monitor memory usage with Flower

4. **Rate Limiting**
   - Configure rate limits for API-heavy tasks
   - Use task routing for better resource allocation

## Production Deployment

### Systemd Services

Create systemd service files for production deployment:

1. Create worker service file:
   ```bash
   sudo nano /etc/systemd/system/celery-worker.service
   ```

2. Create beat service file:
   ```bash
   sudo nano /etc/systemd/system/celery-beat.service
   ```

3. Enable and start services:
   ```bash
   sudo systemctl enable celery-worker celery-beat
   sudo systemctl start celery-worker celery-beat
   ```

### Security Considerations

1. Use Redis AUTH in production
2. Configure firewall rules for Redis
3. Use TLS/SSL for Redis connections
4. Limit worker permissions
5. Monitor resource usage and set limits

### Scaling

1. **Horizontal Scaling**
   - Run workers on multiple servers
   - Use Redis Cluster for high availability

2. **Vertical Scaling**
   - Increase worker concurrency
   - Add more CPU cores and memory

3. **Queue Optimization**
   - Separate queues by priority
   - Use different workers for different task types