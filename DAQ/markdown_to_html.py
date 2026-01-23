import markdown
import os
import sys
if sys.argv and len(sys.argv) < 2:
    print("A arguement specifying the input markdown file is required.")
elif len(sys.argv) >= 2:
    input_markdown_file = sys.argv[1]
    dirname = os.path.dirname(input_markdown_file)
    with open(input_markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    html_content = markdown.markdown(markdown_content)
    if len(sys.argv) == 3:
        output_file_path = sys.argv[2]
    else:
        output_file_path = os.path.join(dirname, 'README.html')
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
