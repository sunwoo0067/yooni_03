"""
Product utility functions
"""
import re
import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import unicodedata

from app.models.product import Product


def validate_product_data(product_data: Dict[str, Any]) -> List[str]:
    """Validate product data and return list of errors"""
    errors = []
    
    # Required fields
    if not product_data.get('sku'):
        errors.append("SKU is required")
    elif len(product_data['sku']) > 100:
        errors.append("SKU cannot exceed 100 characters")
    
    if not product_data.get('name'):
        errors.append("Product name is required")
    elif len(product_data['name']) > 500:
        errors.append("Product name cannot exceed 500 characters")
    
    # Price validation
    cost_price = product_data.get('cost_price')
    sale_price = product_data.get('sale_price')
    min_price = product_data.get('min_price')
    max_price = product_data.get('max_price')
    
    if cost_price is not None and cost_price < 0:
        errors.append("Cost price cannot be negative")
    
    if sale_price is not None and sale_price < 0:
        errors.append("Sale price cannot be negative")
    
    if min_price is not None and min_price < 0:
        errors.append("Minimum price cannot be negative")
    
    if max_price is not None and max_price < 0:
        errors.append("Maximum price cannot be negative")
    
    if min_price is not None and max_price is not None and min_price > max_price:
        errors.append("Minimum price cannot be greater than maximum price")
    
    if cost_price is not None and sale_price is not None and cost_price > sale_price:
        errors.append("Cost price should not exceed sale price")
    
    # Stock validation
    stock_quantity = product_data.get('stock_quantity', 0)
    if stock_quantity < 0:
        errors.append("Stock quantity cannot be negative")
    
    min_stock_level = product_data.get('min_stock_level', 0)
    if min_stock_level < 0:
        errors.append("Minimum stock level cannot be negative")
    
    max_stock_level = product_data.get('max_stock_level')
    if max_stock_level is not None and max_stock_level < min_stock_level:
        errors.append("Maximum stock level cannot be less than minimum stock level")
    
    # Weight validation
    weight = product_data.get('weight')
    if weight is not None and weight < 0:
        errors.append("Weight cannot be negative")
    
    shipping_weight = product_data.get('shipping_weight')
    if shipping_weight is not None and shipping_weight < 0:
        errors.append("Shipping weight cannot be negative")
    
    # Dimensions validation
    dimensions = product_data.get('dimensions')
    if dimensions:
        for dim_name, dim_value in dimensions.items():
            if dim_value is not None and dim_value < 0:
                errors.append(f"Dimension {dim_name} cannot be negative")
    
    # URL validation
    main_image_url = product_data.get('main_image_url')
    if main_image_url and not is_valid_url(main_image_url):
        errors.append("Main image URL is not valid")
    
    image_urls = product_data.get('image_urls', [])
    for i, url in enumerate(image_urls):
        if not is_valid_url(url):
            errors.append(f"Image URL {i+1} is not valid")
    
    video_urls = product_data.get('video_urls', [])
    for i, url in enumerate(video_urls):
        if not is_valid_url(url):
            errors.append(f"Video URL {i+1} is not valid")
    
    return errors


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def calculate_optimal_price(
    cost_price: Optional[Decimal],
    current_price: Optional[Decimal],
    margin_percentage: Optional[float],
    min_price: Optional[Decimal],
    max_price: Optional[Decimal],
    market_data: Optional[Dict[str, Any]] = None,
    stock_level: int = 0,
    performance_score: Optional[float] = None
) -> Decimal:
    """Calculate optimal price based on various factors"""
    
    if not cost_price or cost_price <= 0:
        return current_price or Decimal("0")
    
    # Base price using margin
    if margin_percentage:
        # Calculate price to achieve target margin
        # margin = (price - cost) / price
        # price = cost / (1 - margin/100)
        margin_decimal = Decimal(str(margin_percentage / 100))
        base_price = cost_price / (Decimal("1") - margin_decimal)
    else:
        # Default 30% markup
        base_price = cost_price * Decimal("1.3")
    
    # Adjust based on market data
    if market_data:
        competitor_avg = market_data.get('competitor_average_price')
        market_avg = market_data.get('market_average_price')
        
        if competitor_avg:
            competitor_price = Decimal(str(competitor_avg))
            # Adjust to be competitive (slightly below average)
            base_price = min(base_price, competitor_price * Decimal("0.98"))
        
        if market_avg:
            market_price = Decimal(str(market_avg))
            # Don't deviate too much from market average
            if base_price > market_price * Decimal("1.2"):
                base_price = market_price * Decimal("1.1")
            elif base_price < market_price * Decimal("0.8"):
                base_price = market_price * Decimal("0.9")
    
    # Adjust based on stock level
    if stock_level > 100:
        # High stock - reduce price slightly to move inventory
        base_price *= Decimal("0.95")
    elif stock_level < 10:
        # Low stock - can afford to price higher
        base_price *= Decimal("1.05")
    
    # Adjust based on performance score
    if performance_score:
        if performance_score > 8.0:
            # High performing product - premium pricing
            base_price *= Decimal("1.1")
        elif performance_score < 5.0:
            # Poor performing product - lower price
            base_price *= Decimal("0.9")
    
    # Apply min/max constraints
    if min_price and base_price < min_price:
        base_price = min_price
    
    if max_price and base_price > max_price:
        base_price = max_price
    
    # Round to 2 decimal places
    return base_price.quantize(Decimal('0.01'))


def generate_seo_keywords(
    name: Optional[str],
    description: Optional[str],
    brand: Optional[str],
    category_path: Optional[str]
) -> List[str]:
    """Generate SEO keywords from product data"""
    keywords = set()
    
    # Extract from name
    if name:
        name_words = extract_keywords_from_text(name)
        keywords.update(name_words)
    
    # Extract from description
    if description:
        desc_words = extract_keywords_from_text(description)
        # Take top keywords from description
        keywords.update(desc_words[:10])
    
    # Add brand
    if brand:
        keywords.add(brand.lower())
    
    # Extract from category
    if category_path:
        category_parts = category_path.split(' > ')
        for part in category_parts:
            cat_words = extract_keywords_from_text(part)
            keywords.update(cat_words)
    
    # Remove common stop words
    stop_words = {
        '이', '그', '저', '것', '의', '에', '을', '를', '은', '는', '이다', '하다',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
    }
    
    filtered_keywords = [kw for kw in keywords if kw not in stop_words and len(kw) > 2]
    
    return list(set(filtered_keywords))[:20]  # Return top 20 unique keywords


def extract_keywords_from_text(text: str) -> List[str]:
    """Extract keywords from text"""
    if not text:
        return []
    
    # Normalize text
    text = unicodedata.normalize('NFKD', text.lower())
    
    # Remove special characters and split
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    
    # Filter words (length > 2, not all digits)
    keywords = [
        word for word in words 
        if len(word) > 2 and not word.isdigit()
    ]
    
    return keywords


def optimize_product_title(
    title: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    max_length: int = 200
) -> str:
    """Optimize product title for search and platforms"""
    if not title:
        return title
    
    # Clean title
    cleaned_title = title.strip()
    
    # Add brand if not already in title
    if brand and brand.lower() not in cleaned_title.lower():
        cleaned_title = f"{brand} {cleaned_title}"
    
    # Ensure important keywords are at the beginning
    # This is a simplified version - in production, you'd use more sophisticated NLP
    
    # Truncate if too long
    if len(cleaned_title) > max_length:
        cleaned_title = cleaned_title[:max_length-3] + "..."
    
    return cleaned_title


def calculate_shipping_cost(
    weight: Optional[float],
    dimensions: Optional[Dict[str, float]],
    destination: str = "domestic",
    shipping_class: str = "standard"
) -> Decimal:
    """Calculate shipping cost based on weight and dimensions"""
    
    if not weight:
        weight = 0.5  # Default 500g
    
    base_cost = Decimal("3000")  # Base shipping cost in KRW
    
    # Weight-based calculation
    if weight <= 1.0:
        weight_cost = Decimal("0")
    elif weight <= 5.0:
        weight_cost = Decimal(str((weight - 1) * 1000))  # 1000 KRW per kg over 1kg
    else:
        weight_cost = Decimal(str(4000 + (weight - 5) * 1500))  # Higher rate for heavy items
    
    # Dimension-based calculation (if large)
    dimension_cost = Decimal("0")
    if dimensions:
        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)
        
        # Calculate volumetric weight (L x W x H / 5000)
        if length > 0 and width > 0 and height > 0:
            volumetric_weight = (length * width * height) / 5000
            if volumetric_weight > weight:
                # Use volumetric weight if larger
                additional_cost = (volumetric_weight - weight) * 500
                dimension_cost = Decimal(str(additional_cost))
    
    # Destination modifier
    destination_multiplier = Decimal("1.0")
    if destination == "international":
        destination_multiplier = Decimal("3.0")
    elif destination == "remote":
        destination_multiplier = Decimal("1.5")
    
    # Shipping class modifier
    class_multiplier = Decimal("1.0")
    if shipping_class == "express":
        class_multiplier = Decimal("2.0")
    elif shipping_class == "premium":
        class_multiplier = Decimal("1.5")
    
    total_cost = (base_cost + weight_cost + dimension_cost) * destination_multiplier * class_multiplier
    
    return total_cost.quantize(Decimal('1'))  # Round to nearest won


def generate_sku(
    brand: Optional[str] = None,
    category: Optional[str] = None,
    product_name: Optional[str] = None,
    counter: int = 1
) -> str:
    """Generate SKU from product data"""
    sku_parts = []
    
    # Brand code (first 3 letters)
    if brand:
        brand_code = re.sub(r'[^A-Za-z]', '', brand)[:3].upper()
        sku_parts.append(brand_code)
    
    # Category code (first 3 letters)
    if category:
        # Get last part of category path
        category_name = category.split(' > ')[-1] if ' > ' in category else category
        category_code = re.sub(r'[^A-Za-z]', '', category_name)[:3].upper()
        sku_parts.append(category_code)
    
    # Product code (first 4 letters of cleaned name)
    if product_name:
        product_code = re.sub(r'[^A-Za-z]', '', product_name)[:4].upper()
        sku_parts.append(product_code)
    
    # Counter (4 digits)
    counter_str = f"{counter:04d}"
    sku_parts.append(counter_str)
    
    # Join with hyphens
    sku = '-'.join(sku_parts) if sku_parts else f"PROD-{counter_str}"
    
    return sku


def generate_product_export_csv(products: List[Product]) -> str:
    """Generate CSV content for product export"""
    output = io.StringIO()
    
    # Define CSV headers
    headers = [
        'sku', 'name', 'description', 'brand', 'category_path',
        'cost_price', 'wholesale_price', 'retail_price', 'sale_price',
        'stock_quantity', 'min_stock_level', 'weight', 'status',
        'is_featured', 'tags', 'main_image_url', 'created_at', 'updated_at'
    ]
    
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    for product in products:
        row = {
            'sku': product.sku,
            'name': product.name,
            'description': product.description or '',
            'brand': product.brand or '',
            'category_path': product.category_path or '',
            'cost_price': str(product.cost_price) if product.cost_price else '',
            'wholesale_price': str(product.wholesale_price) if product.wholesale_price else '',
            'retail_price': str(product.retail_price) if product.retail_price else '',
            'sale_price': str(product.sale_price) if product.sale_price else '',
            'stock_quantity': product.stock_quantity,
            'min_stock_level': product.min_stock_level,
            'weight': str(product.weight) if product.weight else '',
            'status': product.status.value if product.status else '',
            'is_featured': product.is_featured,
            'tags': ','.join(product.tags) if product.tags else '',
            'main_image_url': product.main_image_url or '',
            'created_at': product.created_at.isoformat() if product.created_at else '',
            'updated_at': product.updated_at.isoformat() if product.updated_at else ''
        }
        writer.writerow(row)
    
    return output.getvalue()


def calculate_product_margin(cost_price: Decimal, sale_price: Decimal) -> float:
    """Calculate product margin percentage"""
    if not cost_price or not sale_price or sale_price <= 0:
        return 0.0
    
    margin = ((sale_price - cost_price) / sale_price) * 100
    return float(margin)


def calculate_markup_percentage(cost_price: Decimal, sale_price: Decimal) -> float:
    """Calculate markup percentage"""
    if not cost_price or not sale_price or cost_price <= 0:
        return 0.0
    
    markup = ((sale_price - cost_price) / cost_price) * 100
    return float(markup)


def suggest_product_improvements(product: Product) -> Dict[str, List[str]]:
    """Suggest improvements for a product"""
    suggestions = {
        'critical': [],
        'important': [],
        'minor': []
    }
    
    # Critical issues
    if not product.main_image_url:
        suggestions['critical'].append("상품 메인 이미지가 없습니다")
    
    if not product.description or len(product.description) < 50:
        suggestions['critical'].append("상품 설명이 너무 짧습니다 (최소 50자 권장)")
    
    if product.stock_quantity <= 0:
        suggestions['critical'].append("재고가 없습니다")
    
    # Important issues
    if not product.keywords or len(product.keywords) < 5:
        suggestions['important'].append("SEO 키워드가 부족합니다")
    
    if not product.brand:
        suggestions['important'].append("브랜드 정보가 없습니다")
    
    if not product.category_path:
        suggestions['important'].append("카테고리가 설정되지 않았습니다")
    
    if product.is_low_stock:
        suggestions['important'].append("재고가 부족합니다")
    
    # Minor issues
    if not product.tags or len(product.tags) < 3:
        suggestions['minor'].append("상품 태그를 추가하면 검색에 도움됩니다")
    
    if not product.seo_title:
        suggestions['minor'].append("SEO 제목을 설정하면 좋습니다")
    
    if not product.seo_description:
        suggestions['minor'].append("SEO 설명을 설정하면 좋습니다")
    
    if not product.weight:
        suggestions['minor'].append("상품 무게 정보가 없습니다")
    
    return suggestions


def clean_product_title(title: str) -> str:
    """Clean and normalize product title"""
    if not title:
        return ""
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', title.strip())
    
    # Remove special characters except common ones
    cleaned = re.sub(r'[^\w\s\-\(\)\[\]\/]', '', cleaned)
    
    # Normalize Korean characters
    cleaned = unicodedata.normalize('NFC', cleaned)
    
    return cleaned


def extract_product_features(description: str) -> List[str]:
    """Extract product features from description"""
    if not description:
        return []
    
    features = []
    
    # Look for bullet points or lists
    bullet_patterns = [
        r'[•·▪▫‣⁃]\s*(.+)',
        r'[-*]\s*(.+)',
        r'\d+\.\s*(.+)',
        r'[가-힣a-zA-Z0-9\s]+:\s*(.+)'
    ]
    
    for pattern in bullet_patterns:
        matches = re.findall(pattern, description, re.MULTILINE)
        features.extend([match.strip() for match in matches if len(match.strip()) > 5])
    
    # Remove duplicates and return top 10
    unique_features = list(dict.fromkeys(features))
    return unique_features[:10]


def validate_barcode(barcode: str) -> bool:
    """Validate barcode format (EAN-13, UPC-A, etc.)"""
    if not barcode:
        return False
    
    # Remove any non-digit characters
    digits = re.sub(r'\D', '', barcode)
    
    # Check length (8, 12, 13, or 14 digits are common)
    if len(digits) not in [8, 12, 13, 14]:
        return False
    
    # For EAN-13, check the check digit
    if len(digits) == 13:
        return validate_ean13_check_digit(digits)
    
    # For UPC-A, check the check digit
    if len(digits) == 12:
        return validate_upc_check_digit(digits)
    
    return True  # For other lengths, just check format


def validate_ean13_check_digit(ean: str) -> bool:
    """Validate EAN-13 check digit"""
    if len(ean) != 13:
        return False
    
    # Calculate check digit
    odd_sum = sum(int(ean[i]) for i in range(0, 12, 2))
    even_sum = sum(int(ean[i]) for i in range(1, 12, 2))
    total = odd_sum + (even_sum * 3)
    check_digit = (10 - (total % 10)) % 10
    
    return check_digit == int(ean[12])


def validate_upc_check_digit(upc: str) -> bool:
    """Validate UPC-A check digit"""
    if len(upc) != 12:
        return False
    
    # Calculate check digit
    odd_sum = sum(int(upc[i]) for i in range(0, 11, 2))
    even_sum = sum(int(upc[i]) for i in range(1, 11, 2))
    total = (odd_sum * 3) + even_sum
    check_digit = (10 - (total % 10)) % 10
    
    return check_digit == int(upc[11])


def format_price_for_display(price: Decimal, currency: str = "KRW") -> str:
    """Format price for display"""
    if not price:
        return "가격 미정"
    
    if currency == "KRW":
        # Korean Won - no decimal places
        formatted = f"{int(price):,}원"
    elif currency == "USD":
        # US Dollar - 2 decimal places
        formatted = f"${price:,.2f}"
    elif currency == "EUR":
        # Euro - 2 decimal places
        formatted = f"€{price:,.2f}"
    else:
        # Default format
        formatted = f"{price:,.2f} {currency}"
    
    return formatted