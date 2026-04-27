import re

def update_styles():
    filepath = "c:/Users/mauri/OneDrive/Desktop/Atlas/apps/desktop/styles.css"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    replacement_top = """/* Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  /* ── Premium Dark Theme Palette ── */
  --bg-color: #05050A; /* Deep space dark */
  --bg-surface: #0B0E17;
  --card-bg: rgba(15, 20, 31, 0.45);
  
  --text-primary: #FFFFFF;
  --text-secondary: #8B949E;
  
  --accent-green: #00FF88;
  --accent-orange: #FFB020;
  --accent-red: #FF3366;
  --border-color: rgba(255, 255, 255, 0.08);
  --bg-dark: #000000;

  /* ── Typography ── */
  --font-serif: 'Outfit', sans-serif;
  --font-sans: 'Inter', sans-serif;

  /* ── Compatibility aliases ── */
  --bg-deep:      #000000;
  --glass-sm:     rgba(255, 255, 255, 0.02);
  --glass-md:     rgba(255, 255, 255, 0.04);
  --glass-lg:     rgba(255, 255, 255, 0.08);
  --bdr-faint:    rgba(255, 255, 255, 0.04);
  --bdr-soft:     rgba(255, 255, 255, 0.08);
  --bdr-subtle:   rgba(255, 255, 255, 0.12);
  --bdr-strong:   rgba(255, 255, 255, 0.2);
  --txt-primary:  #FFFFFF;
  --txt-secondary:#A1A1AA;
  --txt-muted:    #71717A;
  --ff-body:      'Inter', sans-serif;
  --ff-mono:      'Courier New', Courier, monospace;
  --ff-display:   'Outfit', sans-serif;
  
  --orange:       #FFB020;
  --green:        #00FF88;
  --red:          #FF3366;
  --cyan:         #00F0FF;
  --purple:       #b5179e;
  --accent-color: #00F0FF;
  
  --glow-cyan:    0 0 15px rgba(0, 240, 255, 0.2);
  --glow-green:   0 0 15px rgba(0, 255, 136, 0.2);
  --glow-blue:    0 0 12px rgba(74,127,160,0.18);
  --glow-purple:  0 0 15px rgba(181, 23, 158, 0.2);

  /* ── Animation easing ── */
  --ease-spring:  cubic-bezier(0.175, 0.885, 0.32, 1.275);
  --ease-smooth:  cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out:     cubic-bezier(0, 0, 0.2, 1);
}"""

    # Replace the top chunk
    content = re.sub(r"/\* Fonts \*/.*?\}\n", replacement_top + "\n", content, flags=re.DOTALL)

    # Remove italic styling
    content = content.replace("font-style: italic;", "")

    # Replace hard borders
    content = content.replace("border: 1px solid var(--text-primary);", "border: 1px solid var(--border-color);")
    content = content.replace("border-right: 1px solid var(--text-primary);", "border-right: 1px solid var(--border-color);")
    content = content.replace("border-top: 1px solid var(--text-primary);", "border-top: 1px solid var(--border-color);")
    content = content.replace("border-bottom: 1px solid var(--text-primary);", "border-bottom: 1px solid var(--border-color);")

    # Change terminal icon background
    content = content.replace(".module-icon.terminal {\n  background: #1A1A1A;\n  color: white;\n}", ".module-icon.terminal {\n  background: rgba(255, 255, 255, 0.1);\n  color: white;\n}")
    
    # Update avatar background
    content = content.replace("background: #E0E0E0;", "background: rgba(255,255,255,0.1);")

    # Update stat-value fonts
    content = content.replace("font-family: var(--font-serif);", "font-family: var(--font-serif); font-weight: 600;")
    
    # Inject backdrop-filter for glassmorphism
    glass_classes = ['.module-card', '.overview-grid', '.input-area', '.status-card', '.scenario-card']
    for cls in glass_classes:
        content = re.sub(r'(' + re.escape(cls) + r' \{[^\}]*?)(?!\n\s*backdrop-filter)', r'\1\n  backdrop-filter: blur(16px);\n  -webkit-backdrop-filter: blur(16px);', content)

    # Status card tweaks
    content = content.replace("background: var(--accent-green);", "background: rgba(0, 255, 136, 0.1); border-color: rgba(0, 255, 136, 0.3);")
    content = content.replace("color: #4A5D2E;", "color: var(--accent-green);")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("styles.css updated successfully.")

if __name__ == "__main__":
    update_styles()
