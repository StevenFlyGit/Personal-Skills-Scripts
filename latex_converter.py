# -*- coding: utf-8 -*-
import json
import re
import sys
import requests

# ==============================================================================
# Notion API Configuration
# ==============================================================================
# Configure your Notion Integration Token here.
# Get one from: https://www.notion.so/my-integrations
# Make sure to share the target database/page with your integration in Notion.
NOTION_TOKEN = "YOUR_NOTION_API_TOKEN"

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

# ==============================================================================
# LaTeX Formula Processing Logic
# ==============================================================================
def text_to_notion_rich_text(text, annotations=None):
    """
    Splits text by $$...$$ or $...$ and converts formulas to Notion native
    equation objects, preserving original text annotations.
    """
    if annotations is None:
        annotations = {
            "bold": False,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default"
        }
    
    # Split by either $$...$$ (display math) or $...$ (inline math)
    parts = re.split(r'(\$\$.*?\$\$|\$.*?\$)', text)
    rich_text = []
    
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # This is a matched formula block (e.g. "$formula$" or "$$formula$$")
            if part.startswith("$$") and part.endswith("$$"):
                expr = part[2:-2].strip()
            elif part.startswith("$") and part.endswith("$"):
                expr = part[1:-1].strip()
            else:
                expr = part.strip()
            
            if expr:
                rich_text.append({
                    "type": "equation",
                    "equation": {"expression": expr},
                    "annotations": annotations
                })
        else:
            # This is regular text outside delimiters
            if part:
                rich_text.append({
                    "type": "text",
                    "text": {"content": part},
                    "annotations": annotations
                })
                
    return rich_text

# ==============================================================================
# Notion Block Helpers
# ==============================================================================
def get_block_text(block):
    """Concatenates the plain text content of all rich text items in a block."""
    btype = block.get("type")
    if not btype or btype not in block:
        return ""
    rich_text = block[btype].get("rich_text", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text)

def get_heading_level(btype):
    """Determines the level of a heading block (1, 2, or 3)."""
    if btype == "heading_1":
        return 1
    elif btype == "heading_2":
        return 2
    elif btype == "heading_3":
        return 3
    return None

def get_block_children(block_id, headers):
    """Fetches all children blocks for a given block ID, handling pagination."""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    children = []
    has_more = True
    next_cursor = None
    
    while has_more:
        params = {"page_size": 100}
        if next_cursor:
            params["start_cursor"] = next_cursor
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching children for block {block_id}: {response.text}")
            break
            
        data = response.json()
        children.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)
        
    return children

# ==============================================================================
# Update & Traversal Logic
# ==============================================================================
def update_block_formulas(block, headers):
    """Checks and updates a block's formula formatting directly via API."""
    btype = block.get("type")
    if not btype or btype not in block:
        return
        
    block_data = block[btype]
    if "rich_text" not in block_data:
        return
        
    rich_text_list = block_data.get("rich_text", [])
    if not rich_text_list:
        return
        
    needs_update = False
    new_rich_text = []
    
    for rt in rich_text_list:
        if rt.get("type") == "equation":
            new_rich_text.append(rt)
            continue
            
        content = rt.get("text", {}).get("content", "")
        # If formula symbols are present, process them
        if "$" in content:
            needs_update = True
            annotations = rt.get("annotations", {})
            converted = text_to_notion_rich_text(content, annotations)
            new_rich_text.extend(converted)
        else:
            new_rich_text.append(rt)
            
    if needs_update:
        cleaned_rich_text = []
        for rt in new_rich_text:
            item = {"type": rt["type"]}
            if rt["type"] == "text":
                item["text"] = {"content": rt["text"]["content"]}
                if "link" in rt["text"] and rt["text"]["link"]:
                    item["text"]["link"] = rt["text"]["link"]
            elif rt["type"] == "equation":
                item["equation"] = {"expression": rt["equation"]["expression"]}
            
            if "annotations" in rt:
                item["annotations"] = {
                    "bold": rt["annotations"].get("bold", False),
                    "italic": rt["annotations"].get("italic", False),
                    "strikethrough": rt["annotations"].get("strikethrough", False),
                    "underline": rt["annotations"].get("underline", False),
                    "code": rt["annotations"].get("code", False),
                    "color": rt["annotations"].get("color", "default")
                }
            cleaned_rich_text.append(item)
            
        url = f"https://api.notion.com/v1/blocks/{block['id']}"
        payload = {
            btype: {
                "rich_text": cleaned_rich_text
            }
        }
        
        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"Successfully updated block {block['id']} (Type: {btype})")
        else:
            print(f"Failed to update block {block['id']}: {response.text}")

def process_block_tree(block, headers):
    """Recursively processes formulas inside a block and its entire descendant tree."""
    update_block_formulas(block, headers)
    if block.get("has_children", False):
        children = get_block_children(block["id"], headers)
        for child in children:
            process_block_tree(child, headers)

def find_heading_block(blocks, heading_name, headers):
    """
    Recursively searches a list of blocks for a heading matching target name.
    Returns: (matched_block, subsequent_sibling_blocks)
    """
    for i, block in enumerate(blocks):
        btype = block.get("type", "")
        if btype in ("heading_1", "heading_2", "heading_3"):
            text = get_block_text(block).strip()
            if text == heading_name.strip():
                return block, blocks[i+1:]
        
        if block.get("has_children", False):
            child_blocks = get_block_children(block["id"], headers)
            result = find_heading_block(child_blocks, heading_name, headers)
            if result:
                return result
    return None

# ==============================================================================
# Main Execution Entry
# ==============================================================================
def main():
    if NOTION_TOKEN == "YOUR_NOTION_INTEGRATION_TOKEN" or not NOTION_TOKEN:
        print("Error: Please replace NOTION_TOKEN with your actual Notion Integration Token inside the script.")
        sys.exit(1)
        
    # Get parameters via CLI arguments or user prompts
    if len(sys.argv) >= 3:
        page_id = sys.argv[1]
        heading_name = sys.argv[2]
    else:
        page_id = input("Enter Notion Page ID (e.g., 1f4a89196df181648e97c2c84c024b74): ").strip()
        heading_name = input("Enter Target Heading Name: ").strip()
        
    if not page_id or not heading_name:
        print("Error: Both Page ID and Heading Name are required.")
        sys.exit(1)
        
    # Strip hyphens and whitespace from page ID
    page_id = page_id.replace("-", "").strip()
    headers = get_headers(NOTION_TOKEN)
    
    print(f"Fetching children blocks of page {page_id}...")
    page_blocks = get_block_children(page_id, headers)
    if not page_blocks:
        print("No blocks found or failed to access page. Check permissions/token.")
        sys.exit(1)
        
    print(f"Searching for heading block named: '{heading_name}'...")
    search_result = find_heading_block(page_blocks, heading_name, headers)
    if not search_result:
        print(f"Heading block '{heading_name}' not found.")
        sys.exit(1)
        
    target_block, subsequent_siblings = search_result
    target_type = target_block["type"]
    target_level = get_heading_level(target_type)
    
    print(f"Found heading '{heading_name}' (ID: {target_block['id']}, Level: {target_level})")
    
    # Collect blocks to process under this heading
    blocks_to_process = []
    
    # 1. If it's a toggle heading, collect its direct children
    if target_block.get("has_children", False):
        print("Heading has children (Toggle layout). Collecting child blocks...")
        heading_children = get_block_children(target_block["id"], headers)
        blocks_to_process.extend(heading_children)
        
    # 2. Collect subsequent sibling blocks until a heading of same or higher level is met
    for sibling in subsequent_siblings:
        sib_type = sibling.get("type", "")
        sib_level = get_heading_level(sib_type)
        if sib_level is not None and sib_level <= target_level:
            # Stop if another heading of same or higher level is reached
            break
        blocks_to_process.append(sibling)
        
    print(f"Collected {len(blocks_to_process)} direct blocks under the heading.")
    
    # Iterate and recursively process all blocks and their child trees
    print("Beginning formula conversion to native Notion LaTeX objects...")
    for block in blocks_to_process:
        process_block_tree(block, headers)
        
    print("Formula conversion completed successfully!")

if __name__ == "__main__":
    main()
