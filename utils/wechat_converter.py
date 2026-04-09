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

def markdown_to_wechat_html(markdown_text, style="wechat"):
    """
    Convert Markdown text to WeChat-compatible HTML with inline styles.
    Supports different themes: wechat, zhihu, futuristic, elegant.
    """
    if not markdown_text:
        return ""

    # Preprocess markdown to fix common table issues
    markdown_text = _fix_markdown_table_spacing(markdown_text)

    # 1. Convert Markdown to basic HTML
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

    # 3. Define Theme-specific styles
    themes = {
        "wechat": {
            "primary": "#07c160",
            "text": "#333333",
            "secondary_text": "#888888",
            "bg": "#f7f7f7",
            "code_bg": "#f0f0f0",
            "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
        },
        "zhihu": {
            "primary": "#0066ff",
            "text": "#121212",
            "secondary_text": "#8590a6",
            "bg": "#f6f6f6",
            "code_bg": "#f4f4f4",
            "font_family": "-apple-system, BlinkMacSystemFont, 'Helvetica Neue', 'PingFang SC', 'Microsoft YaHei', sans-serif"
        },
        "futuristic": {
            "primary": "#38bdf8",
            "text": "#e2e8f0",
            "secondary_text": "#94a3b8",
            "bg": "#1e293b",
            "code_bg": "#0f172a",
            "font_family": "'Inter', 'Segoe UI', system-ui, sans-serif"
        },
        "elegant": {
            "primary": "#d4af37",
            "text": "#2c3e50",
            "secondary_text": "#7f8c8d",
            "bg": "#fdfcf0",
            "code_bg": "#f4f1de",
            "font_family": "'Georgia', 'Times New Roman', serif"
        }
    }

    theme = themes.get(style, themes["wechat"])
    
    styles = {
        'h1': f'font-size: 24px; font-weight: bold; margin-top: 35px; margin-bottom: 20px; color: {theme["text"]}; text-align: center; border-bottom: 2px solid {theme["primary"]}; padding-bottom: 10px;',
        'h2': f'font-size: 20px; font-weight: bold; margin-top: 30px; margin-bottom: 15px; padding-left: 12px; border-left: 5px solid {theme["primary"]}; color: {theme["text"]}; line-height: 1.4;',
        'h3': f'font-size: 18px; font-weight: bold; margin-top: 25px; margin-bottom: 12px; color: {theme["text"]}; padding-left: 10px; border-left: 3px solid {theme["primary"]}; opacity: 0.9;',
        'p': f'font-size: 16px; line-height: 1.8; margin-bottom: 20px; color: {theme["text"]}; text-align: justify; letter-spacing: 0.5px;',
        'ul': f'margin-bottom: 20px; padding-left: 20px; color: {theme["text"]}; list-style-type: disc;',
        'ol': f'margin-bottom: 20px; padding-left: 20px; color: {theme["text"]}; list-style-type: decimal;',
        'li': 'font-size: 16px; line-height: 1.8; margin-bottom: 8px;',
        'blockquote': f'padding: 15px 20px; margin: 25px 0; border-left: 4px solid {theme["primary"]}; background-color: {theme["bg"]}; color: {theme["secondary_text"]}; font-size: 15px; line-height: 1.7; border-radius: 8px; font-style: italic;',
        'code': f'font-family: Menlo, Monaco, Consolas, monospace; font-size: 14px; background-color: {theme["code_bg"]}; padding: 3px 6px; border-radius: 4px; color: {theme["primary"]};',
        'pre': f'background-color: #282c34; padding: 18px; overflow-x: auto; border-radius: 10px; margin-bottom: 25px; color: #abb2bf; font-family: Menlo, Monaco, Consolas, monospace; font-size: 14px; line-height: 1.6;',
        'img': 'max-width: 100%; height: auto; display: block; margin: 25px auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);',
        'a': f'color: {theme["primary"]}; text-decoration: none; border-bottom: 1px dashed {theme["primary"]};',
        'strong': f'font-weight: bold; color: {theme["text"]}; border-bottom: 2px solid {theme["primary"]}40;',
        'table': f'width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 15px; border: 1px solid #e0e0e0; background-color: {theme["bg"]}10;',
        'th': f'background-color: {theme["primary"]}; color: #ffffff; border: 1px solid #e0e0e0; padding: 12px; text-align: left; font-weight: bold;',
        'td': 'border: 1px solid #e0e0e0; padding: 12px;',
        'hr': f'border: 0; border-top: 1px solid {theme["primary"]}40; margin: 40px 0;'
    }

    # Custom theme adjustments
    if style == "elegant":
        styles['h1'] = f'font-size: 28px; font-family: serif; font-weight: normal; margin-top: 40px; margin-bottom: 30px; color: #1a1a1a; text-align: center; border-bottom: 1px solid {theme["primary"]}; padding-bottom: 15px;'
        styles['h2'] = f'font-size: 22px; font-family: serif; font-weight: normal; margin-top: 35px; margin-bottom: 20px; text-align: center; color: #1a1a1a;'
        styles['p'] = f'font-size: 17px; font-family: serif; line-height: 1.9; margin-bottom: 25px; color: {theme["text"]}; text-align: justify;'
    
    elif style == "futuristic":
        styles['h1'] = f'font-size: 26px; font-weight: 800; margin-top: 35px; margin-bottom: 20px; color: {theme["primary"]}; text-align: left; text-transform: uppercase; letter-spacing: 2px; border-left: 8px solid {theme["primary"]}; padding-left: 15px;'
        styles['p'] = f'font-size: 16px; line-height: 1.8; margin-bottom: 22px; color: {theme["text"]}; opacity: 0.9;'

    # 4. Apply styles
    for tag, st in styles.items():
        for element in soup.find_all(tag):
            if tag == 'code' and element.parent.name == 'pre':
                element['style'] = 'font-family: inherit; color: inherit; background-color: transparent; padding: 0;' 
                continue 
            
            existing_style = element.get('style', '')
            new_style = f"{st} {existing_style}".strip()
            element['style'] = new_style

    # 4.1 Table zebra striping
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for i, row in enumerate(rows):
            if row.parent.name == 'thead': continue
            if i % 2 == 1:
                existing_style = row.get('style', '')
                row['style'] = f"{existing_style} background-color: {theme['bg']}50;".strip()
        
        wrapper = soup.new_tag("section", style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 25px; max-width: 100%; border-radius: 8px;")
        table.wrap(wrapper)

    # 5. Images
    for img in soup.find_all('img'):
        alt = img.get('alt')
        if alt and alt != '图片':
            wrapper = soup.new_tag("div", style="text-align: center; margin: 25px 0;")
            caption = soup.new_tag("span", style=f"font-size: 14px; color: {theme['secondary_text']}; display: block; margin-top: 8px; font-style: italic;")
            caption.string = alt
            img.wrap(wrapper)
            wrapper.append(caption)

    # 6. Wrap in a main container
    container_style = f"font-family: {theme['font_family']}; font-size: 16px; line-height: 1.6; color: {theme['text']}; padding: 20px; background-color: {theme['bg'] if style == 'futuristic' else '#ffffff'};"
    container = soup.new_tag("div", id="wechat-content", style=container_style)
    
    for element in list(soup.contents):
        container.append(element)
    
    return str(container)

