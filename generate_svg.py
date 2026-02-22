import base64
import urllib.request
import re
import os

def generate_svgs():
    # List of (input_md, output_svg) pairs
    files_to_process = [
        ("docs/redis_architecture.md", "docs/redis_architecture.svg"),
        ("docs/redis_manual_flow.md", "docs/redis_manual_flow.svg"),
        ("docs/redis_flow_diagram.md", "docs/redis_flow_diagram.svg"),
        ("docs/interaction_flow.md", "docs/interaction_flow.svg")
    ]

    for input_file, output_file in files_to_process:
        if not os.path.exists(input_file):
            print(f"Skipping {input_file}: File not found.")
            continue

        print(f"Processing {input_file}...")

        # 1. Read the markdown file
        with open(input_file, "r") as f:
            content = f.read()

        # 2. Extract the mermaid block
        # Using a more robust regex to handle various mermaid blocks
        match = re.search(r"```mermaid\s*\n(.*?)\n\s*```", content, re.DOTALL)
        if not match:
            print(f"  No mermaid block found in {input_file}")
            continue

        mermaid_code = match.group(1).strip()
        
        # 3. Encode for mermaid.ink
        encoded_string = base64.b64encode(mermaid_code.encode("utf-8")).decode("utf-8")
        url = f"https://mermaid.ink/svg/{encoded_string}"
        
        try:
            # Use a dummy user-agent to avoid potential blocks
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                svg_content = response.read().decode("utf-8")
                
            # 4. Save to file
            with open(output_file, "w") as f:
                f.write(svg_content)
            
            print(f"  Successfully saved {output_file}")

        except Exception as e:
            print(f"  Error fetching SVG for {input_file}: {e}")

if __name__ == "__main__":
    generate_svgs()
