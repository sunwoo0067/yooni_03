"""
Pre-defined workflow templates for common business processes.
"""
from typing import Dict, Any, List
from django.contrib.auth.models import User

from .models import Workflow, WorkflowStep


class WorkflowTemplate:
    """
    Base class for workflow templates.
    Provides methods to create workflow instances with predefined steps.
    """
    
    @classmethod
    def create_workflow(cls, name: str, description: str = '', created_by: User = None) -> Workflow:
        """
        Create a workflow instance with predefined steps.
        
        Args:
            name: Workflow name
            description: Workflow description
            created_by: User who created the workflow
            
        Returns:
            Created workflow instance
        """
        # Create workflow
        workflow = Workflow.objects.create(
            name=name,
            code=cls.get_code(name),
            description=description or cls.get_description(),
            workflow_type=cls.get_workflow_type(),
            config=cls.get_default_config(),
            created_by=created_by,
            status='active'
        )
        
        # Create steps
        steps_config = cls.get_steps_config()
        for step_config in steps_config:
            WorkflowStep.objects.create(
                workflow=workflow,
                **step_config
            )
        
        return workflow
    
    @classmethod
    def get_code(cls, name: str) -> str:
        """Generate workflow code from name."""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    @classmethod
    def get_workflow_type(cls) -> str:
        """Get workflow type."""
        raise NotImplementedError
    
    @classmethod
    def get_description(cls) -> str:
        """Get default description."""
        raise NotImplementedError
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Get default workflow configuration."""
        return {}
    
    @classmethod
    def get_steps_config(cls) -> List[Dict[str, Any]]:
        """Get steps configuration."""
        raise NotImplementedError


class ProductImportWorkflow(WorkflowTemplate):
    """
    Workflow template for importing products from suppliers.
    Handles fetching, validation, transformation, and storage.
    """
    
    @classmethod
    def get_workflow_type(cls) -> str:
        return 'product_import'
    
    @classmethod
    def get_description(cls) -> str:
        return 'Import products from suppliers with validation and enrichment'
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            'batch_size': 100,
            'enable_validation': True,
            'enable_ai_enrichment': True,
            'auto_create_source_data': True
        }
    
    @classmethod
    def get_steps_config(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'Fetch Supplier Products',
                'step_type': 'data_fetch',
                'description': 'Fetch products from supplier API',
                'order': 1,
                'config': {
                    'source_type': 'supplier',
                    'fetch_type': 'products'
                },
                'timeout_seconds': 300
            },
            {
                'name': 'Validate Product Data',
                'step_type': 'data_validate',
                'description': 'Validate product data quality',
                'order': 2,
                'config': {
                    'source_field': 'products',
                    'validation_rules': [
                        {'type': 'required', 'field': 'sku'},
                        {'type': 'required', 'field': 'name'},
                        {'type': 'required', 'field': 'price'},
                        {'type': 'min_value', 'field': 'price', 'min_value': 0.01},
                        {'type': 'type', 'field': 'price', 'expected_type': 'number'},
                        {'type': 'min_length', 'field': 'name', 'min_length': 3},
                        {'type': 'max_length', 'field': 'name', 'max_length': 500}
                    ],
                    'fail_on_error': False
                }
            },
            {
                'name': 'Transform Product Data',
                'step_type': 'data_transform',
                'description': 'Transform products to standard format',
                'order': 3,
                'config': {
                    'transform_type': 'normalize',
                    'source_field': 'valid_records',
                    'target_format': 'standard_product',
                    'mapping_rules': {
                        'internal_sku': 'sku',
                        'title': 'name',
                        'description': 'description',
                        'cost_price': 'price',
                        'weight': 'weight',
                        'brand': 'brand',
                        'category': 'category',
                        'image_urls': 'images'
                    }
                }
            },
            {
                'name': 'AI Product Enrichment',
                'step_type': 'ai_process',
                'description': 'Enrich products with AI-generated content',
                'order': 4,
                'config': {
                    'task_type': 'enrich_product',
                    'source_field': 'transformed_data'
                },
                'is_optional': True,
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.enable_ai_enrichment',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Create Source Data Records',
                'step_type': 'database_query',
                'description': 'Store products in source_data table',
                'order': 5,
                'config': {
                    'query_type': 'insert',
                    'model': 'SourceData',
                    'source_field': 'enriched_products',
                    'record_mapping': {
                        'source_type': 'supplier_product',
                        'source_system': '$supplier.code',
                        'source_id': '$sku',
                        'raw_data': '$',
                        'normalized_data': '$transformed_data',
                        'ai_data': '$ai_enriched',
                        'processing_status': 'processed'
                    }
                }
            },
            {
                'name': 'Update Supplier Statistics',
                'step_type': 'database_query',
                'description': 'Update supplier product count and sync status',
                'order': 6,
                'config': {
                    'query_type': 'update',
                    'model': 'Supplier',
                    'filters': {
                        'id': '$supplier_id'
                    },
                    'updates': {
                        'total_products': '$products_count',
                        'last_sync_at': 'now()',
                        'last_sync_status': 'success'
                    }
                }
            },
            {
                'name': 'Send Import Notification',
                'step_type': 'notification',
                'description': 'Send notification about import completion',
                'order': 7,
                'config': {
                    'type': 'log',
                    'level': 'info',
                    'message': 'Product import completed: {products_imported} products imported from supplier {supplier_name}'
                },
                'is_optional': True
            }
        ]


class ListingCreationWorkflow(WorkflowTemplate):
    """
    Workflow template for creating marketplace listings.
    Handles product selection, optimization, and marketplace publishing.
    """
    
    @classmethod
    def get_workflow_type(cls) -> str:
        return 'listing_creation'
    
    @classmethod
    def get_description(cls) -> str:
        return 'Create and optimize marketplace listings from product data'
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            'auto_optimize': True,
            'enable_translation': False,
            'price_markup_percentage': 20,
            'default_quantity': 10
        }
    
    @classmethod
    def get_steps_config(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'Fetch Product Data',
                'step_type': 'database_query',
                'description': 'Fetch products ready for listing',
                'order': 1,
                'config': {
                    'query_type': 'select',
                    'model': 'SourceData',
                    'filters': {
                        'source_type': 'supplier_product',
                        'processing_status': 'processed'
                    },
                    'fields': ['id', 'normalized_data', 'ai_data'],
                    'limit': 50
                }
            },
            {
                'name': 'Validate Listing Requirements',
                'step_type': 'data_validate',
                'description': 'Validate products meet marketplace requirements',
                'order': 2,
                'config': {
                    'source_field': 'results',
                    'validation_rules': [
                        {'type': 'required', 'field': 'title'},
                        {'type': 'required', 'field': 'description'},
                        {'type': 'required', 'field': 'price'},
                        {'type': 'required', 'field': 'image_urls'},
                        {'type': 'min_length', 'field': 'title', 'min_length': 10},
                        {'type': 'max_length', 'field': 'title', 'max_length': 80},
                        {'type': 'min_length', 'field': 'description', 'min_length': 50}
                    ]
                }
            },
            {
                'name': 'Optimize Listings for Marketplace',
                'step_type': 'ai_process',
                'description': 'Optimize titles and descriptions for marketplace',
                'order': 3,
                'config': {
                    'task_type': 'optimize_listing',
                    'source_field': 'valid_records'
                },
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.auto_optimize',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Calculate Pricing',
                'step_type': 'data_transform',
                'description': 'Calculate marketplace pricing with markup',
                'order': 4,
                'config': {
                    'transform_type': 'map',
                    'source_field': 'optimized_listings',
                    'mapping_rules': {
                        'marketplace_price': 'cost_price * (1 + markup_percentage/100)',
                        'sale_price': 'marketplace_price * 0.9',
                        'listing_quantity': 'default_quantity'
                    }
                }
            },
            {
                'name': 'Translate Content',
                'step_type': 'ai_process',
                'description': 'Translate content for international marketplaces',
                'order': 5,
                'config': {
                    'task_type': 'translate',
                    'source_field': 'priced_listings',
                    'target_language': 'es'
                },
                'is_optional': True,
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.enable_translation',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Create Marketplace Listings',
                'step_type': 'api_call',
                'description': 'Create listings on marketplace via API',
                'order': 6,
                'config': {
                    'url': '{marketplace_api_url}/listings',
                    'method': 'POST',
                    'auth_type': 'bearer',
                    'auth_token': '$marketplace.auth_token',
                    'body': {
                        'title': '$optimized_title',
                        'description': '$optimized_description',
                        'price': '$marketplace_price',
                        'quantity': '$listing_quantity',
                        'images': '$image_urls',
                        'category_id': '$category_id'
                    }
                }
            },
            {
                'name': 'Store Listing Records',
                'step_type': 'database_query',
                'description': 'Store marketplace listing records',
                'order': 7,
                'config': {
                    'query_type': 'insert',
                    'model': 'MarketplaceListing',
                    'source_field': 'api_responses',
                    'record_mapping': {
                        'marketplace_id': '$marketplace.id',
                        'marketplace_listing_id': '$response.listing_id',
                        'marketplace_sku': '$sku',
                        'title': '$title',
                        'description': '$description',
                        'price': '$price',
                        'quantity_listed': '$quantity',
                        'status': 'active'
                    }
                }
            },
            {
                'name': 'Update Product Status',
                'step_type': 'database_query',
                'description': 'Mark products as listed',
                'order': 8,
                'config': {
                    'query_type': 'update',
                    'model': 'SourceData',
                    'filters': {
                        'id__in': '$processed_product_ids'
                    },
                    'updates': {
                        'processing_status': 'listed',
                        'market_data': '$listing_data'
                    }
                }
            },
            {
                'name': 'Send Success Notification',
                'step_type': 'notification',
                'description': 'Notify about successful listing creation',
                'order': 9,
                'config': {
                    'type': 'log',
                    'level': 'info',
                    'message': 'Listing creation completed: {listings_created} listings created on {marketplace_name}'
                }
            }
        ]


class InventorySyncWorkflow(WorkflowTemplate):
    """
    Workflow template for synchronizing inventory across systems.
    Handles inventory updates, allocation, and marketplace sync.
    """
    
    @classmethod
    def get_workflow_type(cls) -> str:
        return 'inventory_sync'
    
    @classmethod
    def get_description(cls) -> str:
        return 'Synchronize inventory levels across suppliers and marketplaces'
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            'sync_all_marketplaces': True,
            'inventory_buffer': 5,
            'enable_low_stock_alerts': True,
            'low_stock_threshold': 10
        }
    
    @classmethod
    def get_steps_config(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'Fetch Current Inventory',
                'step_type': 'data_fetch',
                'description': 'Fetch current inventory from suppliers',
                'order': 1,
                'config': {
                    'source_type': 'supplier',
                    'fetch_type': 'inventory'
                }
            },
            {
                'name': 'Validate Inventory Data',
                'step_type': 'data_validate',
                'description': 'Validate inventory data integrity',
                'order': 2,
                'config': {
                    'source_field': 'inventory_data',
                    'validation_rules': [
                        {'type': 'required', 'field': 'sku'},
                        {'type': 'required', 'field': 'quantity'},
                        {'type': 'type', 'field': 'quantity', 'expected_type': 'number'},
                        {'type': 'min_value', 'field': 'quantity', 'min_value': 0}
                    ]
                }
            },
            {
                'name': 'Update Internal Inventory',
                'step_type': 'database_query',
                'description': 'Update internal inventory records',
                'order': 3,
                'config': {
                    'query_type': 'update',
                    'model': 'SupplierProduct',
                    'filters': {
                        'supplier_sku': '$sku'
                    },
                    'updates': {
                        'quantity_available': '$quantity',
                        'last_updated_from_supplier': 'now()'
                    }
                }
            },
            {
                'name': 'Calculate Available Quantity',
                'step_type': 'data_transform',
                'description': 'Calculate available quantity after buffers and reservations',
                'order': 4,
                'config': {
                    'transform_type': 'map',
                    'source_field': 'updated_inventory',
                    'mapping_rules': {
                        'available_for_listing': 'max(0, quantity_available - reserved_quantity - inventory_buffer)',
                        'needs_update': 'marketplace_quantity != available_for_listing'
                    }
                }
            },
            {
                'name': 'Filter Items Needing Update',
                'step_type': 'data_transform',
                'description': 'Filter items that need marketplace updates',
                'order': 5,
                'config': {
                    'transform_type': 'filter',
                    'source_field': 'calculated_inventory',
                    'filter_rules': [
                        {'field': 'needs_update', 'operator': 'equals', 'value': True}
                    ]
                }
            },
            {
                'name': 'Update Marketplace Inventory',
                'step_type': 'api_call',
                'description': 'Update inventory on marketplaces',
                'order': 6,
                'config': {
                    'url': '{marketplace_api_url}/inventory/{sku}',
                    'method': 'PUT',
                    'auth_type': 'api_key',
                    'auth_token': '$marketplace.api_key',
                    'body': {
                        'quantity': '$available_for_listing'
                    }
                },
                'can_run_parallel': True,
                'parallel_group': 'marketplace_updates'
            },
            {
                'name': 'Update Inventory Records',
                'step_type': 'database_query',
                'description': 'Update marketplace inventory records',
                'order': 7,
                'config': {
                    'query_type': 'update',
                    'model': 'MarketplaceInventory',
                    'filters': {
                        'marketplace_sku': '$sku'
                    },
                    'updates': {
                        'marketplace_quantity': '$available_for_listing',
                        'last_sync_at': 'now()',
                        'sync_status': 'synced'
                    }
                }
            },
            {
                'name': 'Check Low Stock Items',
                'step_type': 'data_transform',
                'description': 'Identify low stock items',
                'order': 8,
                'config': {
                    'transform_type': 'filter',
                    'source_field': 'updated_inventory',
                    'filter_rules': [
                        {'field': 'quantity_available', 'operator': 'less_than', 'value': '$workflow.config.low_stock_threshold'}
                    ]
                },
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.enable_low_stock_alerts',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Send Low Stock Alerts',
                'step_type': 'notification',
                'description': 'Send alerts for low stock items',
                'order': 9,
                'config': {
                    'type': 'email',
                    'recipient': 'inventory@company.com',
                    'subject': 'Low Stock Alert',
                    'body': 'The following items are running low on stock: {low_stock_items}'
                },
                'is_optional': True,
                'condition': {
                    'type': 'expression',
                    'expression': 'len(context.get("low_stock_items", [])) > 0'
                }
            },
            {
                'name': 'Log Sync Summary',
                'step_type': 'notification',
                'description': 'Log inventory sync summary',
                'order': 10,
                'config': {
                    'type': 'log',
                    'level': 'info',
                    'message': 'Inventory sync completed: {items_updated} items updated across {marketplaces_count} marketplaces'
                }
            }
        ]


class OrderProcessingWorkflow(WorkflowTemplate):
    """
    Workflow template for processing marketplace orders.
    Handles order validation, inventory allocation, and fulfillment.
    """
    
    @classmethod
    def get_workflow_type(cls) -> str:
        return 'order_processing'
    
    @classmethod
    def get_description(cls) -> str:
        return 'Process marketplace orders from receipt to fulfillment'
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        return {
            'auto_acknowledge': True,
            'enable_fraud_check': True,
            'auto_ship_threshold': 100,  # Auto-ship orders under this amount
            'require_manual_review': False
        }
    
    @classmethod
    def get_steps_config(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'Fetch New Orders',
                'step_type': 'data_fetch',
                'description': 'Fetch new orders from marketplaces',
                'order': 1,
                'config': {
                    'source_type': 'marketplace',
                    'fetch_type': 'orders'
                }
            },
            {
                'name': 'Validate Orders',
                'step_type': 'data_validate',
                'description': 'Validate order data completeness',
                'order': 2,
                'config': {
                    'source_field': 'orders',
                    'validation_rules': [
                        {'type': 'required', 'field': 'order_id'},
                        {'type': 'required', 'field': 'customer_name'},
                        {'type': 'required', 'field': 'shipping_address'},
                        {'type': 'required', 'field': 'order_items'},
                        {'type': 'required', 'field': 'total_amount'},
                        {'type': 'min_value', 'field': 'total_amount', 'min_value': 0.01}
                    ]
                }
            },
            {
                'name': 'Check Inventory Availability',
                'step_type': 'database_query',
                'description': 'Verify inventory availability for order items',
                'order': 3,
                'config': {
                    'query_type': 'select',
                    'model': 'SupplierProduct',
                    'filters': {
                        'supplier_sku__in': '$order_skus'
                    },
                    'fields': ['supplier_sku', 'quantity_available']
                }
            },
            {
                'name': 'Validate Inventory Allocation',
                'step_type': 'data_validate',
                'description': 'Ensure sufficient inventory for all items',
                'order': 4,
                'config': {
                    'source_field': 'inventory_check',
                    'validation_rules': [
                        {'type': 'custom', 'function': 'record["quantity_available"] >= record["order_quantity"]', 'error_message': 'Insufficient inventory'}
                    ]
                }
            },
            {
                'name': 'Fraud Detection Check',
                'step_type': 'ai_process',
                'description': 'Run fraud detection on orders',
                'order': 5,
                'config': {
                    'task_type': 'fraud_check',
                    'source_field': 'valid_orders'
                },
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.enable_fraud_check',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Reserve Inventory',
                'step_type': 'database_query',
                'description': 'Reserve inventory for valid orders',
                'order': 6,
                'config': {
                    'query_type': 'update',
                    'model': 'SupplierProduct',
                    'filters': {
                        'supplier_sku': '$sku'
                    },
                    'updates': {
                        'quantity_available': 'quantity_available - $order_quantity'
                    }
                }
            },
            {
                'name': 'Create Internal Order Records',
                'step_type': 'database_query',
                'description': 'Create internal order tracking records',
                'order': 7,
                'config': {
                    'query_type': 'insert',
                    'model': 'MarketplaceOrder',
                    'source_field': 'processed_orders',
                    'record_mapping': {
                        'marketplace_id': '$marketplace.id',
                        'marketplace_order_id': '$order_id',
                        'customer_name': '$customer_name',
                        'shipping_address': '$shipping_address',
                        'order_items': '$order_items',
                        'total_amount': '$total_amount',
                        'status': 'pending'
                    }
                }
            },
            {
                'name': 'Acknowledge Orders',
                'step_type': 'api_call',
                'description': 'Acknowledge orders with marketplace',
                'order': 8,
                'config': {
                    'url': '{marketplace_api_url}/orders/{order_id}/acknowledge',
                    'method': 'POST',
                    'auth_type': 'bearer',
                    'auth_token': '$marketplace.auth_token'
                },
                'condition': {
                    'type': 'value_check',
                    'path': 'workflow.config.auto_acknowledge',
                    'value': True,
                    'operator': 'equals'
                }
            },
            {
                'name': 'Check Auto-Ship Eligibility',
                'step_type': 'data_transform',
                'description': 'Determine which orders can be auto-shipped',
                'order': 9,
                'config': {
                    'transform_type': 'filter',
                    'source_field': 'acknowledged_orders',
                    'filter_rules': [
                        {'field': 'total_amount', 'operator': 'less_than', 'value': '$workflow.config.auto_ship_threshold'},
                        {'field': 'fraud_score', 'operator': 'less_than', 'value': 0.3}
                    ]
                }
            },
            {
                'name': 'Generate Shipping Labels',
                'step_type': 'api_call',
                'description': 'Generate shipping labels for auto-ship orders',
                'order': 10,
                'config': {
                    'url': '{shipping_api_url}/labels',
                    'method': 'POST',
                    'auth_type': 'api_key',
                    'api_key': '$shipping.api_key',
                    'body': {
                        'recipient': '$shipping_address',
                        'items': '$order_items',
                        'service_type': 'standard'
                    }
                }
            },
            {
                'name': 'Update Order Status',
                'step_type': 'database_query',
                'description': 'Update order status to shipped',
                'order': 11,
                'config': {
                    'query_type': 'update',
                    'model': 'MarketplaceOrder',
                    'filters': {
                        'marketplace_order_id': '$order_id'
                    },
                    'updates': {
                        'status': 'shipped',
                        'tracking_number': '$tracking_number',
                        'shipped_at': 'now()'
                    }
                }
            },
            {
                'name': 'Notify Marketplace of Shipment',
                'step_type': 'api_call',
                'description': 'Update marketplace with tracking information',
                'order': 12,
                'config': {
                    'url': '{marketplace_api_url}/orders/{order_id}/ship',
                    'method': 'POST',
                    'auth_type': 'bearer',
                    'auth_token': '$marketplace.auth_token',
                    'body': {
                        'tracking_number': '$tracking_number',
                        'carrier': '$carrier',
                        'ship_date': '$ship_date'
                    }
                }
            },
            {
                'name': 'Send Order Notifications',
                'step_type': 'notification',
                'description': 'Send order processing notifications',
                'order': 13,
                'config': {
                    'type': 'log',
                    'level': 'info',
                    'message': 'Order processing completed: {orders_processed} orders processed, {orders_shipped} orders shipped'
                }
            }
        ]


# Workflow factory for easy creation
WORKFLOW_TEMPLATES = {
    'product_import': ProductImportWorkflow,
    'listing_creation': ListingCreationWorkflow,
    'inventory_sync': InventorySyncWorkflow,
    'order_processing': OrderProcessingWorkflow,
}


def create_workflow_from_template(template_name: str, name: str, 
                                description: str = '', created_by: User = None) -> Workflow:
    """
    Create a workflow from a predefined template.
    
    Args:
        template_name: Name of the template to use
        name: Name for the new workflow
        description: Description for the workflow
        created_by: User who created the workflow
        
    Returns:
        Created workflow instance
    """
    template_class = WORKFLOW_TEMPLATES.get(template_name)
    
    if not template_class:
        raise ValueError(f"Unknown workflow template: {template_name}")
    
    return template_class.create_workflow(name, description, created_by)