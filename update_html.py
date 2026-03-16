import re

def update_html():
    filepath = "c:/Users/mauri/OneDrive/Desktop/Atlas/apps/desktop/index.html"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Borders
    content = re.sub(r'border(?:-[a-z]+)?\s*:\s*1px solid #[345]{3,6};?', 'border:1px solid var(--border-color);', content)
    content = re.sub(r'border(?:-[a-z]+)?\s*:\s*1px solid #(?:1f2a44|22304a|111128|1a1a40);?', 'border:1px solid var(--bdr-strong);', content)
    
    # Backgrounds
    content = re.sub(r'background\s*:\s*#(?:111|222|111128|101828|0b0f1a|0f1523|101828|1a1030|0a0a20|0b101d);?', 'background:var(--card-bg);', content)
    content = re.sub(r'background\s*:\s*#(?:07070f|070710|222);?', 'background:var(--bg-surface);', content)
    
    # Text colors
    content = re.sub(r'color\s*:\s*white;?', 'color:var(--text-primary);', content)
    content = re.sub(r'color\s*:\s*#(?:ccc|e8eaf6|e0f0ff|e8e0ff|e0fff0|d0f4ff|f6e9d4|fbf6dd);?', 'color:var(--text-primary);', content)
    content = re.sub(r'color\s*:\s*#(?:888|999|aaa|9ab|778|777);?', 'color:var(--text-secondary);', content)
    content = re.sub(r'color\s*:\s*#(?:444|555|334);?', 'color:var(--txt-muted);', content)

    # Specific inline gradients that clash with the new premium dark mode
    content = re.sub(r'background\s*:\s*linear-gradient\([^)]+\)\s*;?', 'background:var(--glass-lg);', content)
    
    # Remove old classes that are not needed or fix text
    content = content.replace('color:#1A1A1A;', 'color:var(--text-primary);')
    content = content.replace('color: var(--text-secondary);', 'color: var(--text-secondary);')

    # Add glassmorphism classes to inline styled containers if missing, or just rely on the new variables.

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("index.html updated successfully.")

if __name__ == "__main__":
    update_html()
