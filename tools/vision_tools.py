"""Vision tools - screenshot analysis using Claude vision API."""

import base64
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _encode_image_base64(image_path: str) -> Optional[str]:
    """Encode an image file to base64."""
    try:
        path = Path(image_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / image_path
        if not path.exists():
            return None
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


@register_tool({
    "name": "analyze_screenshot",
    "description": "Take a screenshot and analyze it using Claude vision to describe what is on screen, identify errors, or answer questions about the UI.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "What to analyze or ask about the screen (e.g. 'What errors are visible?', 'Describe the UI', 'What application is open?').",
            },
            "image_path": {
                "type": "string",
                "description": "Optional path to an existing image file. If not provided, a new screenshot is taken.",
            },
        },
        "required": ["question"],
    },
})
def analyze_screenshot(question: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a screenshot using Claude vision."""
    # Take screenshot if no image provided
    if not image_path:
        from tools.computer_control import take_screenshot
        shot_result = take_screenshot("vision_analysis.png")
        if not shot_result.get("success"):
            return {
                "success": False,
                "error": f"Could not take screenshot: {shot_result.get('error')}. Provide an image_path instead.",
            }
        image_path = shot_result["absolute_path"]

    # Encode image
    encoded = _encode_image_base64(image_path)
    if not encoded:
        return {"success": False, "error": f"Could not read image at '{image_path}'."}

    # Determine media type
    path_lower = str(image_path).lower()
    media_type = "image/jpeg" if path_lower.endswith((".jpg", ".jpeg")) else "image/png"

    # Call Claude vision
    try:
        from config import ANTHROPIC_API_KEY, MODEL
        import anthropic

        if not ANTHROPIC_API_KEY:
            return {
                "success": False,
                "error": "Vision analysis requires a real Anthropic API key (ANTHROPIC_API_KEY not set).",
            }

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                        {
                            "type": "text",
                            "text": question,
                        },
                    ],
                }
            ],
        )

        analysis = ""
        for block in response.content:
            if hasattr(block, "text"):
                analysis += block.text

        return {
            "success": True,
            "question": question,
            "analysis": analysis,
            "image_path": str(image_path),
        }

    except ImportError:
        return {"success": False, "error": "anthropic package not installed."}
    except Exception as exc:
        return {"success": False, "error": f"Vision analysis failed: {str(exc)}"}


@register_tool({
    "name": "analyze_image_file",
    "description": "Analyze any image file (screenshot, diagram, error message, document) using Claude vision.",
    "input_schema": {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image file to analyze.",
            },
            "question": {
                "type": "string",
                "description": "What to analyze or ask about the image.",
            },
        },
        "required": ["image_path", "question"],
    },
})
def analyze_image_file(image_path: str, question: str) -> Dict[str, Any]:
    """Analyze an image file using Claude vision."""
    return analyze_screenshot(question=question, image_path=image_path)
