import os
import re
from jinja2 import Template

def generate_dark_theme_html(title, content):
    """
    Generate HTML content with dark theme styling.
    
    Args:
        title (str): The title of the HTML document
        content (str): The main content (can be HTML)
        
    Returns:
        str: Complete HTML document with dark theme styling
    """
    # Get the template path
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'templates', 'dark_theme_template.html')
    
    # Read the template
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # Create Jinja2 template
    template = Template(template_content)
    
    # Process content to add data-text attributes to any gradient-text elements
    # This ensures text is visible in screenshots
    content = fix_gradient_text_for_screenshots(content)
    
    # Render the template
    html = template.render(title=title, content=content)
    
    return html

def fix_gradient_text_for_screenshots(content):
    """
    Fix gradient text elements to ensure they display properly in screenshots.
    Adds data-text attribute with the same text content for fallback display.
    
    Args:
        content (str): HTML content
        
    Returns:
        str: Modified HTML content with fixed gradient text
    """
    # If content already has class="gradient-text" but no data-text attribute,
    # add the data-text attribute with the text content
    pattern = r'<([a-zA-Z0-9]+)\s+[^>]*class="[^"]*gradient-text[^"]*"[^>]*>([^<]+)</\1>'
    
    def add_data_text(match):
        tag = match.group(1)
        text = match.group(2)
        # Check if data-text already exists
        if 'data-text=' not in match.group(0):
            # Insert data-text attribute before the closing bracket
            return f'<{tag} class="gradient-text" data-text="{text}">{text}</{tag}>'
        return match.group(0)
    
    # Apply the fix
    fixed_content = re.sub(pattern, add_data_text, content)
    
    return fixed_content

def wrap_with_dark_theme(html_content, title="Generated Content"):
    """
    Wrap existing HTML content with dark theme styling.
    Useful for converting plain HTML to dark themed HTML.
    
    Args:
        html_content (str): Existing HTML content
        title (str): Title for the page
        
    Returns:
        str: HTML content wrapped with dark theme
    """
    # Extract body content if it's a complete HTML document
    body_content = html_content
    
    # If it's a complete HTML document, extract just the body content
    if '<body' in html_content.lower() and '</body>' in html_content.lower():
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_content = body_match.group(1)
    
    # Generate new HTML with dark theme
    return generate_dark_theme_html(title, body_content)
