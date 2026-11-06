import re

with open('index.html', 'r') as f:
    content = f.read()

new_css = """
      /* The Grid */
      .flow-diagram { 
        display: grid; 
        grid-template-columns: 180px 100px 220px 80px 180px; 
        grid-template-rows: 120px 40px 120px;
        gap: 16px 8px; 
        align-items: center; 
        justify-items: center;
        font-family: 'Inter', sans-serif; 
        min-width: 864px;
      }

      /* Nodes */
      .flow-node { 
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 16px; background: white; border: 1px solid var(--line); 
        border-radius: 12px; box-shadow: 0 4px 16px rgba(22,32,29,.04); text-align: center; 
        width: 100%; height: 100%; z-index: 2; position: relative;
      }
      .flow-node i { font-size: 24px; margin-bottom: 8px; }
      .flow-node h4 { margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: var(--ink); }
      .flow-node p { margin: 0; font-size: 11px; color: var(--muted); line-height: 1.3; }

      .node-claude { grid-column: 1; grid-row: 1; }
      .node-chatgpt { grid-column: 1; grid-row: 3; }
      .node-bridge { grid-column: 3; grid-row: 1 / 4; border-color: var(--green); box-shadow: 0 8px 24px rgba(49,134,111,.1); padding: 24px;}
      .node-bridge i { color: var(--green); font-size: 32px;}
      .node-idp { grid-column: 5; grid-row: 1; border-color: #f59e0b; height: 80px;}
      .node-idp i { color: #f59e0b; }
      .node-server { grid-column: 5; grid-row: 3; border-color: #f43f5e; height: 80px;}
      .node-server i { color: #f43f5e; }

      .ai i { color: #3b82f6; }

      /* Connectors */
      .connector { position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; z-index: 1;}
      .line-h { position: absolute; width: 100%; height: 2px; background: var(--line); top: 50%; left: 0; transform: translateY(-50%);}
      .arrow-right::after { content: ''; position: absolute; right: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent transparent transparent var(--line); }
      .arrow-left::after { content: ''; position: absolute; left: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent var(--line) transparent transparent; }
      .arrow-both::after { content: ''; position: absolute; right: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent transparent transparent var(--line); }
      .arrow-both::before { content: ''; position: absolute; left: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent var(--line) transparent transparent; }

      .label { background: #fafcfa; padding: 2px 8px; font-size: 10px; font-weight: 700; color: var(--muted); z-index: 2; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;}

      .conn-stdio { grid-column: 2; grid-row: 1; }
      .conn-http { grid-column: 2; grid-row: 3; }
      .conn-idp { grid-column: 4; grid-row: 1; }
      .conn-ssh { grid-column: 4; grid-row: 3; }
"""

new_html = """
                <div class="flow-diagram">

                  <!-- Column 1: Clients -->
                  <div class="flow-node ai node-claude">
                    <i class="fa-solid fa-desktop"></i>
                    <h4>Claude / VS Code</h4>
                    <p>Local Desktop Client</p>
                  </div>
                  
                  <div class="flow-node ai node-chatgpt">
                    <i class="fa-solid fa-cloud"></i>
                    <h4>ChatGPT Web</h4>
                    <p>Remote Web Client</p>
                  </div>

                  <!-- Column 2: Client Connections -->
                  <div class="connector conn-stdio">
                    <div class="line-h arrow-right"></div>
                    <span class="label">STDIO</span>
                  </div>

                  <div class="connector conn-http">
                    <div class="line-h arrow-right"></div>
                    <span class="label">HTTP / SSE</span>
                  </div>

                  <!-- Column 3: The Bridge -->
                  <div class="flow-node node-bridge">
                    <i class="fa-solid fa-network-wired"></i>
                    <h4 style="font-size: 16px;">SSH MCP Bridge</h4>
                    <p style="margin-bottom: 16px;">Python Application</p>
                    
                    <div style="display: flex; gap: 8px; flex-direction: column; width: 100%;">
                      <div style="background: rgba(22,32,29,.04); padding: 8px; border-radius: 8px; border: 1px solid var(--line); font-size: 11px; font-weight: 600; color: var(--ink);">
                        <i class="fa-solid fa-shield-halved" style="color: #f59e0b; margin-right: 4px; font-size: 12px; margin-bottom:0;"></i> Auth Middleware
                      </div>
                      <div style="background: rgba(22,32,29,.04); padding: 8px; border-radius: 8px; border: 1px solid var(--line); font-size: 11px; font-weight: 600; color: var(--ink);">
                        <i class="fa-solid fa-file-export" style="color: var(--green); margin-right: 4px; font-size: 12px; margin-bottom:0;"></i> SFTP + Execution
                      </div>
                    </div>
                  </div>

                  <!-- Column 4: Outbound Connections -->
                  <div class="connector conn-idp">
                    <div class="line-h arrow-both"></div>
                    <span class="label">OAuth 2.0</span>
                  </div>

                  <div class="connector conn-ssh">
                    <div class="line-h arrow-both"></div>
                    <span class="label">Secure SSH</span>
                  </div>

                  <!-- Column 5: External Targets -->
                  <div class="flow-node node-idp">
                    <i class="fa-solid fa-id-card"></i>
                    <h4>Identity Provider</h4>
                    <p>Auth0 / Okta / Azure</p>
                  </div>

                  <div class="flow-node node-server">
                    <i class="fa-solid fa-server"></i>
                    <h4>Remote Target</h4>
                    <p>Web Host / DB / Linux</p>
                  </div>

                </div>
"""

# Extract components
css_start = content.find("/* Custom CSS Flow Diagram (Grid based) */")
css_end = content.find("/* Features */")
content = content[:css_start] + new_css + "\n      " + content[css_end:]

html_start = content.find('<div class="flow-diagram">')
html_end = content.find('</div>\n\n              </div>\n            </div>\n          </div>\n        </section>')

if html_end == -1:
    # If the exact whitespace was slightly different
    html_pattern = re.compile(r'<div class="flow-diagram">.*?</div>\s*</div>\s*</div>\s*</div>\s*</section>', re.DOTALL)
    match = html_pattern.search(content[html_start:])
    if match:
        old_html = match.group(0)
        # We only want to replace the flow diagram itself, not the closing tags for sections.
        
old_html = content[html_start:content.find('</div>\n\n              </div>\n            </div>\n          </div>\n        </section>', html_start)]
content = content.replace(old_html, new_html.strip())

with open('index.html', 'w') as f:
    f.write(content)
