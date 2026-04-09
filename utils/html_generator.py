import re

def extract_html_from_llm_output(llm_output):
    """
    Extract clean HTML code from LLM output.
    Handles markdown code blocks and raw HTML.
    
    Args:
        llm_output (str): The raw response string from LLM
        
    Returns:
        str: Clean HTML document
    """
    # Pattern to match markdown code blocks containing html
    code_block_pattern = r'```html\s*(.*?)```'
    
    # Try to find HTML in code block first
    match = re.search(code_block_pattern, llm_output, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # If no code block, try to find generic code block
    code_block_pattern_generic = r'```\s*(.*?)```'
    match_generic = re.search(code_block_pattern_generic, llm_output, re.DOTALL)
    if match_generic:
        content = match_generic.group(1).strip()
        if '<html' in content.lower() or '<!doctype html>' in content.lower():
            return content
            
    # If no code blocks, check if the output itself looks like HTML
    # Look for DOCTYPE or html tag
    if '<!doctype html>' in llm_output.lower() or '<html' in llm_output.lower():
        # Try to extract from start of html to end of html
        html_start = llm_output.lower().find('<!doctype html>')
        if html_start == -1:
            html_start = llm_output.lower().find('<html')
            
        html_end = llm_output.lower().rfind('</html>')
        
        if html_start != -1 and html_end != -1:
            return llm_output[html_start:html_end + 7] # +7 for length of </html>
            
    # If we can't find structured HTML, return original output but warn/log if needed
    # For now, assuming LLM followed instructions reasonably well or this is the best we have
    return llm_output.strip()
