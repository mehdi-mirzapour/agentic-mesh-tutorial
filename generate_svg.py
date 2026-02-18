import base64
import json
import urllib.request
import re

def generate_svg():
    # 1. Read the markdown file
    with open("docs/redis_architecture.md", "r") as f:
        content = f.read()

    # 2. Extract the mermaid block
    match = re.search(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
    if not match:
        print("No mermaid block found in docs/redis_architecture.md")
        return

    mermaid_code = match.group(1).strip()
    
    # 3. Encode for mermaid.ink
    # The format is simple base64, but using json object {"code": "...", "mermaid": {...}} is safer for config
    # Wait, looking at mermaid.live docs, simple base64 of the code works for the /svg endpoint too.
    # Let's try the simple method first: base64 encoded string.
    
    # Needs to be URL-safe base64 but without padding? Or just standard?
    # According to mermaid.ink: https://mermaid.ink/svg/<base64>
    # It uses standard base64 encoding.

    encoded_string = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
    
    url = f"https://mermaid.ink/svg/{encoded_string}"
    print(f"Fetching SVG from: {url}")

    try:
        with urllib.request.urlopen(url) as response:
            svg_content = response.read().decode("utf-8")
            
        # 4. Save to file
        output_path = "docs/redis_architecture.svg"
        with open(output_path, "w") as f:
            f.write(svg_content)
        
        print(f"Successfully saved SVG to {output_path}")

    except Exception as e:
        print(f"Error fetching SVG: {e}")
        # Fallback: Create HTML for manual screenshot if network fails (optional, but good practice)
        pass

if __name__ == "__main__":
    generate_svg()
