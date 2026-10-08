"""Vision tools for analyzing screenshots and images using Google Gemini Vision."""

import base64
from pathlib import Path
from typing import Any, Dict, Optional

from tools.registry import register_tool


def _encode_image_base64(image_path: str) -> Optional[str]:
    """Read an image file and return its base64-encoded string."""
    try:
        path = Path(image_path).expanduser().resolve()
        if not path.is_file():
            return None
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception:
        return None


@register_tool({
    "name": "analyze_screenshot",
    "description": "Capture the current screen or take a specified image and analyze it using Gemini vision AI.",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "What to look for or analyze in the screenshot (e.g. 'What error is shown?', 'Describe what is on screen').",
            },
            "image_path": {
                "type": "string",
                "description": "Optional path to an existing image file. If omitted, takes a fresh screenshot.",
            },
        },
        "required": ["question"],
    },
})
def analyze_screenshot(question: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a screenshot using Google Gemini vision."""
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

    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        return {"success": False, "error": f"Could not find image at '{image_path}'."}

    path_lower = str(image_path).lower()
    media_type = "image/jpeg" if path_lower.endswith((".jpg", ".jpeg")) else "image/png"

    from config import GEMINI_API_KEY, ANTHROPIC_API_KEY, MODEL

    # 1. Primary: Google Gemini Vision
    if GEMINI_API_KEY:
        try:
            from agent.gemini_client import GeminiClient
            client = GeminiClient(api_key=GEMINI_API_KEY, default_model=MODEL)
            image_bytes = path.read_bytes()
            analysis_text = client.analyze_image(
                image_bytes=image_bytes,
                mime_type=media_type,
                prompt=question,
            )
            return {
                "success": True,
                "provider": "gemini",
                "question": question,
                "analysis": analysis_text,
                "image_path": str(image_path),
            }
        except Exception as exc:
            return {"success": False, "error": f"Gemini Vision error: {str(exc)}"}

    # 2. Fallback: Anthropic Claude Vision
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            encoded = _encode_image_base64(str(image_path))
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
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
                            {"type": "text", "text": question},
                        ],
                    }
                ],
            )
            analysis = "".join(b.text for b in response.content if hasattr(b, "text"))
            return {
                "success": True,
                "provider": "anthropic",
                "question": question,
                "analysis": analysis,
                "image_path": str(image_path),
            }
        except Exception as exc:
            return {"success": False, "error": f"Anthropic Vision error: {str(exc)}"}

    return {
        "success": False,
        "error": "Vision analysis requires an AI API key. Configure GEMINI_API_KEY in your .env file.",
    }


@register_tool({
    "name": "analyze_image_file",
    "description": "Analyze any image file (screenshot, diagram, error message, document) using Gemini vision.",
    "input_schema": {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image file to analyze.",
            },
            "prompt": {
                "type": "string",
                "description": "Instructions or questions about the image (defaults to 'Describe this image in detail').",
            },
        },
        "required": ["image_path"],
    },
})
def analyze_image_file(image_path: str, prompt: str = "Describe this image in detail.") -> Dict[str, Any]:
    """Analyze an image file using Gemini vision."""
    return analyze_screenshot(question=prompt, image_path=image_path)
