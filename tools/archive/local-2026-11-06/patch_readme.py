import re

with open('README.md', 'r') as f:
    content = f.read()

new_quickstart = """## Quick Start

You can run the bridge instantly without cloning the repository using `pipx` or `uvx` (the Python equivalents of `npx`):

```bash
# Using pipx (Standard)
pipx run ssh-mcp-bridge config.yaml

# Using uvx (Faster)
uvx ssh-mcp-bridge config.yaml
```

Alternatively, you can install it globally using `pip`:
```bash
pip install ssh-mcp-bridge
ssh-mcp-bridge config.yaml
```

### Advanced: Local Source Deployment

If you want to modify the source code:

```bash
# 1. Clone the repository
git clone https://github.com/shashikanth-gs/mcp-ssh-bridge.git
cd mcp-ssh-bridge

# 2. Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Create configuration
cp examples/config.stdio.yaml config.yaml
# Edit config.yaml with your SSH hosts
"""

quickstart_pattern = re.compile(r'## Quick Start.*?# Edit config\.yaml with your SSH hosts\n', re.DOTALL)
content = quickstart_pattern.sub(new_quickstart.strip() + "\n", content)

with open('README.md', 'w') as f:
    f.write(content)
