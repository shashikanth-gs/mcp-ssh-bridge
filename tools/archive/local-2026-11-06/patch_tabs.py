import re

with open('index.html', 'r') as f:
    content = f.read()

new_css = """
      /* The Grid */
      .stdio-grid { 
        display: grid; 
        grid-template-columns: 180px 140px 220px 140px 180px; 
        gap: 16px; 
        align-items: center; 
        justify-items: center;
        font-family: 'Inter', sans-serif; 
        min-width: 864px;
      }
      .http-grid { 
        display: grid; 
        grid-template-columns: 180px 140px 220px 140px 180px; 
        grid-template-rows: 120px 60px 100px;
        gap: 16px; 
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
      .flow-node svg { width: 24px; height: 24px; margin-bottom: 8px; fill: currentColor; }
      .flow-node h4 { margin: 0 0 4px 0; font-size: 13px; font-weight: 700; color: var(--ink); }
      .flow-node p { margin: 0; font-size: 11px; color: var(--muted); line-height: 1.3; }

      .node-bridge { border-color: var(--green); box-shadow: 0 8px 24px rgba(49,134,111,.1); padding: 24px;}
      .node-bridge i.main-icon { color: var(--green); font-size: 32px; margin-bottom: 12px;}

      .node-idp { border-color: #f59e0b; }
      .node-idp i { color: #f59e0b; }

      .node-server { border-color: #f43f5e; }
      .node-server i { color: #f43f5e; font-size: 32px;}

      .ai-icon { color: #d97757; }
      .openai-icon { color: #10a37f; }
      
      .badge { background: rgba(22,32,29,.04); padding: 8px; border-radius: 8px; border: 1px solid var(--line); font-size: 11px; font-weight: 600; color: var(--ink); width: 100%; margin-top: 6px; }

      /* Connectors */
      .connector { position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; z-index: 1;}
      .line-h { position: absolute; width: 100%; height: 2px; background: var(--line); top: 50%; left: 0; transform: translateY(-50%);}
      .line-v { position: absolute; width: 2px; height: 100%; background: var(--line); left: 50%; top: 0; transform: translateX(-50%);}
      .arrow-right::after { content: ''; position: absolute; right: -2px; top: -4px; border-width: 5px; border-style: solid; border-color: transparent transparent transparent var(--line); }
      .arrow-down::after { content: ''; position: absolute; bottom: -2px; left: -4px; border-width: 5px; border-style: solid; border-color: var(--line) transparent transparent transparent; }
      .arrow-both-v::after { content: ''; position: absolute; bottom: -2px; left: -4px; border-width: 5px; border-style: solid; border-color: var(--line) transparent transparent transparent; }
      .arrow-both-v::before { content: ''; position: absolute; top: -2px; left: -4px; border-width: 5px; border-style: solid; border-color: transparent transparent var(--line) transparent; }

      .label { background: #fafcfa; padding: 2px 8px; font-size: 10px; font-weight: 700; color: var(--muted); z-index: 2; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;}
      
      .stage-tabs { display: flex; gap: 4px; padding: 4px; border: 1px solid rgba(22,32,29,.08); border-radius: 10px; background: #eff3f1; }
      .stage-tabs button { border: 0; border-radius: 7px; padding: 7px 12px; color: #6e7a76; background: transparent; cursor: pointer; font-size: 11px; font-weight: 700; transition: .2s; }
      .stage-tabs button span { margin-right: 7px; color: #97a49f; font-family: 'Fira Code', monospace; }
      .stage-tabs button.active { color: var(--green-dark); background: white; box-shadow: 0 2px 8px rgba(30,54,46,.08); }
"""

new_html = """
              <div class="stage-toolbar" style="justify-content: space-between;">
                <div class="window-dots">
                  <i></i><i></i><i></i>
                </div>
                <div class="stage-tabs">
                  <button id="tab-stdio" class="active" onclick="document.getElementById('flow-stdio').style.display='grid'; document.getElementById('flow-http').style.display='none'; document.getElementById('tab-stdio').classList.add('active'); document.getElementById('tab-http').classList.remove('active');"><span>1</span> STDIO</button>
                  <button id="tab-http" onclick="document.getElementById('flow-stdio').style.display='none'; document.getElementById('flow-http').style.display='grid'; document.getElementById('tab-http').classList.add('active'); document.getElementById('tab-stdio').classList.remove('active');"><span>2</span> HTTP / SSE</button>
                </div>
                <div style="width: 42px;"></div>
              </div>
              <div class="stage-content">
                
                <!-- STDIO FLOW -->
                <div id="flow-stdio" class="stdio-grid">
                  <div class="flow-node ai">
                    <i class="fa-solid fa-desktop ai-icon"></i>
                    <h4>Claude Desktop</h4>
                    <p>MCP Host</p>
                  </div>
                  
                  <div class="connector">
                    <div class="line-h arrow-right"></div>
                    <span class="label">STDIO Transport</span>
                  </div>

                  <div class="flow-node node-bridge">
                    <i class="fa-solid fa-network-wired main-icon"></i>
                    <h4 style="font-size: 16px;">SSH MCP Bridge</h4>
                    <p style="margin-bottom: 8px;">MCP Server</p>
                    <div class="badge"><i class="fa-solid fa-file-export" style="color: var(--green); margin-right: 4px;"></i> Secure SSH + SFTP</div>
                  </div>

                  <div class="connector">
                    <div class="line-h arrow-right"></div>
                    <span class="label">Secure SSH</span>
                  </div>

                  <div class="flow-node node-server">
                    <i class="fa-solid fa-server"></i>
                    <h4>Remote Target</h4>
                    <p>Web Host / DB</p>
                  </div>
                </div>

                <!-- HTTP/SSE FLOW -->
                <div id="flow-http" class="http-grid" style="display: none;">
                  <div class="flow-node" style="grid-row: 1; grid-column: 1;">
                    <svg class="openai-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.073zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.8956zm16.0993 3.8558L12.5973 8.3829v-2.3324a.0804.0804 0 0 1 .0332-.0615l4.3329-2.5055a4.4992 4.4992 0 0 1 6.1408 1.6464 4.4708 4.4708 0 0 1 .5346 3.0137l-.1416-.0852-4.783-2.7582a.7712.7712 0 0 0-.7806 0l-5.8428 3.3685zm4.0152-6.5658a4.485 4.485 0 0 1-2.3655 1.9728V5.6826a.7664.7664 0 0 0-.3879-.6765L13.8875 1.6518l2.0201-1.1685a.0757.0757 0 0 1 .071 0l4.8303 2.7864a4.504 4.504 0 0 1-4.3541 1.9161zM8.5202 3.864a4.4755 4.4755 0 0 1 2.8764 1.0408l-.1416.0804-4.7783 2.7582a.7948.7948 0 0 0-.3927.6813v6.7369l-2.02-1.1686a.071.071 0 0 1-.038-.052V8.3584A4.504 4.504 0 0 1 8.5202 3.864zM12 14.8966a2.8966 2.8966 0 1 1 0-5.7932 2.8966 2.8966 0 0 1 0 5.7932z" />
                    </svg>
                    <h4>ChatGPT</h4>
                    <p>MCP Host (Web)</p>
                  </div>

                  <div class="connector" style="grid-row: 1; grid-column: 2;">
                    <div class="line-h arrow-right"></div>
                    <span class="label">HTTP / SSE</span>
                  </div>

                  <div class="flow-node node-bridge" style="grid-row: 1; grid-column: 3;">
                    <i class="fa-solid fa-network-wired main-icon"></i>
                    <h4 style="font-size: 16px;">SSH MCP Bridge</h4>
                    <p style="margin-bottom: 4px;">MCP Server</p>
                    <div class="badge"><i class="fa-solid fa-shield-halved" style="color: #f59e0b; margin-right: 4px;"></i> Auth Middleware</div>
                    <div class="badge"><i class="fa-solid fa-file-export" style="color: var(--green); margin-right: 4px;"></i> Secure SSH + SFTP</div>
                  </div>

                  <div class="connector" style="grid-row: 2; grid-column: 3;">
                    <div class="line-v arrow-both-v"></div>
                    <span class="label" style="padding: 2px 6px;">OAuth 2.0</span>
                  </div>

                  <div class="flow-node node-idp" style="grid-row: 3; grid-column: 3;">
                    <i class="fa-solid fa-id-card"></i>
                    <h4>Identity Provider</h4>
                    <p>Auth0 / Okta</p>
                  </div>

                  <div class="connector" style="grid-row: 1; grid-column: 4;">
                    <div class="line-h arrow-right"></div>
                    <span class="label">Secure SSH</span>
                  </div>

                  <div class="flow-node node-server" style="grid-row: 1; grid-column: 5;">
                    <i class="fa-solid fa-server"></i>
                    <h4>Remote Target</h4>
                    <p>Web Host / DB</p>
                  </div>
                </div>
"""

# Extract components
css_start = content.find("/* The Grid */")
css_end = content.find("/* Features */")
content = content[:css_start] + new_css + "\n      " + content[css_end:]

html_start = content.find('<div class="stage-toolbar">')
old_html = content[html_start:content.find('</div>\n\n              </div>\n            </div>\n          </div>\n        </section>', html_start)]
content = content.replace(old_html, new_html.strip())

with open('index.html', 'w') as f:
    f.write(content)
