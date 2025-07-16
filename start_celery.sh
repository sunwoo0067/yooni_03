#!/bin/bash

# Celery Worker and Beat Startup Script
# This script starts Celery workers and beat scheduler for the Django project

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Celery Workers and Beat Scheduler${NC}"
echo "============================================="

# Function to check if Redis is running
check_redis() {
    echo -e "${YELLOW}Checking Redis connection...${NC}"
    python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print('✓ Redis is running')
except Exception as e:
    print(f'✗ Redis connection failed: {e}')
    exit(1)
"
}

# Function to start worker
start_worker() {
    local queue=$1
    local concurrency=${2:-2}
    local loglevel=${3:-info}
    
    echo -e "${GREEN}Starting worker for queue: ${queue}${NC}"
    
    celery -A config worker \
        --queues=${queue} \
        --concurrency=${concurrency} \
        --loglevel=${loglevel} \
        --hostname=${queue}@%h \
        --logfile=logs/celery_${queue}.log \
        --pidfile=logs/celery_${queue}.pid \
        --detach
}

# Function to start beat scheduler
start_beat() {
    echo -e "${GREEN}Starting Celery Beat scheduler${NC}"
    
    celery -A config beat \
        --loglevel=info \
        --scheduler=django_celery_beat.schedulers:DatabaseScheduler \
        --logfile=logs/celery_beat.log \
        --pidfile=logs/celery_beat.pid \
        --detach
}

# Function to start flower monitoring
start_flower() {
    echo -e "${GREEN}Starting Flower monitoring${NC}"
    
    celery -A config flower \
        --port=5555 \
        --logfile=logs/flower.log \
        --pidfile=logs/flower.pid \
        --detach
}

# Function to show status
show_status() {
    echo -e "${BLUE}Celery Status:${NC}"
    echo "=============="
    
    # Check workers
    celery -A config inspect active 2>/dev/null && echo -e "${GREEN}✓ Workers are running${NC}" || echo -e "${RED}✗ No workers found${NC}"
    
    # Check beat
    if [ -f "logs/celery_beat.pid" ] && kill -0 $(cat logs/celery_beat.pid) 2>/dev/null; then
        echo -e "${GREEN}✓ Beat scheduler is running${NC}"
    else
        echo -e "${RED}✗ Beat scheduler is not running${NC}"
    fi
    
    # Check flower
    if [ -f "logs/flower.pid" ] && kill -0 $(cat logs/flower.pid) 2>/dev/null; then
        echo -e "${GREEN}✓ Flower monitoring is running (http://localhost:5555)${NC}"
    else
        echo -e "${RED}✗ Flower monitoring is not running${NC}"
    fi
}

# Function to stop all services
stop_all() {
    echo -e "${YELLOW}Stopping all Celery services...${NC}"
    
    # Stop workers
    if command -v pkill >/dev/null 2>&1; then
        pkill -f "celery.*worker"
    fi
    
    # Stop beat
    if [ -f "logs/celery_beat.pid" ]; then
        kill $(cat logs/celery_beat.pid) 2>/dev/null
        rm -f logs/celery_beat.pid
    fi
    
    # Stop flower
    if [ -f "logs/flower.pid" ]; then
        kill $(cat logs/flower.pid) 2>/dev/null
        rm -f logs/flower.pid
    fi
    
    echo -e "${GREEN}All services stopped${NC}"
}

# Create logs directory
mkdir -p logs

# Parse command line arguments
case "${1:-start}" in
    start)
        check_redis
        
        echo -e "${YELLOW}Starting all Celery services...${NC}"
        
        # Start workers for different queues
        start_worker "suppliers" 2 "info"
        start_worker "marketplaces" 3 "info"
        start_worker "workflows" 2 "info"
        start_worker "ai_processing" 1 "info"
        start_worker "analytics" 1 "info"
        start_worker "maintenance" 1 "info"
        
        # Start beat scheduler
        start_beat
        
        # Start flower monitoring
        start_flower
        
        sleep 3
        show_status
        
        echo ""
        echo -e "${GREEN}Celery startup complete!${NC}"
        echo -e "${YELLOW}Useful commands:${NC}"
        echo "  ./start_celery.sh status    - Show status"
        echo "  ./start_celery.sh stop      - Stop all services"
        echo "  ./start_celery.sh restart   - Restart all services"
        echo "  ./start_celery.sh flower    - Start only Flower"
        echo ""
        echo -e "${BLUE}Flower Web UI: http://localhost:5555${NC}"
        ;;
        
    stop)
        stop_all
        ;;
        
    restart)
        stop_all
        sleep 2
        $0 start
        ;;
        
    status)
        show_status
        ;;
        
    flower)
        start_flower
        echo -e "${GREEN}Flower started at http://localhost:5555${NC}"
        ;;
        
    worker)
        if [ -z "$2" ]; then
            echo "Usage: $0 worker <queue_name> [concurrency] [loglevel]"
            echo "Available queues: suppliers, marketplaces, workflows, ai_processing, analytics, maintenance"
            exit 1
        fi
        check_redis
        start_worker "$2" "${3:-2}" "${4:-info}"
        ;;
        
    beat)
        check_redis
        start_beat
        ;;
        
    *)
        echo "Usage: $0 {start|stop|restart|status|flower|worker|beat}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all Celery services"
        echo "  stop     - Stop all Celery services"
        echo "  restart  - Restart all Celery services"
        echo "  status   - Show status of all services"
        echo "  flower   - Start only Flower monitoring"
        echo "  worker   - Start a specific worker queue"
        echo "  beat     - Start only Beat scheduler"
        exit 1
        ;;
esac