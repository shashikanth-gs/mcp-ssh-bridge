import re

with open('index.html', 'r') as f:
    content = f.read()

new_footer = """
      <footer class="site-footer">
        <div class="section-wrap" style="display: flex; flex-direction: row; justify-content: space-between; align-items: center;">
          <p style="margin: 0; display: flex; align-items: center; gap: 8px;">
            <i class="fa-solid fa-code" style="color: var(--green);"></i> 
            Open source by <a href="https://www.shashikanth.me" target="_blank">Shashikanth GS</a>
          </p>
          <div style="display: flex; gap: 24px;">
            <a href="https://www.shashikanth.me" target="_blank" style="display: flex; align-items: center; gap: 6px;">
              <i class="fa-solid fa-globe"></i> shashikanth.me
            </a>
            <a href="https://github.com/shashikanth-gs" target="_blank" style="display: flex; align-items: center; gap: 6px;">
              <i class="fa-brands fa-github"></i> GitHub
            </a>
          </div>
        </div>
      </footer>
"""

footer_pattern = re.compile(r'<footer class="site-footer">.*?</footer>', re.DOTALL)
content = footer_pattern.sub(new_footer.strip(), content)

# I should also make sure the footer looks good on mobile by tweaking the inline styles or letting it wrap.
# Let's remove the inline flex and just add classes, but inline is fine for small tweaks.
# Actually, I'll update the CSS for site-footer to handle flex.

css_footer = """
      .site-footer { border-top: 1px solid var(--line); padding: 48px 0; background: white; }
      .footer-inner { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 24px; }
      .site-footer p { margin: 0; color: var(--muted); font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 8px; }
      .site-footer .footer-links { display: flex; gap: 24px; }
      .site-footer a { color: var(--ink); font-weight: 600; text-decoration: none; display: flex; align-items: center; gap: 6px; transition: color .2s; }
      .site-footer a:hover { color: var(--green); }
      @media (max-width: 768px) {
        .footer-inner { flex-direction: column; text-align: center; justify-content: center; }
      }
"""

new_footer_html = """
      <footer class="site-footer">
        <div class="section-wrap footer-inner">
          <p><i class="fa-solid fa-code" style="color: var(--green);"></i> Open source by Shashikanth GS</p>
          <div class="footer-links">
            <a href="https://www.shashikanth.me" target="_blank"><i class="fa-solid fa-globe"></i> shashikanth.me</a>
            <a href="https://github.com/shashikanth-gs" target="_blank"><i class="fa-brands fa-github"></i> GitHub</a>
          </div>
        </div>
      </footer>
"""

# Replace CSS
css_pattern = re.compile(r'/\* Footer \*/.*?@media', re.DOTALL)
content = css_pattern.sub('/* Footer */\n' + css_footer.strip() + '\n\n      @media', content)

# Replace HTML
content = footer_pattern.sub(new_footer_html.strip(), content)

with open('index.html', 'w') as f:
    f.write(content)
