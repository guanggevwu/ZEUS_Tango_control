import markdown
import os
with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r', encoding='utf-8') as f:
    markdown_content = f.read()

html_content = markdown.markdown(markdown_content)
output_file_path = os.path.join(os.path.dirname(__file__), 'README.html')
with open(output_file_path, "w", encoding="utf-8") as f:
    f.write(html_content)
