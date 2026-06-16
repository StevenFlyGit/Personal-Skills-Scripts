---
name: video-downloader
description: >-
  Extracts and downloads video streams from any given video page URL. Handles complex dynamic pages (like CSDN Live) by falling back to the browser agent for stream extraction when direct download tools fail.
---

# Video Downloader Skill

## Overview
This skill robustly downloads videos given a webpage URL and a target directory. It relies primarily on the `yt-dlp` CLI tool for fast, direct downloads. If `yt-dlp` cannot parse the video link (e.g. dynamic live streams or protected pages), this skill provides an intelligent fallback: it will invoke a browser subagent to navigate to the page, intercept network requests to extract the raw video stream (`.m3u8`, `.mp4`), and then download it.

## Dependencies
- **yt-dlp**: Required for downloading. The agent will install it globally if missing (`python -m pip install yt-dlp`).
- **browser subagent**: Used for intercepting network requests on unsupported URLs to find the direct stream.

## Quick Start
User prompt: `Use the video-downloader skill to download the video from https://live.csdn.net/room/csdnstudent/pbqwDa7C?spm=1001.2014.3001.5501 and save it to D:\Downloads`

## Workflow

### 1. Check Requirements
- Verify that the user has provided both the **URL containing the video** and the **Target Directory**.
- Run `python -m pip show yt-dlp` to verify installation. If missing, install it using `python -m pip install yt-dlp`.
- Ensure the target directory exists. If it does not, create it.

### 2. Initial Download Attempt
- Attempt to download the video directly using `yt-dlp` via terminal command:
  `yt-dlp -P "<Target Directory>" "<URL>"`
- **Success Criteria**: If the download finishes without errors, the task is complete. Proceed to Step 5.

### 3. Fallback: Browser Stream Extraction
- **Condition**: If `yt-dlp` returns an error such as "Unsupported URL" or fails to find the video stream.
- **Action**: Use the `invoke_subagent` tool to spawn a `browser` agent. 
- **Prompt to Browser Agent**: "Navigate to `<URL>`. Find the video player. Monitor the network requests or inspect the video element to extract the direct stream URL (typically ending in `.m3u8` or `.mp4`). Return the extracted direct URL to me. If no video is present, inform me."

### 4. Final Download
- Once the browser agent returns the raw `.m3u8` or `.mp4` stream URL, run `yt-dlp` again:
  `yt-dlp -P "<Target Directory>" "<Extracted Stream URL>"`

### 5. Robustness & Error Handling
- If the URL is invalid, or if the browser agent confirms that there is absolutely no video playing on the webpage (or it cannot extract a stream), **fail gracefully**.
- **Friendly Prompt**: Output a clear, friendly message to the user: "很抱歉，我无法从该链接中找到任何视频。这可能是因为链接错误，或者该视频受版权保护/使用了强化的防盗链技术，无法解析出视频流地址。"

## Common Mistakes
- Not handling paths with spaces: Always wrap paths and URLs in double quotes when running `yt-dlp`.
- Using `yt-dlp.exe` without checking if it's on PATH: Usually, `python -m yt_dlp` or standard `yt-dlp` works if installed globally.
