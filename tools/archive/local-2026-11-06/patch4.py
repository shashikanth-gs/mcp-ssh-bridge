import re

with open('index.html', 'r') as f:
    content = f.read()

# 1. Fix the ChatGPT Logo
# First, let's find the current img tag used for ChatGPT/Codex
chatgpt_pattern = re.compile(r'<img src="https://unpkg.com/@lobehub/icons-static-svg@1.94.0/icons/[^"]+" width="32" height="32" style="margin-bottom: 8px;" alt="OpenAI" />')
openai_svg = '<svg class="openai-icon" viewBox="0 0 24 24" width="32" height="32" style="margin-bottom: 8px;" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.073zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.8956zm16.0993 3.8558L12.5973 8.3829v-2.3324a.0804.0804 0 0 1 .0332-.0615l4.3329-2.5055a4.4992 4.4992 0 0 1 6.1408 1.6464 4.4708 4.4708 0 0 1 .5346 3.0137l-.1416-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685zm4.0152-6.5658a4.485 4.485 0 0 1-2.3655 1.9728V5.6826a.7664.7664 0 0 0-.3879-.6765L13.8875 1.6518l2.0201-1.1685a.0757.0757 0 0 1 .071 0l4.8303 2.7864a4.504 4.504 0 0 1-4.3541 1.9161zM8.5202 3.864a4.4755 4.4755 0 0 1 2.8764 1.0408l-.1416.0804-4.7783 2.7582a.7948.7948 0 0 0-.3927.6813v6.7369l-2.02-1.1686a.071.071 0 0 1-.038-.052V8.3584A4.504 4.504 0 0 1 8.5202 3.864zM12 14.8966a2.8966 2.8966 0 1 1 0-5.7932 2.8966 2.8966 0 0 1 0 5.7932z" /></svg>'

if chatgpt_pattern.search(content):
    content = chatgpt_pattern.sub(openai_svg, content)
else:
    # Maybe it was already an SVG or different class
    pass

# 2. Add section-wrap to .features
features_pattern = re.compile(r'(<section class="features">)(\s*)(<div class="section-header">)')
if features_pattern.search(content):
    content = features_pattern.sub(r'\1\n<div class="section-wrap">\2\3', content)
    # find the end of the feature-grid to close section-wrap
    end_features_pattern = re.compile(r'(</div>\s*</div>\s*</section>)')
    content = end_features_pattern.sub(r'</div>\n\1', content)

# 3. Change MCP Host -> MCP Client
content = content.replace("<p>MCP Host</p>", "<p>MCP Client</p>")
content = content.replace("<p>MCP Host (Web)</p>", "<p>MCP Client (Web)</p>")

with open('index.html', 'w') as f:
    f.write(content)
