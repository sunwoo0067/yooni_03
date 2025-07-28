"""
Validation utilities for the application
"""
import re
from typing import Optional, Any, Dict, List
from datetime import datetime
from decimal import Decimal


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number (Korean format)"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Check Korean phone number patterns
    patterns = [
        r'^01[0-9]{8,9}$',  # Mobile
        r'^0[2-9][0-9]{7,8}$',  # Landline
    ]
    
    return any(re.match(pattern, digits) for pattern in patterns)


def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_price(price: Any) -> bool:
    """Validate price value"""
    try:
        price_decimal = Decimal(str(price))
        return price_decimal >= 0
    except:
        return False


def validate_quantity(quantity: Any) -> bool:
    """Validate quantity value"""
    try:
        qty = int(quantity)
        return qty >= 0
    except:
        return False


def validate_sku(sku: str) -> bool:
    """Validate SKU format"""
    if not sku or not isinstance(sku, str):
        return False
    
    # SKU should be alphanumeric with optional hyphens and underscores
    pattern = r'^[A-Za-z0-9_-]+$'
    return bool(re.match(pattern, sku)) and len(sku) <= 100


def validate_date(date_string: str, format: str = '%Y-%m-%d') -> bool:
    """Validate date string format"""
    try:
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False


def validate_json(data: Any) -> bool:
    """Validate if data is valid JSON serializable"""
    import json
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False


def validate_korean_business_number(business_number: str) -> bool:
    """Validate Korean business registration number"""
    # Remove hyphens
    number = re.sub(r'[-\s]', '', business_number)
    
    if not re.match(r'^\d{10}$', number):
        return False
    
    # Korean business number validation algorithm
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    check_sum = 0
    
    for i in range(9):
        check_sum += int(number[i]) * weights[i]
    
    check_sum += (int(number[8]) * 5) // 10
    check_digit = (10 - (check_sum % 10)) % 10
    
    return check_digit == int(number[9])


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength and return detailed results
    
    Returns:
        Dict with keys: valid, score, messages
    """
    messages = []
    score = 0
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        messages.append("Password must be at least 8 characters long")
    
    # Uppercase check
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        messages.append("Password should contain at least one uppercase letter")
    
    # Lowercase check
    if re.search(r'[a-z]', password):
        score += 1
    else:
        messages.append("Password should contain at least one lowercase letter")
    
    # Number check
    if re.search(r'\d', password):
        score += 1
    else:
        messages.append("Password should contain at least one number")
    
    # Special character check
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        messages.append("Password should contain at least one special character")
    
    return {
        'valid': score >= 3,  # At least 3 criteria met
        'score': score,
        'messages': messages
    }


def validate_image_url(url: str) -> bool:
    """Validate if URL points to an image"""
    if not validate_url(url):
        return False
    
    # Check common image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    return any(url.lower().endswith(ext) for ext in image_extensions)


def validate_hex_color(color: str) -> bool:
    """Validate hex color code"""
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize string by removing harmful characters"""
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Strip whitespace
    text = text.strip()
    
    # Limit length if specified
    if max_length:
        text = text[:max_length]
    
    return text


def validate_list_of_strings(data: Any) -> bool:
    """Validate if data is a list of strings"""
    if not isinstance(data, list):
        return False
    
    return all(isinstance(item, str) for item in data)