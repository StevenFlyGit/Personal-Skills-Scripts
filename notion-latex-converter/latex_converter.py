# -*- coding: utf-8 -*-
import json
import re
import sys
import time
import random
import requests

# ==============================================================================
# Notion API Configuration
# ==============================================================================
# Configure your Notion Integration Token here.
# Get one from: https://www.notion.so/my-integrations
# Make sure to share the target database/page with your integration in Notion.
NOTION_TOKEN = "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"

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

class RateLimitError(Exception):
    pass

def _request_with_backoff(method, url, headers, json_payload=None, params=None, max_retries=5, base_delay=1.0):
    """
    Wrapper for requests to handle exponential backoff and retries for HTTP 429
    (rate limits) and 5xx (server errors), with random jitter.
    """
    for attempt in range(max_retries + 1):
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=json_payload, timeout=15)
            else:
                response = requests.request(method, url, headers=headers, json=json_payload, params=params, timeout=15)
                
            if response.status_code == 429:
                raise RateLimitError(f"Notion API rate limit exceeded (429). Response: {response.text}")
            
            if 500 <= response.status_code < 600:
                raise requests.exceptions.RequestException(f"Server error {response.status_code}")
                
            return response
        except (requests.exceptions.RequestException, RateLimitError) as e:
            if attempt == max_retries:
                print(f"Failed after {max_retries} retries. Last error: {e}", file=sys.stderr)
                raise e
            # Exponential backoff with random jitter
            delay = base_delay * (2 ** attempt) + random.uniform(0.0, 1.0)
            print(f"API attempt {attempt + 1} failed. Retrying in {delay:.2f} seconds... Error: {e}", file=sys.stderr)
            time.sleep(delay)

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
    parts = re.split(r'(\$\$.*?\$\$|\$.*?\$)', text, flags=re.DOTALL)
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
        
        response = _request_with_backoff("GET", url, headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching children for block {block_id}: {response.text}", file=sys.stderr)
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
    
    # Handle paragraph-to-block-equation conversion
    if btype == "paragraph":
        text_content = get_block_text(block).strip()
        if text_content.startswith("$$") and text_content.endswith("$$") and len(text_content) > 4:
            expression = text_content[2:-2].strip()
            parent_info = block.get("parent", {})
            parent_type = parent_info.get("type")
            parent_id = parent_info.get(parent_type) if parent_type in ("page_id", "block_id", "database_id") else None
            
            if parent_id:
                print(f"Converting paragraph block {block['id']} to native equation block...")
                url = f"https://api.notion.com/v1/blocks/{parent_id}/children"
                payload = {
                    "children": [
                        {
                            "object": "block",
                            "type": "equation",
                            "equation": {
                                "expression": expression
                            }
                        }
                    ],
                    "position": {
                        "type": "after_block",
                        "after_block": {
                            "id": block["id"]
                        }
                    }
                }
                append_res = _request_with_backoff("PATCH", url, headers, json_payload=payload)
                if append_res.status_code == 200:
                    print(f"Successfully appended equation block after {block['id']}.")
                    del_url = f"https://api.notion.com/v1/blocks/{block['id']}"
                    del_res = _request_with_backoff("DELETE", del_url, headers)
                    if del_res.status_code == 200:
                        print(f"Successfully deleted original paragraph block {block['id']}.")
                    else:
                        print(f"Failed to delete original block {block['id']}: {del_res.text}", file=sys.stderr)
                else:
                    print(f"Failed to append equation block after {block['id']}: {append_res.text}", file=sys.stderr)
                return

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
        
        response = _request_with_backoff("PATCH", url, headers, json_payload=payload)
        if response.status_code == 200:
            print(f"Successfully updated block {block['id']} (Type: {btype})")
        else:
            print(f"Failed to update block {block['id']}: {response.text}", file=sys.stderr)

def process_block_tree(block, headers):
    """Recursively processes formulas inside a block and its entire descendant tree."""
    update_block_formulas(block, headers)
    if block.get("has_children", False):
        children = get_block_children(block["id"], headers)
        for child in children:
            process_block_tree(child, headers)

# ==============================================================================
# Verification Logic
# ==============================================================================
def verify_block_formulas(block, headers, indent=0, corrupt_chars=None, issues_list=None):
    """
    Recursively audits a block and its child tree for unconverted formulas or
    garbled characters.
    """
    if corrupt_chars is None:
        corrupt_chars = ["敷", "攠", "餠"]
    if issues_list is None:
        issues_list = []
        
    btype = block.get("type")
    if not btype or btype not in block:
        return
        
    block_data = block[btype]
    
    # Support auditing native equation blocks
    if btype == "equation":
        expression = block_data.get("expression", "")
        has_garbled = any(c in expression for c in corrupt_chars)
        block_issues = []
        if has_garbled:
            block_issues.append("Garbled characters (敷/攠/餠)")
        status = "OK" if not block_issues else f"FAIL ({', '.join(block_issues)})"
        if block_issues:
            issues_list.append((block["id"], btype, block_issues))
        print(f"{'  ' * indent}- Block ID: {block['id']} ({btype}) [{status}]")
        print(f"{'  ' * (indent+1)}Content: $${expression}$$")
        if block.get("has_children", False):
            children = get_block_children(block["id"], headers)
            for child in children:
                verify_block_formulas(child, headers, indent + 1, corrupt_chars, issues_list)
        return

    if "rich_text" not in block_data:
        return
        
    rich_text_list = block_data.get("rich_text", [])
    text_content = ""
    has_unconverted_dollar = False
    has_garbled = False
    
    for rt in rich_text_list:
        if rt.get("type") == "text":
            content = rt.get("text", {}).get("content", "")
            text_content += content
            if "$" in content:
                has_unconverted_dollar = True
            if any(c in content for c in corrupt_chars):
                has_garbled = True
        elif rt.get("type") == "equation":
            text_content += f"${rt['equation']['expression']}$"
            
    block_issues = []
    if has_unconverted_dollar:
        block_issues.append("Unconverted dollar signs ($)")
    if has_garbled:
        block_issues.append("Garbled characters (敷/攠/餠)")
        
    status = "OK" if not block_issues else f"FAIL ({', '.join(block_issues)})"
    if block_issues:
        issues_list.append((block["id"], btype, block_issues))
        
    # Attempt to print content cleanly with terminal fallback
    try:
        display_text = text_content
    except Exception:
        display_text = text_content.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
        
    print(f"{'  ' * indent}- Block ID: {block['id']} ({btype}) [{status}]")
    if display_text:
        print(f"{'  ' * (indent+1)}Content: {display_text}")
        
    if block.get("has_children", False):
        children = get_block_children(block["id"], headers)
        for child in children:
            verify_block_formulas(child, headers, indent + 1, corrupt_chars, issues_list)

# ==============================================================================
# Search Helpers
# ==============================================================================
def find_heading_block(blocks, heading_name, headers):
    """
    Recursively searches a list of blocks for a heading matching target name.
    Returns: (matched_block, subsequent_sibling_blocks)
    """
    for i, block in enumerate(blocks):
        btype = block.get("type", "")
        if btype in ("heading_1", "heading_2", "heading_3"):
            text = get_block_text(block).strip()
            # Exact match
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
        print("Error: Please replace NOTION_TOKEN with your actual Notion Integration Token inside the script.", file=sys.stderr)
        sys.exit(1)
        
    action = "convert"
    page_id = None
    heading_name = "ALL"
    
    # Check arguments
    if len(sys.argv) >= 2:
        arg1 = sys.argv[1].lower()
        if arg1 in ("convert", "verify"):
            action = arg1
            if len(sys.argv) >= 3:
                page_id = sys.argv[2]
            if len(sys.argv) >= 4:
                heading_name = sys.argv[3]
        else:
            page_id = sys.argv[1]
            if len(sys.argv) >= 3:
                heading_name = sys.argv[2]
            if len(sys.argv) >= 4:
                action = sys.argv[3].lower()
                
    # If not provided, prompt interactively
    if not page_id:
        page_id = input("Enter Notion Page ID (e.g., 1f4a89196df181648e97c2c84c024b74): ").strip()
        heading_name = input("Enter Target Heading Name (Press Enter or type 'ALL' to convert the entire page): ").strip()
        action_input = input("Enter Action (convert/verify, default is convert): ").strip().lower()
        if action_input in ("convert", "verify"):
            action = action_input
            
    if not page_id:
        print("Error: Page ID is required.", file=sys.stderr)
        sys.exit(1)
        
    if not heading_name:
        heading_name = "ALL"
        
    if action not in ("convert", "verify"):
        action = "convert"
        
    # Strip hyphens and whitespace from page ID
    page_id = page_id.replace("-", "").strip()
    headers = get_headers(NOTION_TOKEN)
    
    print(f"Action: {action.upper()}")
    print(f"Fetching children blocks of page {page_id}...")
    page_blocks = get_block_children(page_id, headers)
    if not page_blocks:
        print("No blocks found or failed to access page. Check permissions/token.", file=sys.stderr)
        sys.exit(1)
        
    is_convert_all = (heading_name.upper() == "ALL")
    
    if is_convert_all:
        print("Target: Entire page (heading set to ALL)...")
        blocks_to_process = page_blocks
    else:
        print(f"Searching for heading block named: '{heading_name}'...")
        search_result = find_heading_block(page_blocks, heading_name, headers)
        if not search_result:
            print(f"Heading block '{heading_name}' not found.", file=sys.stderr)
            sys.exit(1)
            
        target_block, subsequent_siblings = search_result
        target_type = target_block["type"]
        target_level = get_heading_level(target_type)
        
        print(f"Found heading '{heading_name}' (ID: {target_block['id']}, Level: {target_level})")
        
        blocks_to_process = []
        if target_block.get("has_children", False):
            heading_children = get_block_children(target_block["id"], headers)
            blocks_to_process.extend(heading_children)
            
        for sibling in subsequent_siblings:
            sib_type = sibling.get("type", "")
            sib_level = get_heading_level(sib_type)
            if sib_level is not None and sib_level <= target_level:
                break
            blocks_to_process.append(sibling)
        
    print(f"Collected {len(blocks_to_process)} direct blocks to process.")
    
    if action == "convert":
        print("Beginning formula conversion to native Notion LaTeX objects...")
        for block in blocks_to_process:
            process_block_tree(block, headers)
        print("Formula conversion completed successfully!")
    elif action == "verify":
        print("Starting double-confirmation and verification of blocks:")
        issues_list = []
        for block in blocks_to_process:
            verify_block_formulas(block, headers, indent=0, issues_list=issues_list)
            
        print("\n=== Verification Summary ===")
        if not issues_list:
            print("100% CLEAN! No unconverted formulas or garbled characters detected.")
        else:
            print(f"FAILED! Found {len(issues_list)} issues:")
            for bid, btype, issues in issues_list:
                print(f"  - Block {bid} ({btype}): {', '.join(issues)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
