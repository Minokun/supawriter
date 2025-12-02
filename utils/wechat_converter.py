import markdown
from bs4 import BeautifulSoup
import re

def _fix_markdown_table_spacing(text):
    """
    Ensure tables in Markdown are preceded by a blank line to be correctly recognized.
    This handles the case where users might not leave a blank line before a table.
    It respects code blocks to avoid modifying content inside them.
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    new_lines = []
    in_code_block = False
    
    for i, line in enumerate(lines):
        # Check for code block fence
        # Markdown allows up to 3 spaces before fence
        if re.match(r'^\s{0,3}(```|~~~)', line):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue
            
        if in_code_block:
            new_lines.append(line)
            continue
        
        # Check if next line is a table separator
        if i + 1 < len(lines):
            next_line = lines[i+1]
            # Regex for separator: 
            # Max 3 spaces indentation (otherwise it's code)
            # Must contain - and |
            if re.match(r'^[ \t]{0,3}\|?[\s\-\:|]+\|?\s*$', next_line) and '-' in next_line and '|' in next_line:
                # Check if current line looks like a header (has pipes)
                if '|' in line:
                    # Check if previous line was NOT empty
                    if i > 0 and lines[i-1].strip() != '':
                        # We found a table header that is not separated from previous text
                        new_lines.append('') # Insert blank line
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def markdown_to_wechat_html(markdown_text):
    """
    Convert Markdown text to WeChat-compatible HTML with inline styles.
    """
    if not markdown_text:
        return ""

    # Preprocess markdown to fix common table issues
    markdown_text = _fix_markdown_table_spacing(markdown_text)

    # 1. Convert Markdown to basic HTML
    # Use extra extensions for better compatibility
    html = markdown.markdown(
        markdown_text, 
        extensions=[
            'fenced_code', 
            'tables', 
            'nl2br', 
            'sane_lists'
        ]
    )

    # 2. Parse with BeautifulSoup to apply styles
    soup = BeautifulSoup(html, 'html.parser')

    # 3. Define WeChat-friendly styles
    # colors
    primary_color = "#07c160" # WeChat Green
    text_color = "#333333"
    secondary_text_color = "#888888"
    bg_color = "#f7f7f7"
    code_bg_color = "#f0f0f0"
    
    styles = {
        'h1': f'font-size: 22px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; color: {text_color}; text-align: center;',
        'h2': f'font-size: 18px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; padding-left: 10px; border-left: 4px solid {primary_color}; color: {text_color}; line-height: 1.4;',
        'h3': f'font-size: 16px; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: {text_color}; display: flex; align-items: center; padding-left: 8px; border-left: 3px solid {primary_color};',
        'p': f'font-size: 16px; line-height: 1.8; margin-bottom: 20px; color: {text_color}; text-align: justify; letter-spacing: 1px;',
        'ul': f'margin-bottom: 20px; padding-left: 20px; color: {text_color}; list-style-type: disc;',
        'ol': f'margin-bottom: 20px; padding-left: 20px; color: {text_color}; list-style-type: decimal;',
        'li': 'font-size: 16px; line-height: 1.8; margin-bottom: 8px;',
        'blockquote': f'padding: 15px; margin: 20px 0; border-left: 4px solid {primary_color}; background-color: {bg_color}; color: {secondary_text_color}; font-size: 15px; line-height: 1.6; border-radius: 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);',
        'code': f'font-family: Menlo, Monaco, Consolas, "Courier New", monospace; font-size: 14px; background-color: {code_bg_color}; padding: 2px 4px; border-radius: 3px; color: #d63384;',
        'pre': f'background-color: #282c34; padding: 15px; overflow-x: auto; border-radius: 5px; margin-bottom: 20px; color: #abb2bf; font-family: Menlo, Monaco, Consolas, "Courier New", monospace; font-size: 13px; line-height: 1.5; -webkit-overflow-scrolling: touch;',
        'img': 'max-width: 100%; height: auto; display: block; margin: 20px auto; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);',
        'a': f'color: {primary_color}; text-decoration: none; border-bottom: 1px dashed {primary_color};',
        'strong': f'font-weight: bold; color: {text_color};',
        'em': 'font-style: italic;',
        'table': 'width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; border: 1px solid #e0e0e0;',
        'th': f'background-color: {primary_color}; color: #ffffff; border: 1px solid #e0e0e0; padding: 10px; text-align: left; font-weight: bold;',
        'td': 'border: 1px solid #e0e0e0; padding: 10px;',
        'hr': 'border: 0; border-top: 1px solid #eee; margin: 30px 0;'
    }

    # 4. Apply styles
    for tag, style in styles.items():
        for element in soup.find_all(tag):
            # Handle code blocks separately (pre > code) vs inline code
            if tag == 'code' and element.parent.name == 'pre':
                # Remove style from code inside pre, as pre handles the block style
                element['style'] = 'font-family: inherit; color: inherit; background-color: transparent; padding: 0;' 
                continue 
            
            # Special handling for h3 to add a small icon or dot if desired
            # Here we just apply the style
            
            # Merge existing style with new style
            existing_style = element.get('style', '')
            # We prioritize our styles but allow existing styles to override if they were there (unlikely from pure markdown)
            # Actually for WeChat, we want to enforce our styles
            new_style = f"{style} {existing_style}".strip()
            element['style'] = new_style

    # 4.1 Special handling for tables: zebra striping and wrapping
    for table in soup.find_all('table'):
        # Apply zebra striping to rows
        rows = table.find_all('tr')
        for i, row in enumerate(rows):
            # Skip header row if it's inside thead
            if row.parent.name == 'thead':
                continue
            
            # Apply background color to even rows (0-indexed, so actually 2nd, 4th...)
            if i % 2 == 1:
                existing_style = row.get('style', '')
                row['style'] = f"{existing_style} background-color: #f9f9f9;".strip()
        
        # Wrap table in a scrollable container
        wrapper = soup.new_tag("section", style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px; max-width: 100%;")
        table.wrap(wrapper)

    # 5. Additional processing for images to ensure they have proper structure
    # WeChat likes images in a container sometimes, but simple img tag usually works
    # Let's add a caption if alt text exists
    for img in soup.find_all('img'):
        alt = img.get('alt')
        if alt and alt != '图片':
            # Create a figure-like structure
            # <div style="text-align: center;">
            #   <img ...>
            #   <span style="font-size: 12px; color: #888; display: block; margin-top: 5px;">alt</span>
            # </div>
            
            wrapper = soup.new_tag("div", style="text-align: center; margin: 20px 0;")
            caption = soup.new_tag("span", style="font-size: 14px; color: #888; display: block; margin-top: 6px;")
            caption.string = alt
            
            img.wrap(wrapper)
            wrapper.append(caption)

    # 6. Wrap in a main container
    container = soup.new_tag("div", id="wechat-content", style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #333; padding: 10px; background-color: #fff;")
    
    # Move all top-level elements to container
    # list(soup.contents) is needed because we are modifying the tree
    for element in list(soup.contents):
        container.append(element)
    
    return str(container)

