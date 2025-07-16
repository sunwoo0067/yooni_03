# Workflow Engine Documentation

The Orchestration app provides a comprehensive workflow engine for automating business processes in the e-commerce system. It handles product imports, listing creation, inventory synchronization, and order processing through configurable, reusable workflows.

## Overview

### Key Components

1. **Workflow Models** - Define workflow templates and track executions
2. **Workflow Engine** - Core execution engine with retry logic and error handling  
3. **Step Executors** - Pluggable components for different step types
4. **Predefined Workflows** - Templates for common business processes
5. **Scheduler** - Automated workflow execution based on schedules
6. **Admin Interface** - Management and monitoring UI
7. **REST API** - Programmatic workflow control

## Models

### Workflow
Defines reusable workflow templates with steps, configuration, and execution settings.

**Key Fields:**
- `name`, `code` - Workflow identification
- `workflow_type` - Type of workflow (product_import, listing_creation, etc.)
- `status` - Active/inactive state
- `config` - Workflow-specific configuration
- `max_retries`, `retry_delay_seconds` - Error handling settings
- Statistics fields for tracking success rates and performance

### WorkflowStep
Individual steps within a workflow with configuration and dependencies.

**Key Fields:**
- `step_type` - Type of operation (data_fetch, api_call, etc.)
- `order` - Execution sequence
- `config` - Step-specific configuration
- `depends_on_steps` - Step dependencies
- `is_optional` - Whether step failure stops workflow
- `can_run_parallel` - Parallel execution capability

### WorkflowExecution
Tracks individual workflow runs with progress and results.

**Key Fields:**
- `execution_id` - Unique execution identifier
- `status` - Current execution state
- `input_data`, `output_data` - Workflow inputs and outputs
- `total_steps`, `completed_steps` - Progress tracking
- Timing and error information

### WorkflowStepExecution
Tracks execution of individual steps within a workflow run.

### WorkflowSchedule
Manages scheduled workflow execution with cron-like scheduling.

## Step Types and Executors

### DataFetchExecutor (`data_fetch`)
Fetches data from various sources:
- **Supplier data** - Products and inventory from supplier APIs
- **Marketplace data** - Listings and orders from marketplace APIs  
- **Source data** - Queries from the source_data table

```json
{
  "source_type": "supplier",
  "fetch_type": "products",
  "supplier_id": 123
}
```

### DataTransformExecutor (`data_transform`)
Transforms and manipulates data:
- **Mapping** - Field mapping and transformation
- **Filtering** - Data filtering based on rules
- **Aggregation** - Grouping and calculations
- **Normalization** - Standardizing data formats

```json
{
  "transform_type": "map",
  "mapping_rules": {
    "title": "name",
    "price": "cost_price"
  }
}
```

### DataValidateExecutor (`data_validate`)
Validates data quality and completeness:
- Required field validation
- Data type checking
- Value range validation
- Custom validation rules

```json
{
  "validation_rules": [
    {"type": "required", "field": "sku"},
    {"type": "min_value", "field": "price", "min_value": 0.01}
  ]
}
```

### APICallExecutor (`api_call`)
Makes external API calls:
- REST API integration
- Authentication support (Bearer, API key)
- Request/response handling
- Error handling and retries

```json
{
  "url": "https://api.marketplace.com/listings",
  "method": "POST",
  "auth_type": "bearer",
  "body": {"title": "$title", "price": "$price"}
}
```

### DatabaseQueryExecutor (`database_query`)
Database operations:
- SELECT queries with filtering
- INSERT operations for creating records
- UPDATE operations for modifying data
- Raw SQL support

```json
{
  "query_type": "insert", 
  "model": "SourceData",
  "record_mapping": {
    "source_type": "supplier_product",
    "raw_data": "$"
  }
}
```

### AIProcessExecutor (`ai_process`)
AI-powered processing:
- Product enrichment
- Listing optimization
- Content translation
- Categorization

```json
{
  "task_type": "enrich_product",
  "source_field": "products"
}
```

### NotificationExecutor (`notification`)
Send notifications:
- Log messages
- Email notifications
- Webhook calls

```json
{
  "type": "email",
  "recipient": "admin@company.com",
  "subject": "Workflow completed"
}
```

## Predefined Workflows

### ProductImportWorkflow
Imports products from suppliers with validation and enrichment.

**Steps:**
1. Fetch products from supplier API
2. Validate product data
3. Transform to standard format
4. AI enrichment (optional)
5. Create source data records
6. Update supplier statistics
7. Send completion notification

### ListingCreationWorkflow  
Creates marketplace listings from product data.

**Steps:**
1. Fetch products ready for listing
2. Validate marketplace requirements
3. Optimize listings with AI
4. Calculate pricing with markup
5. Translate content (optional)
6. Create marketplace listings via API
7. Store listing records
8. Update product status

### InventorySyncWorkflow
Synchronizes inventory across suppliers and marketplaces.

**Steps:**
1. Fetch current inventory from suppliers
2. Validate inventory data
3. Update internal inventory records
4. Calculate available quantities
5. Filter items needing updates
6. Update marketplace inventory via APIs
7. Update inventory tracking records
8. Check for low stock items
9. Send low stock alerts
10. Log sync summary

### OrderProcessingWorkflow
Processes marketplace orders from receipt to fulfillment.

**Steps:**
1. Fetch new orders from marketplaces
2. Validate order data
3. Check inventory availability
4. Validate inventory allocation
5. Fraud detection (optional)
6. Reserve inventory
7. Create internal order records
8. Acknowledge orders with marketplace
9. Check auto-ship eligibility
10. Generate shipping labels
11. Update order status
12. Notify marketplace of shipment
13. Send processing notifications

## Usage Examples

### Creating Workflows from Templates

```python
from orchestration.workflows import create_workflow_from_template

# Create a product import workflow
workflow = create_workflow_from_template(
    template_name='product_import',
    name='Daily Product Import', 
    description='Import products from all active suppliers',
    created_by=user
)
```

### Executing Workflows

```python
from orchestration.engine import WorkflowEngine

engine = WorkflowEngine()

# Execute workflow
execution = engine.execute_workflow(
    workflow=workflow,
    input_data={'supplier_id': 123},
    triggered_by=user,
    trigger_type='manual'
)

print(f"Execution ID: {execution.execution_id}")
print(f"Status: {execution.status}")
```

### Using Management Commands

```bash
# Create workflow templates
python manage.py create_workflow_templates

# Create specific template
python manage.py create_workflow_templates --template product_import

# Run workflow
python manage.py run_workflow product_import_template --input-data '{"supplier_id": 123}'

# Start scheduler daemon
python manage.py workflow_scheduler --max-workers 10
```

### REST API Usage

```bash
# Get workflow templates
GET /orchestration/api/templates/

# Create workflow from template  
POST /orchestration/api/templates/product_import/create/
{
  "name": "My Product Import",
  "description": "Custom import workflow"
}

# Execute workflow
POST /orchestration/api/workflows/1/execute/
{
  "input_data": {"supplier_id": 123}
}

# Get execution status
GET /orchestration/api/executions/1/

# Get workflow statistics
GET /orchestration/api/stats/
```

## Configuration Examples

### Step Configuration

Each step type has specific configuration options:

```json
{
  "name": "Fetch Supplier Products",
  "step_type": "data_fetch", 
  "config": {
    "source_type": "supplier",
    "fetch_type": "products",
    "supplier_id": "$input.supplier_id"
  },
  "timeout_seconds": 300,
  "can_retry": true,
  "max_retries": 3
}
```

### Conditional Execution

```json
{
  "condition": {
    "type": "value_check",
    "path": "workflow.config.enable_ai_enrichment", 
    "value": true,
    "operator": "equals"
  }
}
```

### Parallel Execution

```json
{
  "can_run_parallel": true,
  "parallel_group": "marketplace_updates"
}
```

## Monitoring and Administration

### Django Admin
- Workflow management and configuration
- Execution monitoring with progress bars
- Step-by-step execution details
- Schedule management
- Performance statistics

### REST API Endpoints
- `/api/workflows/` - Workflow CRUD operations
- `/api/executions/` - Execution monitoring  
- `/api/schedules/` - Schedule management
- `/api/stats/` - Performance statistics
- `/api/health/` - Health check

### Logging
Comprehensive logging at multiple levels:
- Workflow execution events
- Step execution details
- Error messages with stack traces
- Performance metrics

## Error Handling

### Retry Logic
- Configurable retry attempts per step
- Exponential backoff delays
- Optional vs required step failures
- Workflow-level error handling

### Error Recovery
- Failed step restart capability
- Partial execution recovery
- Manual intervention points
- Error notifications

## Performance Considerations

### Parallel Execution
- Steps can run in parallel groups
- Thread pool executor for concurrency
- Resource isolation between steps

### Scalability
- Stateless step executors
- Database-backed state management
- Horizontal scaling support
- Async execution capabilities

### Monitoring
- Execution time tracking
- Success rate monitoring
- Resource usage metrics
- Performance bottleneck identification

## Integration Points

### Source Data System
- Creates and updates SourceData records
- Event-driven data lineage tracking
- Centralized data management

### Supplier Integration
- Leverages supplier connectors
- Product and inventory synchronization
- API rate limiting and authentication

### Marketplace Integration  
- Uses marketplace connectors
- Listing and order management
- Multi-marketplace support

### AI Agents System
- Product enrichment workflows
- Content optimization
- Automated categorization
- Translation services

This workflow engine provides a flexible, scalable foundation for automating complex e-commerce operations while maintaining full visibility and control over business processes.