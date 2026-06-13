---
name: notion-latex-converter
description: >-
  Converts inline plain-text formulas ($xx$ and $$xx$$) on a Notion page to native LaTeX equation objects under a specified heading or across the entire page, and provides verification functions to audit pages for encoding corruptions.
---

# Notion LaTeX Converter & Auditor

## Overview
This skill automates the conversion of plain-text LaTeX formulas (formatted with `$` or `$$` delimiters) in Notion blocks (paragraphs, lists, blockquotes, callouts, and quote blocks) into Notion's native LaTeX equation objects. 

It also includes a built-in auditor tool to double-check and verify that the page content under the heading is completely clean, free from garbled text corruptions (such as `敷`, `攠`, `餠`), and that all formula blocks have been successfully converted.

## Dependencies
- `requests` python library

## Quick Start

### 1. Formula Conversion
To convert formulas under a specific heading:
```bash
python latex_converter.py convert <page_id> <heading_name>
```

To convert formulas across the entire page:
```bash
python latex_converter.py convert <page_id> ALL
```

### 2. Double-Confirmation & Verification
To audit a section and verify there are no unconverted formulas or garbled character corruptions:
```bash
python latex_converter.py verify <page_id> <heading_name>
```

To audit the entire page:
```bash
python latex_converter.py verify <page_id> ALL
```

## Utility Scripts
The conversion and verification are powered by `latex_converter.py`.
- **Arguments**:
  - `action` (Optional): Either `convert` (default) or `verify`.
  - `page_id` (Required): The ID of the Notion page to process.
  - `heading_name` (Optional): The exact name of the heading under which to convert/verify formulas. If set to `ALL` or omitted, the entire page is processed.

## Rate Limiting
The script implements exponential backoff with random jitter to respect Notion API rate limits (HTTP 429) and handle transient server errors (HTTP 5xx), retrying up to 5 times.

## Common Mistakes
1. **Unshared Page**: The target page is not shared with the Notion Integration. In Notion, go to the page, click the "..." menu, and add your integration under "Connections".
2. **Missing Token**: Forgetting to configure the `NOTION_TOKEN` inside the script.
