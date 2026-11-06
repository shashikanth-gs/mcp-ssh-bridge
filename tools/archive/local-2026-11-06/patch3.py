import re

with open('index.html', 'r') as f:
    content = f.read()

# Fix the grid row height in http-grid
content = content.replace("grid-template-rows: 120px 60px 100px;", "grid-template-rows: auto 60px 100px;")
content = content.replace("grid-template-rows: 120px;", "grid-template-rows: auto;")

# Replace Claude icon
claude_icon = '<i class="fa-solid fa-desktop ai-icon"></i>'
# Wait, I changed it to robot in patch_tabs.py: <i class="fa-solid fa-robot ai-icon"></i>
if '<i class="fa-solid fa-robot ai-icon"></i>' in content:
    content = content.replace('<i class="fa-solid fa-robot ai-icon"></i>', '<img src="https://unpkg.com/@lobehub/icons-static-svg@1.94.0/icons/claude-color.svg" width="32" height="32" style="margin-bottom: 8px;" alt="Claude" />')
elif '<i class="fa-solid fa-desktop ai-icon"></i>' in content:
    content = content.replace('<i class="fa-solid fa-desktop ai-icon"></i>', '<img src="https://unpkg.com/@lobehub/icons-static-svg@1.94.0/icons/claude-color.svg" width="32" height="32" style="margin-bottom: 8px;" alt="Claude" />')

# Replace ChatGPT icon (the embedded SVG)
chatgpt_svg_pattern = re.compile(r'<svg class="openai-icon".*?</svg>', re.DOTALL)
content = chatgpt_svg_pattern.sub('<img src="https://unpkg.com/@lobehub/icons-static-svg@1.94.0/icons/openai-color.svg" width="32" height="32" style="margin-bottom: 8px;" alt="OpenAI" />', content)

# Also fix the height of the bridge in STDIO grid
content = content.replace('class="stdio-grid"', 'class="stdio-grid" style="grid-template-rows: auto;"')

with open('index.html', 'w') as f:
    f.write(content)
