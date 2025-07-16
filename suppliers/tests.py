"""
Tests for Supplier models and functionality.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Supplier, SupplierProduct
from .connectors.factory import create_connector, list_available_connectors
from .utils.encryption import credential_encryption


class SupplierModelTest(TestCase):
    """Test cases for Supplier model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='test-supplier',
            description='A test supplier',
            api_base_url='https://api.testsupplier.com',
            created_by=self.user
        )
    
    def test_supplier_creation(self):
        """Test supplier is created with correct defaults."""
        self.assertEqual(self.supplier.name, 'Test Supplier')
        self.assertEqual(self.supplier.code, 'test-supplier')
        self.assertEqual(self.supplier.status, 'inactive')
        self.assertEqual(self.supplier.connector_type, 'api')
        self.assertFalse(self.supplier.is_auto_sync_enabled)
        self.assertEqual(self.supplier.sync_frequency_hours, 24)
        self.assertEqual(self.supplier.created_by, self.user)
    
    def test_code_lowercase_conversion(self):
        """Test that supplier code is converted to lowercase."""
        supplier = Supplier.objects.create(
            name='Another Supplier',
            code='UPPERCASE-CODE',
            created_by=self.user
        )
        self.assertEqual(supplier.code, 'uppercase-code')
    
    def test_credentials_encryption(self):
        """Test setting and getting encrypted credentials."""
        test_credentials = {
            'api_key': 'test-api-key-123',
            'api_secret': 'test-secret-456',
            'additional_data': {'nested': 'value'}
        }
        
        # Set credentials
        self.supplier.set_credentials(test_credentials)
        self.supplier.save()
        
        # Verify credentials are encrypted
        self.assertIsNotNone(self.supplier.encrypted_credentials)
        self.assertNotIn('test-api-key-123', self.supplier.encrypted_credentials)
        
        # Get decrypted credentials
        decrypted = self.supplier.get_decrypted_credentials()
        self.assertEqual(decrypted['api_key'], 'test-api-key-123')
        self.assertEqual(decrypted['api_secret'], 'test-secret-456')
        self.assertEqual(decrypted['additional_data']['nested'], 'value')
    
    def test_sync_status_update(self):
        """Test updating sync status."""
        # Test successful sync
        self.supplier.update_sync_status(True)
        self.assertEqual(self.supplier.last_sync_status, 'success')
        self.assertEqual(self.supplier.last_sync_error, '')
        self.assertIsNotNone(self.supplier.last_sync_at)
        
        # Test failed sync
        self.supplier.update_sync_status(False, 'Connection timeout')
        self.assertEqual(self.supplier.last_sync_status, 'failed')
        self.assertEqual(self.supplier.last_sync_error, 'Connection timeout')
    
    def test_is_sync_due_property(self):
        """Test the is_sync_due property."""
        # Should not be due if auto sync is disabled
        self.assertFalse(self.supplier.is_sync_due)
        
        # Enable auto sync but no last sync
        self.supplier.is_auto_sync_enabled = True
        self.assertFalse(self.supplier.is_sync_due)
        
        # Set last sync to recent time
        from django.utils import timezone
        self.supplier.last_sync_at = timezone.now()
        self.assertFalse(self.supplier.is_sync_due)


class SupplierProductModelTest(TestCase):
    """Test cases for SupplierProduct model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='test-supplier',
            created_by=self.user
        )
        
        self.product = SupplierProduct.objects.create(
            supplier=self.supplier,
            supplier_sku='TEST-SKU-001',
            supplier_name='Test Product',
            description='A test product',
            cost_price=10.99,
            quantity_available=100
        )
    
    def test_product_creation(self):
        """Test product is created with correct defaults."""
        self.assertEqual(self.product.supplier, self.supplier)
        self.assertEqual(self.product.supplier_sku, 'TEST-SKU-001')
        self.assertEqual(self.product.status, 'active')
        self.assertEqual(self.product.currency, 'USD')
        self.assertEqual(self.product.min_order_quantity, 1)
    
    def test_unique_constraint(self):
        """Test unique constraint on supplier and SKU."""
        with self.assertRaises(Exception):
            SupplierProduct.objects.create(
                supplier=self.supplier,
                supplier_sku='TEST-SKU-001',  # Same SKU
                supplier_name='Another Product'
            )
    
    def test_is_in_stock_property(self):
        """Test the is_in_stock property."""
        # Should be in stock with quantity > 0 and active status
        self.assertTrue(self.product.is_in_stock)
        
        # Not in stock if quantity is 0
        self.product.quantity_available = 0
        self.assertFalse(self.product.is_in_stock)
        
        # Not in stock if status is not active
        self.product.quantity_available = 100
        self.product.status = 'discontinued'
        self.assertFalse(self.product.is_in_stock)
    
    def test_primary_image_url_property(self):
        """Test the primary_image_url property."""
        # No images
        self.assertIsNone(self.product.primary_image_url)
        
        # With images
        self.product.image_urls = [
            'https://example.com/image1.jpg',
            'https://example.com/image2.jpg'
        ]
        self.assertEqual(
            self.product.primary_image_url, 
            'https://example.com/image1.jpg'
        )
    
    def test_update_from_supplier_data(self):
        """Test updating product from supplier data."""
        supplier_data = {
            'name': 'Updated Product Name',
            'description': 'Updated description',
            'category': 'Electronics',
            'brand': 'TestBrand',
            'price': 15.99,
            'quantity': 50,
            'extra_field': 'extra_value'
        }
        
        self.product.update_from_supplier_data(supplier_data)
        
        self.assertEqual(self.product.supplier_name, 'Updated Product Name')
        self.assertEqual(self.product.description, 'Updated description')
        self.assertEqual(self.product.category, 'Electronics')
        self.assertEqual(self.product.brand, 'TestBrand')
        self.assertEqual(self.product.cost_price, 15.99)
        self.assertEqual(self.product.quantity_available, 50)
        self.assertEqual(self.product.supplier_data, supplier_data)
        self.assertIsNotNone(self.product.last_updated_from_supplier)


class EncryptionUtilsTest(TestCase):
    """Test cases for encryption utilities."""
    
    def test_encrypt_decrypt_cycle(self):
        """Test encrypting and decrypting data."""
        test_data = {
            'key1': 'value1',
            'key2': 123,
            'key3': {'nested': 'data'},
            'key4': ['list', 'items']
        }
        
        # Encrypt
        encrypted = credential_encryption.encrypt_credentials(test_data)
        self.assertIsInstance(encrypted, str)
        self.assertNotIn('value1', encrypted)
        
        # Decrypt
        decrypted = credential_encryption.decrypt_credentials(encrypted)
        self.assertEqual(decrypted, test_data)
    
    def test_empty_credentials(self):
        """Test handling of empty credentials."""
        # Empty dict
        encrypted = credential_encryption.encrypt_credentials({})
        self.assertEqual(encrypted, "")
        
        # Decrypt empty
        decrypted = credential_encryption.decrypt_credentials("")
        self.assertIsNone(decrypted)
    
    def test_invalid_encrypted_data(self):
        """Test handling of invalid encrypted data."""
        decrypted = credential_encryption.decrypt_credentials("invalid-data")
        self.assertIsNone(decrypted)


class ConnectorFactoryTest(TestCase):
    """Test cases for connector factory."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.supplier = Supplier.objects.create(
            name='Test Supplier',
            code='example',  # Will map to example_api connector
            created_by=self.user
        )
    
    def test_create_connector(self):
        """Test creating a connector instance."""
        connector = create_connector(self.supplier)
        self.assertIsNotNone(connector)
        self.assertEqual(connector.supplier, self.supplier)
        self.assertEqual(connector.connector_name, 'Example API Connector')
    
    def test_list_available_connectors(self):
        """Test listing available connectors."""
        connectors = list_available_connectors()
        self.assertIn('example_api', connectors)
        self.assertEqual(
            connectors['example_api']['name'], 
            'Example API Connector'
        )
