"""
Step executors for different types of workflow steps.
Each executor handles a specific type of workflow operation.
"""
import json
import logging
import requests
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type

from django.db import connection
from django.db.models import Q

from source_data.models import SourceData
from suppliers.models import Supplier, SupplierProduct
from marketplaces.models import Marketplace, MarketplaceListing


logger = logging.getLogger(__name__)


class BaseStepExecutor(ABC):
    """
    Base class for all step executors.
    Defines the interface that all executors must implement.
    """
    
    def __init__(self, step, context: Dict[str, Any]):
        """
        Initialize the executor.
        
        Args:
            step: The WorkflowStep instance
            context: Shared workflow context
        """
        self.step = step
        self.context = context
        self.config = step.config or {}
        self.metrics = {}
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the step with given input data.
        
        Args:
            input_data: Input data for the step
            
        Returns:
            Output data from the step
        """
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics."""
        return self.metrics
    
    def log_info(self, message: str):
        """Log info message with step context."""
        logger.info(f"[{self.step.name}] {message}")
    
    def log_error(self, message: str):
        """Log error message with step context."""
        logger.error(f"[{self.step.name}] {message}")


class DataFetchExecutor(BaseStepExecutor):
    """
    Executor for fetching data from various sources.
    Supports suppliers, marketplaces, and source data.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data based on configuration."""
        source_type = self.config.get('source_type')
        
        if source_type == 'supplier':
            return self._fetch_supplier_data(input_data)
        elif source_type == 'marketplace':
            return self._fetch_marketplace_data(input_data)
        elif source_type == 'source_data':
            return self._fetch_source_data(input_data)
        else:
            raise ValueError(f"Unknown source type: {source_type}")
    
    def _fetch_supplier_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from supplier."""
        supplier_id = self.config.get('supplier_id') or input_data.get('supplier_id')
        
        if not supplier_id:
            raise ValueError("Supplier ID is required")
        
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            connector = supplier.get_connector()
            
            # Determine what to fetch
            fetch_type = self.config.get('fetch_type', 'products')
            
            if fetch_type == 'products':
                # Fetch products
                self.log_info(f"Fetching products from supplier: {supplier.name}")
                products = connector.fetch_products()
                
                # Update or create supplier products
                created_count = 0
                updated_count = 0
                
                for product_data in products:
                    supplier_sku = product_data.get('sku')
                    if not supplier_sku:
                        continue
                    
                    product, created = SupplierProduct.objects.update_or_create(
                        supplier=supplier,
                        supplier_sku=supplier_sku,
                        defaults={'supplier_data': product_data}
                    )
                    
                    product.update_from_supplier_data(product_data)
                    product.save()
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                
                # Update metrics
                self.metrics = {
                    'total_products': len(products),
                    'created': created_count,
                    'updated': updated_count
                }
                
                # Update supplier
                supplier.update_sync_status(success=True)
                supplier.total_products = SupplierProduct.objects.filter(
                    supplier=supplier
                ).count()
                supplier.save()
                
                return {
                    'supplier_id': supplier.id,
                    'products_fetched': len(products),
                    'created': created_count,
                    'updated': updated_count
                }
            
            elif fetch_type == 'inventory':
                # Fetch inventory levels
                self.log_info(f"Fetching inventory from supplier: {supplier.name}")
                inventory_data = connector.fetch_inventory()
                
                # Update inventory levels
                updated_count = 0
                for item in inventory_data:
                    sku = item.get('sku')
                    quantity = item.get('quantity', 0)
                    
                    updated = SupplierProduct.objects.filter(
                        supplier=supplier,
                        supplier_sku=sku
                    ).update(quantity_available=quantity)
                    
                    updated_count += updated
                
                self.metrics = {
                    'inventory_items': len(inventory_data),
                    'updated': updated_count
                }
                
                return {
                    'supplier_id': supplier.id,
                    'inventory_updated': updated_count
                }
            
        except Supplier.DoesNotExist:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        except Exception as e:
            supplier.update_sync_status(success=False, error_message=str(e))
            raise
    
    def _fetch_marketplace_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from marketplace."""
        marketplace_id = self.config.get('marketplace_id') or input_data.get('marketplace_id')
        
        if not marketplace_id:
            raise ValueError("Marketplace ID is required")
        
        try:
            marketplace = Marketplace.objects.get(id=marketplace_id)
            connector = marketplace.get_connector()
            
            # Determine what to fetch
            fetch_type = self.config.get('fetch_type', 'listings')
            
            if fetch_type == 'listings':
                # Fetch listings
                self.log_info(f"Fetching listings from marketplace: {marketplace.name}")
                listings = connector.fetch_listings()
                
                # Update listings
                updated_count = 0
                for listing_data in listings:
                    listing_id = listing_data.get('listing_id')
                    if not listing_id:
                        continue
                    
                    try:
                        listing = MarketplaceListing.objects.get(
                            marketplace=marketplace,
                            marketplace_listing_id=listing_id
                        )
                        listing.update_from_marketplace(listing_data)
                        listing.save()
                        updated_count += 1
                    except MarketplaceListing.DoesNotExist:
                        self.log_error(f"Listing {listing_id} not found")
                
                self.metrics = {
                    'listings_fetched': len(listings),
                    'updated': updated_count
                }
                
                marketplace.update_sync_status(success=True)
                
                return {
                    'marketplace_id': marketplace.id,
                    'listings_updated': updated_count
                }
            
            elif fetch_type == 'orders':
                # Fetch new orders
                self.log_info(f"Fetching orders from marketplace: {marketplace.name}")
                orders = connector.fetch_orders()
                
                # Process orders (simplified)
                new_orders = 0
                for order_data in orders:
                    # This would create/update MarketplaceOrder instances
                    new_orders += 1
                
                self.metrics = {
                    'orders_fetched': len(orders),
                    'new_orders': new_orders
                }
                
                return {
                    'marketplace_id': marketplace.id,
                    'new_orders': new_orders
                }
            
        except Marketplace.DoesNotExist:
            raise ValueError(f"Marketplace with ID {marketplace_id} not found")
        except Exception as e:
            marketplace.update_sync_status(success=False, error_message=str(e))
            raise
    
    def _fetch_source_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from source_data table."""
        filters = self.config.get('filters', {})
        limit = self.config.get('limit', 100)
        
        # Build query
        query = SourceData.objects.all()
        
        if 'source_type' in filters:
            query = query.filter(source_type=filters['source_type'])
        
        if 'source_system' in filters:
            query = query.filter(source_system=filters['source_system'])
        
        if 'processing_status' in filters:
            query = query.filter(processing_status=filters['processing_status'])
        
        # Fetch data
        data = list(query[:limit].values())
        
        self.metrics = {
            'records_fetched': len(data)
        }
        
        return {
            'source_data': data,
            'count': len(data)
        }


class DataTransformExecutor(BaseStepExecutor):
    """
    Executor for transforming data.
    Supports mapping, filtering, and aggregation.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data based on configuration."""
        transform_type = self.config.get('transform_type', 'map')
        
        if transform_type == 'map':
            return self._map_transform(input_data)
        elif transform_type == 'filter':
            return self._filter_transform(input_data)
        elif transform_type == 'aggregate':
            return self._aggregate_transform(input_data)
        elif transform_type == 'normalize':
            return self._normalize_transform(input_data)
        else:
            raise ValueError(f"Unknown transform type: {transform_type}")
    
    def _map_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mapping transformation."""
        mapping_rules = self.config.get('mapping_rules', {})
        source_field = self.config.get('source_field', 'data')
        
        # Get source data
        source_data = input_data.get(source_field, [])
        if not isinstance(source_data, list):
            source_data = [source_data]
        
        # Apply mapping
        transformed_data = []
        for item in source_data:
            transformed_item = {}
            
            for target_field, source_path in mapping_rules.items():
                # Navigate source path
                value = item
                for key in source_path.split('.'):
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        value = None
                        break
                
                if value is not None:
                    transformed_item[target_field] = value
            
            transformed_data.append(transformed_item)
        
        self.metrics = {
            'records_transformed': len(transformed_data)
        }
        
        return {
            'transformed_data': transformed_data,
            'count': len(transformed_data)
        }
    
    def _filter_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filter transformation."""
        filter_rules = self.config.get('filter_rules', [])
        source_field = self.config.get('source_field', 'data')
        
        # Get source data
        source_data = input_data.get(source_field, [])
        if not isinstance(source_data, list):
            source_data = [source_data]
        
        # Apply filters
        filtered_data = []
        for item in source_data:
            include = True
            
            for rule in filter_rules:
                field = rule.get('field')
                operator = rule.get('operator')
                value = rule.get('value')
                
                item_value = item.get(field)
                
                if operator == 'equals' and item_value != value:
                    include = False
                elif operator == 'not_equals' and item_value == value:
                    include = False
                elif operator == 'greater_than' and not (item_value > value):
                    include = False
                elif operator == 'less_than' and not (item_value < value):
                    include = False
                elif operator == 'contains' and value not in str(item_value):
                    include = False
                elif operator == 'not_contains' and value in str(item_value):
                    include = False
                
                if not include:
                    break
            
            if include:
                filtered_data.append(item)
        
        self.metrics = {
            'records_filtered': len(source_data) - len(filtered_data),
            'records_passed': len(filtered_data)
        }
        
        return {
            'filtered_data': filtered_data,
            'count': len(filtered_data)
        }
    
    def _aggregate_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply aggregation transformation."""
        group_by = self.config.get('group_by', [])
        aggregations = self.config.get('aggregations', [])
        source_field = self.config.get('source_field', 'data')
        
        # Get source data
        source_data = input_data.get(source_field, [])
        if not isinstance(source_data, list):
            source_data = [source_data]
        
        # Group data
        groups = {}
        for item in source_data:
            # Create group key
            group_key = tuple(item.get(field) for field in group_by)
            
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        # Apply aggregations
        results = []
        for group_key, items in groups.items():
            result = {}
            
            # Add group fields
            for i, field in enumerate(group_by):
                result[field] = group_key[i]
            
            # Apply aggregations
            for agg in aggregations:
                field = agg.get('field')
                operation = agg.get('operation')
                output_field = agg.get('output_field', f"{field}_{operation}")
                
                values = [item.get(field, 0) for item in items]
                
                if operation == 'sum':
                    result[output_field] = sum(values)
                elif operation == 'avg':
                    result[output_field] = sum(values) / len(values) if values else 0
                elif operation == 'min':
                    result[output_field] = min(values) if values else None
                elif operation == 'max':
                    result[output_field] = max(values) if values else None
                elif operation == 'count':
                    result[output_field] = len(values)
            
            results.append(result)
        
        self.metrics = {
            'groups_created': len(results),
            'records_aggregated': len(source_data)
        }
        
        return {
            'aggregated_data': results,
            'count': len(results)
        }
    
    def _normalize_transform(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data for different marketplaces."""
        source_type = self.config.get('source_type')
        target_format = self.config.get('target_format', 'standard')
        
        # This would contain logic to normalize data from different sources
        # into a standard format that can be used across marketplaces
        
        normalized_data = input_data  # Placeholder
        
        return {
            'normalized_data': normalized_data
        }


class DataValidateExecutor(BaseStepExecutor):
    """
    Executor for validating data.
    Checks data quality, completeness, and business rules.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data based on rules."""
        validation_rules = self.config.get('validation_rules', [])
        source_field = self.config.get('source_field', 'data')
        
        # Get source data
        source_data = input_data.get(source_field, [])
        if not isinstance(source_data, list):
            source_data = [source_data]
        
        # Validate each record
        valid_records = []
        invalid_records = []
        validation_errors = []
        
        for idx, record in enumerate(source_data):
            errors = self._validate_record(record, validation_rules)
            
            if errors:
                invalid_records.append(record)
                validation_errors.append({
                    'record_index': idx,
                    'errors': errors
                })
            else:
                valid_records.append(record)
        
        self.metrics = {
            'total_records': len(source_data),
            'valid_records': len(valid_records),
            'invalid_records': len(invalid_records)
        }
        
        # Determine if validation passed
        fail_on_error = self.config.get('fail_on_error', True)
        validation_passed = len(invalid_records) == 0 or not fail_on_error
        
        return {
            'validation_passed': validation_passed,
            'valid_records': valid_records,
            'invalid_records': invalid_records,
            'validation_errors': validation_errors,
            'metrics': self.metrics
        }
    
    def _validate_record(self, record: Dict[str, Any], rules: List[Dict[str, Any]]) -> List[str]:
        """Validate a single record against rules."""
        errors = []
        
        for rule in rules:
            rule_type = rule.get('type')
            field = rule.get('field')
            
            if rule_type == 'required':
                if not record.get(field):
                    errors.append(f"Field '{field}' is required")
            
            elif rule_type == 'type':
                expected_type = rule.get('expected_type')
                value = record.get(field)
                
                if value is not None:
                    if expected_type == 'string' and not isinstance(value, str):
                        errors.append(f"Field '{field}' must be a string")
                    elif expected_type == 'number' and not isinstance(value, (int, float)):
                        errors.append(f"Field '{field}' must be a number")
                    elif expected_type == 'boolean' and not isinstance(value, bool):
                        errors.append(f"Field '{field}' must be a boolean")
                    elif expected_type == 'array' and not isinstance(value, list):
                        errors.append(f"Field '{field}' must be an array")
                    elif expected_type == 'object' and not isinstance(value, dict):
                        errors.append(f"Field '{field}' must be an object")
            
            elif rule_type == 'min_length':
                min_length = rule.get('min_length')
                value = str(record.get(field, ''))
                
                if len(value) < min_length:
                    errors.append(f"Field '{field}' must be at least {min_length} characters")
            
            elif rule_type == 'max_length':
                max_length = rule.get('max_length')
                value = str(record.get(field, ''))
                
                if len(value) > max_length:
                    errors.append(f"Field '{field}' must not exceed {max_length} characters")
            
            elif rule_type == 'min_value':
                min_value = rule.get('min_value')
                value = record.get(field)
                
                if value is not None and value < min_value:
                    errors.append(f"Field '{field}' must be at least {min_value}")
            
            elif rule_type == 'max_value':
                max_value = rule.get('max_value')
                value = record.get(field)
                
                if value is not None and value > max_value:
                    errors.append(f"Field '{field}' must not exceed {max_value}")
            
            elif rule_type == 'pattern':
                import re
                pattern = rule.get('pattern')
                value = str(record.get(field, ''))
                
                if not re.match(pattern, value):
                    errors.append(f"Field '{field}' does not match required pattern")
            
            elif rule_type == 'custom':
                # Custom validation function
                validation_func = rule.get('function')
                if validation_func:
                    try:
                        result = eval(validation_func, {'record': record, 'field': field})
                        if not result:
                            errors.append(rule.get('error_message', f"Custom validation failed for '{field}'"))
                    except:
                        errors.append(f"Custom validation error for '{field}'")
        
        return errors


class APICallExecutor(BaseStepExecutor):
    """
    Executor for making API calls.
    Supports REST API calls with various authentication methods.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call based on configuration."""
        # Get API configuration
        url = self.config.get('url')
        method = self.config.get('method', 'GET').upper()
        headers = self.config.get('headers', {})
        auth_type = self.config.get('auth_type')
        timeout = self.config.get('timeout', 30)
        
        # Build URL with parameters
        url_params = self.config.get('url_params', {})
        for key, value_path in url_params.items():
            value = self._get_value_from_path(input_data, value_path)
            url = url.replace(f"{{{key}}}", str(value))
        
        # Build request body
        body = None
        if method in ['POST', 'PUT', 'PATCH']:
            body_config = self.config.get('body', {})
            if isinstance(body_config, dict):
                body = {}
                for key, value_path in body_config.items():
                    body[key] = self._get_value_from_path(input_data, value_path)
            else:
                body = body_config
        
        # Add authentication
        if auth_type == 'bearer':
            token = self.config.get('auth_token')
            headers['Authorization'] = f"Bearer {token}"
        elif auth_type == 'api_key':
            api_key = self.config.get('api_key')
            api_key_header = self.config.get('api_key_header', 'X-API-Key')
            headers[api_key_header] = api_key
        
        # Make request
        self.log_info(f"Making {method} request to {url}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            # Parse response
            response_data = {}
            if response.content:
                try:
                    response_data = response.json()
                except:
                    response_data = {'text': response.text}
            
            self.metrics = {
                'status_code': response.status_code,
                'response_time_ms': response.elapsed.total_seconds() * 1000
            }
            
            return {
                'success': True,
                'status_code': response.status_code,
                'response': response_data
            }
            
        except requests.exceptions.RequestException as e:
            self.log_error(f"API call failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation path."""
        value = data
        for key in path.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class DatabaseQueryExecutor(BaseStepExecutor):
    """
    Executor for running database queries.
    Supports SELECT, INSERT, UPDATE operations.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database query."""
        query_type = self.config.get('query_type', 'select')
        
        if query_type == 'select':
            return self._execute_select(input_data)
        elif query_type == 'insert':
            return self._execute_insert(input_data)
        elif query_type == 'update':
            return self._execute_update(input_data)
        elif query_type == 'raw':
            return self._execute_raw(input_data)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
    
    def _execute_select(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SELECT query."""
        model_name = self.config.get('model')
        filters = self.config.get('filters', {})
        fields = self.config.get('fields', [])
        limit = self.config.get('limit', 100)
        
        # Build filters from input data
        query_filters = {}
        for field, value_path in filters.items():
            if isinstance(value_path, str) and value_path.startswith('$'):
                # Dynamic value from input
                path = value_path[1:]  # Remove $
                value = self._get_value_from_path(input_data, path)
                query_filters[field] = value
            else:
                # Static value
                query_filters[field] = value_path
        
        # Execute query
        if model_name == 'SourceData':
            query = SourceData.objects.filter(**query_filters)
        elif model_name == 'SupplierProduct':
            query = SupplierProduct.objects.filter(**query_filters)
        elif model_name == 'MarketplaceListing':
            query = MarketplaceListing.objects.filter(**query_filters)
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Apply field selection
        if fields:
            results = list(query[:limit].values(*fields))
        else:
            results = list(query[:limit].values())
        
        self.metrics = {
            'records_fetched': len(results)
        }
        
        return {
            'results': results,
            'count': len(results)
        }
    
    def _execute_insert(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute INSERT operation."""
        model_name = self.config.get('model')
        records = input_data.get('records', [])
        
        if not records:
            return {'inserted': 0}
        
        # Insert records
        inserted = 0
        if model_name == 'SourceData':
            for record in records:
                SourceData.objects.create(**record)
                inserted += 1
        
        self.metrics = {
            'records_inserted': inserted
        }
        
        return {
            'inserted': inserted
        }
    
    def _execute_update(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute UPDATE operation."""
        model_name = self.config.get('model')
        filters = self.config.get('filters', {})
        updates = self.config.get('updates', {})
        
        # Build query filters
        query_filters = {}
        for field, value in filters.items():
            if isinstance(value, str) and value.startswith('$'):
                path = value[1:]
                query_filters[field] = self._get_value_from_path(input_data, path)
            else:
                query_filters[field] = value
        
        # Build update values
        update_values = {}
        for field, value in updates.items():
            if isinstance(value, str) and value.startswith('$'):
                path = value[1:]
                update_values[field] = self._get_value_from_path(input_data, path)
            else:
                update_values[field] = value
        
        # Execute update
        updated = 0
        if model_name == 'SourceData':
            updated = SourceData.objects.filter(**query_filters).update(**update_values)
        
        self.metrics = {
            'records_updated': updated
        }
        
        return {
            'updated': updated
        }
    
    def _execute_raw(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute raw SQL query."""
        sql = self.config.get('sql')
        params = self.config.get('params', [])
        
        # Build parameters from input data
        query_params = []
        for param in params:
            if isinstance(param, str) and param.startswith('$'):
                path = param[1:]
                value = self._get_value_from_path(input_data, path)
                query_params.append(value)
            else:
                query_params.append(param)
        
        # Execute query
        with connection.cursor() as cursor:
            cursor.execute(sql, query_params)
            
            if sql.strip().upper().startswith('SELECT'):
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return {
                    'results': results,
                    'count': len(results)
                }
            else:
                return {
                    'affected_rows': cursor.rowcount
                }
    
    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation path."""
        value = data
        for key in path.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class AIProcessExecutor(BaseStepExecutor):
    """
    Executor for AI processing tasks.
    Integrates with the AI agents system.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AI processing task."""
        task_type = self.config.get('task_type')
        agent_id = self.config.get('agent_id')
        
        if task_type == 'enrich_product':
            return self._enrich_product(input_data)
        elif task_type == 'optimize_listing':
            return self._optimize_listing(input_data)
        elif task_type == 'categorize':
            return self._categorize(input_data)
        elif task_type == 'translate':
            return self._translate(input_data)
        else:
            raise ValueError(f"Unknown AI task type: {task_type}")
    
    def _enrich_product(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich product data using AI."""
        products = input_data.get('products', [])
        
        enriched_products = []
        for product in products:
            # This would call the AI agent to enrich product data
            # For now, we'll simulate it
            enriched = product.copy()
            enriched['ai_enriched'] = {
                'optimized_title': f"Premium {product.get('title', 'Product')}",
                'enhanced_description': f"{product.get('description', '')} - Enhanced by AI",
                'extracted_features': ['High Quality', 'Fast Shipping', 'Best Value'],
                'suggested_categories': ['Electronics', 'Gadgets'],
                'quality_score': 0.85
            }
            enriched_products.append(enriched)
        
        self.metrics = {
            'products_enriched': len(enriched_products)
        }
        
        return {
            'enriched_products': enriched_products
        }
    
    def _optimize_listing(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize marketplace listing using AI."""
        listing = input_data.get('listing', {})
        marketplace = input_data.get('marketplace', 'general')
        
        # This would call the AI agent to optimize the listing
        optimized = {
            'title': f"[BEST SELLER] {listing.get('title', '')}",
            'description': listing.get('description', ''),
            'keywords': ['premium', 'quality', 'fast shipping'],
            'pricing_suggestion': listing.get('price', 0) * 1.1
        }
        
        return {
            'optimized_listing': optimized
        }
    
    def _categorize(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize products using AI."""
        products = input_data.get('products', [])
        
        categorized = []
        for product in products:
            # AI categorization logic
            result = {
                'product_id': product.get('id'),
                'suggested_categories': ['Electronics', 'Consumer Goods'],
                'confidence': 0.92
            }
            categorized.append(result)
        
        return {
            'categorized_products': categorized
        }
    
    def _translate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate content using AI."""
        content = input_data.get('content', {})
        target_language = input_data.get('target_language', 'en')
        
        # AI translation logic
        translated = {
            'title': f"[{target_language}] {content.get('title', '')}",
            'description': f"[{target_language}] {content.get('description', '')}"
        }
        
        return {
            'translated_content': translated
        }


class NotificationExecutor(BaseStepExecutor):
    """
    Executor for sending notifications.
    Supports email, webhook, and system notifications.
    """
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send notification based on configuration."""
        notification_type = self.config.get('type', 'log')
        
        if notification_type == 'log':
            return self._send_log_notification(input_data)
        elif notification_type == 'email':
            return self._send_email_notification(input_data)
        elif notification_type == 'webhook':
            return self._send_webhook_notification(input_data)
        else:
            raise ValueError(f"Unknown notification type: {notification_type}")
    
    def _send_log_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send log notification."""
        message = self.config.get('message', 'Workflow step completed')
        level = self.config.get('level', 'info')
        
        # Format message with input data
        formatted_message = message.format(**input_data)
        
        if level == 'info':
            logger.info(formatted_message)
        elif level == 'warning':
            logger.warning(formatted_message)
        elif level == 'error':
            logger.error(formatted_message)
        
        return {
            'notification_sent': True,
            'message': formatted_message
        }
    
    def _send_email_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email notification."""
        # This would integrate with Django's email system
        # For now, we'll simulate it
        
        recipient = self.config.get('recipient')
        subject = self.config.get('subject', 'Workflow Notification')
        body = self.config.get('body', '')
        
        # Format with input data
        formatted_subject = subject.format(**input_data)
        formatted_body = body.format(**input_data)
        
        self.log_info(f"Email notification sent to {recipient}: {formatted_subject}")
        
        return {
            'notification_sent': True,
            'recipient': recipient,
            'subject': formatted_subject
        }
    
    def _send_webhook_notification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send webhook notification."""
        webhook_url = self.config.get('webhook_url')
        payload = self.config.get('payload', {})
        
        # Build payload with input data
        webhook_payload = {}
        for key, value in payload.items():
            if isinstance(value, str) and value.startswith('$'):
                path = value[1:]
                webhook_payload[key] = self._get_value_from_path(input_data, path)
            else:
                webhook_payload[key] = value
        
        try:
            response = requests.post(webhook_url, json=webhook_payload, timeout=30)
            response.raise_for_status()
            
            return {
                'notification_sent': True,
                'webhook_url': webhook_url,
                'status_code': response.status_code
            }
        except Exception as e:
            self.log_error(f"Webhook notification failed: {str(e)}")
            return {
                'notification_sent': False,
                'error': str(e)
            }
    
    def _get_value_from_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation path."""
        value = data
        for key in path.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


# Step executor registry
STEP_EXECUTORS = {
    'data_fetch': DataFetchExecutor,
    'data_transform': DataTransformExecutor,
    'data_validate': DataValidateExecutor,
    'api_call': APICallExecutor,
    'database_query': DatabaseQueryExecutor,
    'ai_process': AIProcessExecutor,
    'notification': NotificationExecutor,
}


def get_step_executor(step_type: str) -> Type[BaseStepExecutor]:
    """
    Get the appropriate executor class for a step type.
    
    Args:
        step_type: The type of step
        
    Returns:
        Executor class
    """
    executor_class = STEP_EXECUTORS.get(step_type)
    
    if not executor_class:
        # Default to base executor for custom types
        return BaseStepExecutor
    
    return executor_class