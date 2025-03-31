import os
import re

# Path to the pages directory
PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pages')

# Authentication decorator import statement
AUTH_IMPORT = "from utils.auth_decorator import require_auth\n"

# Authentication decorator
AUTH_DECORATOR = "@require_auth\n"

def wrap_in_function(content):
    """Wrap the content in a main function and add the decorator"""
    # Check if the content already has a main function
    if re.search(r'def\s+main\s*\(\s*\)\s*:', content):
        # If it has a main function, just add the decorator before it
        content = re.sub(r'(def\s+main\s*\(\s*\)\s*:)', f"{AUTH_DECORATOR}\\1", content)
    else:
        # Find the first non-import statement
        import_end = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if not line.strip().startswith(('import ', 'from ')):
                import_end = i
                break
        
        # Split the content at the import end
        header = '\n'.join(lines[:import_end])
        body = '\n'.join(lines[import_end:])
        
        # Wrap the body in a main function
        indented_body = '\n'.join(['    ' + line if line.strip() else line for line in body.split('\n')])
        content = f"{header}\n\n{AUTH_DECORATOR}def main():\n{indented_body}\n\n# Call the main function\nmain()"
    
    return content

def add_auth_to_file(file_path):
    """Add authentication decorator to a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if the auth decorator is already in the file
    if "@require_auth" in content:
        print(f"Auth decorator already in {file_path}")
        return
    
    # Add the import if it's not already there
    if "from utils.auth_decorator import require_auth" not in content:
        if content.strip().startswith('import ') or content.strip().startswith('from '):
            # Find the last import statement
            import_end = 0
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    import_end = i
            
            # Insert the auth import after the last import
            lines.insert(import_end + 1, AUTH_IMPORT)
            content = '\n'.join(lines)
        else:
            # Add the import at the beginning
            content = AUTH_IMPORT + content
    
    # Wrap the content in a main function with the decorator
    content = wrap_in_function(content)
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Added auth to {file_path}")

def apply_auth_to_all_pages():
    """Apply authentication to all pages in the pages directory"""
    for filename in os.listdir(PAGES_DIR):
        if filename.endswith('.py'):
            file_path = os.path.join(PAGES_DIR, filename)
            add_auth_to_file(file_path)

if __name__ == "__main__":
    apply_auth_to_all_pages()
