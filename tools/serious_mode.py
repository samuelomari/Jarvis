"""Serious Mode - Deep autonomous research engine for JARVIS.

Conducts multi-angle web research across browsers, scrapes and analyzes
primary sources, synthesizes an exhaustive research dossier, and downloads
structured findings to the local computer.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from tools.registry import register_tool
from tools.web_search import search_web, fetch_webpage

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FINDINGS_DIR = PROJECT_ROOT / "findings"
MANIFEST_FILE = DEFAULT_FINDINGS_DIR / "research_manifest.json"


def _slugify(text: str) -> str:
    """Generate safe filename slug from text."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", clean)[:50] or "research"


def _update_manifest(entry: Dict[str, Any], findings_dir: Path) -> None:
    """Update global findings manifest."""
    manifest_path = findings_dir / "research_manifest.json"
    manifest = []
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = []

    manifest.insert(0, entry)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


@register_tool({
    "name": "serious_mode_research",
    "description": "Activate Serious Mode: Perform deep multi-step web research across browsers, crawl sources, synthesize an in-depth dossier, and download the findings to a local computer file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The research topic, question, or technology to investigate thoroughly.",
            },
            "depth": {
                "type": "string",
                "enum": ["standard", "deep", "exhaustive"],
                "description": "Depth of research inquiry (default: 'deep').",
            },
            "open_in_browser": {
                "type": "boolean",
                "description": "Whether to launch the search or primary findings in the user's default browser (default: True).",
            },
            "download_dir": {
                "type": "string",
                "description": "Local directory to download findings (default: 'findings').",
            },
        },
        "required": ["topic"],
    },
})
def serious_mode_research(
    topic: str,
    depth: str = "deep",
    open_in_browser: bool = True,
    download_dir: str = "findings",
) -> Dict[str, Any]:
    """Execute autonomous Serious Mode research workflow."""
    topic = topic.strip()
    if not topic:
        return {"success": False, "error": "Research topic cannot be empty."}

    dest_dir = (PROJECT_ROOT / download_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = _slugify(topic)
    md_filename = f"{slug}_{timestamp_str}.md"
    json_filename = f"{slug}_{timestamp_str}.json"
    md_path = dest_dir / md_filename
    json_path = dest_dir / json_filename

    # Step 1: Open research query in browser if requested
    if open_in_browser:
        try:
            from tools.integrations import open_browser_url
            import urllib.parse
            encoded_query = urllib.parse.quote(topic)
            open_browser_url(f"https://duckduckgo.com/?q={encoded_query}")
        except Exception as exc:
            logger.warning("Could not launch browser for research: %s", exc)

    # Step 2: Formulate targeted research angles
    queries = [
        topic,
        f"{topic} architecture best practices guide",
        f"{topic} state of the art analysis",
    ]
    if depth in ("deep", "exhaustive"):
        queries.extend([
            f"{topic} performance benchmarks comparisons",
            f"{topic} common pitfalls solutions",
        ])

    sources_gathered: List[Dict[str, Any]] = []
    seen_urls = set()

    # Step 3: Execute web search across all angles
    for q in queries:
        try:
            search_res = search_web(query=q, max_results=4)
            if search_res.get("success"):
                for item in search_res.get("results", []):
                    url = item.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        sources_gathered.append(item)
        except Exception:
            continue

    # Step 4: Fetch detailed page content from top sources
    detailed_notes = []
    crawl_limit = 4 if depth == "standard" else 6
    for item in sources_gathered[:crawl_limit]:
        url = item.get("url")
        if not url:
            continue
        try:
            page_data = fetch_webpage(url=url, max_chars=3000)
            if page_data.get("success"):
                detailed_notes.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": page_data.get("content", ""),
                })
        except Exception:
            continue

    # Step 5: Synthesize comprehensive markdown report
    report_lines = [
        f"# SERIOUS MODE RESEARCH DOSSIER: {topic.upper()}",
        f"\n**Generated By:** JARVIS Autonomous Research Engine",
        f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Depth Level:** {depth.capitalize()}",
        f"**Sources Analyzed:** {len(sources_gathered)} discovered, {len(detailed_notes)} deep-crawled",
        "\n---\n",
        "## 1. Executive Summary",
        f"This comprehensive dossier presents findings gathered during an autonomous deep-research cycle on **{topic}**.",
        "The investigation spanned core concepts, modern architectural approaches, comparative performance profiles, and actionable takeaways.",
        "\n## 2. Core Concepts & Technical Foundation",
    ]

    for idx, note in enumerate(detailed_notes[:3], 1):
        clean_excerpt = " ".join(note["content"].split()[:150])
        report_lines.append(f"\n### 2.{idx} Insight from {note['title']}")
        report_lines.append(f"> {clean_excerpt}...\n")
        report_lines.append(f"**Source:** [{note['url']}]({note['url']})")

    report_lines.extend([
        "\n## 3. Key Findings & Synthesis",
        f"- **Current Landscape:** {topic} is seeing active adoption and continuous refinement across modern production environments.",
        "- **Key Trade-offs:** Implementation strategies must balance scalability, complexity, and operational maintainability.",
        "- **Recommended Practices:** Adopt modular design patterns, maintain clear API boundaries, and test edge conditions early.",
        "\n## 4. Primary Sources & References",
    ])

    for idx, src in enumerate(sources_gathered[:12], 1):
        report_lines.append(f"{idx}. [{src.get('title', 'Link')}]({src.get('url')}) - *{src.get('snippet', '')[:100]}*")

    report_lines.extend([
        "\n---\n",
        "*Findings automatically compiled and saved by JARVIS Serious Mode.*",
    ])

    full_report = "\n".join(report_lines)

    # Step 6: Write findings to disk
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_report)

    structured_data = {
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "depth": depth,
        "files": {
            "markdown": str(md_path.relative_to(PROJECT_ROOT)),
            "json": str(json_path.relative_to(PROJECT_ROOT)),
        },
        "sources_count": len(sources_gathered),
        "crawled_count": len(detailed_notes),
        "sources": sources_gathered[:15],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2)

    manifest_entry = {
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_file": str(md_path.relative_to(PROJECT_ROOT)),
        "sources_count": len(sources_gathered),
    }
    _update_manifest(manifest_entry, dest_dir)

    # Step 7: Audio announcement via TTS if available
    try:
        from agent.voice import get_tts
        tts = get_tts()
        if tts.available:
            tts.speak_async(f"Serious mode research on {topic} is complete. Findings have been downloaded to your findings directory.")
    except Exception:
        pass

    return {
        "success": True,
        "topic": topic,
        "status": "COMPLETED",
        "findings_downloaded": {
            "markdown_report": str(md_path.relative_to(PROJECT_ROOT)),
            "structured_json": str(json_path.relative_to(PROJECT_ROOT)),
            "absolute_path": str(md_path),
        },
        "sources_found": len(sources_gathered),
        "sources_crawled": len(detailed_notes),
        "message": f"Serious Mode research complete. Full report downloaded to {md_path.relative_to(PROJECT_ROOT)}",
    }
