"""
Text processing utilities
"""
import re
import unicodedata
from typing import List, Optional


def slugify(text: str, separator: str = '-') -> str:
    """
    Convert text to URL-friendly slug
    
    Args:
        text: Text to slugify
        separator: Character to use as separator (default: '-')
    
    Returns:
        Slugified text
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove non-alphanumeric characters (keep spaces and hyphens)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    
    # Replace spaces with separator
    text = re.sub(r'[\s-]+', separator, text)
    
    # Remove leading/trailing separators
    text = text.strip(separator)
    
    return text


def truncate(text: str, length: int, suffix: str = '...') -> str:
    """
    Truncate text to specified length
    
    Args:
        text: Text to truncate
        length: Maximum length
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= length:
        return text
    
    return text[:length - len(suffix)] + suffix


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text"""
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    return text.strip()


def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text"""
    numbers = re.findall(r'-?\d+\.?\d*', text)
    return [float(n) for n in numbers]


def remove_special_characters(text: str, keep_spaces: bool = True) -> str:
    """Remove special characters from text"""
    if keep_spaces:
        return re.sub(r'[^a-zA-Z0-9\s]', '', text)
    else:
        return re.sub(r'[^a-zA-Z0-9]', '', text)


def camel_to_snake(text: str) -> str:
    """Convert camelCase to snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(text: str, capitalize_first: bool = False) -> str:
    """Convert snake_case to camelCase"""
    components = text.split('_')
    if capitalize_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])


def count_words(text: str) -> int:
    """Count words in text"""
    words = text.split()
    return len(words)


def reverse_string(text: str) -> str:
    """Reverse a string"""
    return text[::-1]


def is_palindrome(text: str, ignore_case: bool = True, ignore_spaces: bool = True) -> bool:
    """Check if text is a palindrome"""
    if ignore_case:
        text = text.lower()
    
    if ignore_spaces:
        text = text.replace(' ', '')
    
    return text == text[::-1]


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def capitalize_first_letter(text: str) -> str:
    """Capitalize first letter of text"""
    if not text:
        return text
    return text[0].upper() + text[1:]


def remove_duplicates(text: str, delimiter: str = ' ') -> str:
    """Remove duplicate words from text"""
    words = text.split(delimiter)
    seen = set()
    result = []
    
    for word in words:
        if word not in seen:
            seen.add(word)
            result.append(word)
    
    return delimiter.join(result)


def highlight_text(text: str, keyword: str, before: str = '**', after: str = '**') -> str:
    """Highlight keyword in text"""
    if not keyword:
        return text
    
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(f'{before}{keyword}{after}', text)


def mask_sensitive_data(text: str, mask_char: str = '*', keep_chars: int = 4) -> str:
    """Mask sensitive data like credit card numbers"""
    # Mask credit card numbers (16 digits)
    cc_pattern = r'\b(\d{4})(\d{4})(\d{4})(\d{4})\b'
    text = re.sub(cc_pattern, lambda m: m.group(1) + mask_char * 8 + m.group(4), text)
    
    # Mask phone numbers (Korean format)
    phone_pattern = r'\b(01[0-9])(\d{3,4})(\d{4})\b'
    text = re.sub(phone_pattern, lambda m: m.group(1) + mask_char * len(m.group(2)) + m.group(3)[-keep_chars:], text)
    
    return text


def generate_excerpt(text: str, word_limit: int = 50) -> str:
    """Generate excerpt from text"""
    words = text.split()
    
    if len(words) <= word_limit:
        return text
    
    excerpt = ' '.join(words[:word_limit])
    
    # Try to end at sentence boundary
    last_period = excerpt.rfind('.')
    if last_period > word_limit * 5:  # If period is reasonably far
        excerpt = excerpt[:last_period + 1]
    else:
        excerpt += '...'
    
    return excerpt