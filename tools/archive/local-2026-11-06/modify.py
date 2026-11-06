import re

with open('index.html', 'r') as f:
    content = f.read()

# Define the new CSS for the grid layout
new_css = """
      /* Custom CSS Flow Diagram (Grid based) */
      .flow-diagram { 
        display: grid; 
        grid-template-columns: 180px 180px 200px 60px 180px; 
        gap: 16px; 
        align-items: center; 
        font-family: 'Inter', sans-serif; 
        min-width: 864px; 
      }
      
      .flow-node { 
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 20px; background: white; border: 1px solid var(--line); 
        border-radius: 16px; box-shadow: 0 8px 24px rgba(22,32,29,.04); text-align: center; 
        position: relative; z-index: 2;
      }
      .flow-node i { font-size: 26px; margin-bottom: 14px; }
      .flow-node h4 { margin: 0 0 6px 0; font-size: 14px; font-weight: 700; color: var(--ink); }
      .flow-node p { margin: 0; font-size: 11px; color: var(--muted); line-height: 1.4; }

      .flow-node.ai i { color: #3b82f6; }
      .flow-node.bridge { border-color: var(--green); box-shadow: 0 8px 24px rgba(49,134,111,.1); }
      .flow-node.bridge i { color: var(--green); }
      .flow-node.auth { border-color: #f59e0b; padding: 12px; }
      .flow-node.auth i { color: #f59e0b; font-size: 20px; margin-bottom: 8px; }
      .flow-node.server i { color: #f43f5e; }

      .col-clients { display: flex; flex-direction: column; gap: 32px; }
      .col-paths { display: flex; flex-direction: column; gap: 32px; height: 100%; justify-content: center; position: relative; }
      .col-bridge { display: flex; align-items: center; justify-content: center; }
      .col-targets { display: flex; flex-direction: column; gap: 24px; }

      .flow-path { position: relative; display: flex; align-items: center; justify-content: center; height: 40px; width: 100%; }
      .path-label { 
        font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; 
        background: #fafcfa; padding: 2px 8px; z-index: 2; letter-spacing: 0.05em; border-radius: 4px; 
      }
      .line-h { position: absolute; height: 2px; background: var(--line); width: 100%; top: 50%; left: 0; z-index: 1; }
      .line-h.arrow-right::after { 
        content: ''; position: absolute; right: -2px; top: -4px; 
        border-width: 5px; border-style: solid; border-color: transparent transparent transparent var(--line); 
      }
      .line-v { position: absolute; width: 2px; background: var(--line); height: 10px; left: 50%; top: 40px; z-index: 1; }
      
      .fork-paths { position: relative; height: 140px; width: 100%; }
      .fork-paths::before { content: ''; position: absolute; left: 0; top: 35px; bottom: 35px; width: 50%; border-top: 2px solid var(--line); border-bottom: 2px solid var(--line); border-left: 2px solid var(--line); z-index: 1; }
      .fork-paths::after { content: ''; position: absolute; left: 0; top: 50%; width: 50%; height: 2px; background: var(--line); z-index: 1; }
      .fork-arrow { position: absolute; left: 50%; width: 50%; height: 2px; background: var(--line); z-index: 1; }
      .fork-arrow.top { top: 35px; }
      .fork-arrow.bottom { bottom: 35px; }
      .fork-arrow::after { content: ''; position: absolute; right: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent transparent transparent var(--line); }
"""

# Define the new HTML for the diagram
new_html = """
                <div class="flow-diagram">
                  <!-- Column 1: Clients -->
                  <div class="col-clients">
                    <div class="flow-node ai">
                      <i class="fa-solid fa-desktop"></i>
                      <h4>Claude / VS Code</h4>
                      <p>Local Desktop Client</p>
                    </div>
                    <div class="flow-node ai">
                      <i class="fa-solid fa-cloud"></i>
                      <h4>ChatGPT Web</h4>
                      <p>Remote Web Client</p>
                    </div>
                  </div>

                  <!-- Column 2: Transports & Auth -->
                  <div class="col-paths">
                    <!-- STDIO Path -->
                    <div class="flow-path">
                      <div class="line-h arrow-right"></div>
                      <span class="path-label">STDIO</span>
                    </div>
                    
                    <!-- HTTP Path with Auth -->
                    <div style="position: relative; display: flex; flex-direction: column; align-items: center; margin-top: 10px;">
                      <div class="flow-path">
                        <div class="line-h arrow-right"></div>
                        <span class="path-label">HTTP / SSE</span>
                      </div>
                      
                      <!-- Auth Node -->
                      <div class="line-v"></div>
                      <div class="flow-node auth" style="margin-top: 10px;">
                        <i class="fa-solid fa-shield-halved"></i>
                        <h4>OAuth 2.0 IDP</h4>
                        <p>Auth Middleware</p>
                      </div>
                    </div>
                  </div>

                  <!-- Column 3: Bridge -->
                  <div class="col-bridge">
                    <div class="flow-node bridge" style="height: 180px;">
                      <i class="fa-solid fa-network-wired"></i>
                      <h4>SSH Bridge</h4>
                      <p>Python Application<br/>Access Control & SFTP</p>
                    </div>
                  </div>

                  <!-- Column 4: Fork -->
                  <div class="col-fork">
                    <div class="fork-paths">
                      <div class="fork-arrow top"></div>
                      <div class="fork-arrow bottom"></div>
                    </div>
                  </div>

                  <!-- Column 5: Targets -->
                  <div class="col-targets">
                    <div class="flow-node server">
                      <i class="fa-solid fa-server"></i>
                      <h4>Remote Server 1</h4>
                      <p>Web Host / Linux</p>
                    </div>
                    <div class="flow-node server">
                      <i class="fa-solid fa-database"></i>
                      <h4>Remote Server 2</h4>
                      <p>Database Instance</p>
                    </div>
                  </div>
                </div>
"""

# Replace the CSS
css_start = content.find("/* Custom CSS Flow Diagram */")
css_end = content.find("/* Features */")
content = content[:css_start] + new_css + "\n      " + content[css_end:]

# Replace the HTML
html_start = content.find('<div class="flow-diagram">')
html_end = content.find('</div>\n\n              </div>\n            </div>\n          </div>\n        </section>')
if html_end == -1:
    html_end = content.find('</div>\n              </div>\n            </div>\n          </div>\n        </section>')

# Note: We just look for the end of the flow-diagram. The easiest way is to use regex or string methods.
# The flow-diagram div ends right before `</div>\n\n              </div>\n            </div>\n          </div>\n        </section>`
import textwrap

html_pattern = re.compile(r'<div class="flow-diagram">.*?</div>\s*</div>\s*</div>\s*</div>\s*</section>', re.DOTALL)
# Wait, let's just find <div class="flow-diagram"> and the corresponding closing div.

# Let's do a simple replace since we control the exact text.
old_html_content = content[html_start:content.find('</div>\n\n              </div>', html_start)]
content = content.replace(old_html_content, new_html.strip())

with open('index.html', 'w') as f:
    f.write(content)

print("Modified successfully")
