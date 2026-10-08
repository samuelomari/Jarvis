"""Google Gemini API client for Jarvis agent reasoning, tool execution, and vision."""

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger("jarvis.gemini")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiTextBlock:
    """Represents a text response block from Gemini."""

    def __init__(self, text: str):
        self.type = "text"
        self.text = text

    def __repr__(self) -> str:
        return f"<GeminiTextBlock text={self.text[:40]!r}>"


class GeminiToolBlock:
    """Represents a tool / function call requested by Gemini."""

    def __init__(self, name: str, tool_input: Dict[str, Any], call_id: Optional[str] = None):
        self.type = "tool_use"
        self.name = name
        self.input = tool_input or {}
        self.id = call_id or f"gemini_call_{name}_{abs(hash(str(tool_input))) % 100000}"

    def __repr__(self) -> str:
        return f"<GeminiToolBlock name={self.name} input={self.input}>"


class GeminiResponse:
    """Standardized response from Gemini matching Jarvis's agent interface."""

    def __init__(
        self,
        content: List[Union[GeminiTextBlock, GeminiToolBlock]],
        stop_reason: str = "end_turn",
        raw_response: Optional[Dict[str, Any]] = None,
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.raw = raw_response or {}

    @property
    def text(self) -> str:
        """Extract full plain text from all text blocks."""
        texts = [b.text for b in self.content if isinstance(b, GeminiTextBlock) or getattr(b, "type", "") == "text"]
        return "\n\n".join(texts)

    def __repr__(self) -> str:
        return f"<GeminiResponse stop_reason={self.stop_reason} blocks={len(self.content)}>"


class GeminiClient:
    """Client for Google Gemini foundational models using the Gemini REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "gemini-2.5-flash",
        timeout: float = 60.0,
    ):
        self.api_key = api_key or ""
        self.default_model = default_model
        self.timeout = timeout
        self.client = httpx.Client(timeout=self.timeout)

    @property
    def messages(self):
        """Compatibility property matching Anthropic/Mock client signature."""
        return self

    def _convert_tool_schemas(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert standard tool schemas to Gemini function_declarations format."""
        function_declarations = []
        for tool in tools:
            name = tool.get("name")
            description = tool.get("description", "")
            # Schema might be under input_schema or parameters
            schema = tool.get("input_schema") or tool.get("parameters") or {"type": "object", "properties": {}}

            # Clean schema for Gemini parameters specification
            param_spec = self._clean_schema_for_gemini(schema)

            decl = {
                "name": name,
                "description": description,
                "parameters": param_spec,
            }
            function_declarations.append(decl)

        return [{"function_declarations": function_declarations}] if function_declarations else []

    def _clean_schema_for_gemini(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure schema keys conform to Gemini OpenAPI subset."""
        if not isinstance(schema, dict):
            return {"type": "object", "properties": {}}

        clean: Dict[str, Any] = {}
        for k, v in schema.items():
            if k == "type":
                clean["type"] = str(v).lower()
            elif k == "properties" and isinstance(v, dict):
                clean["properties"] = {
                    prop_name: self._clean_schema_for_gemini(prop_val)
                    for prop_name, prop_val in v.items()
                }
            elif k == "items" and isinstance(v, dict):
                clean["items"] = self._clean_schema_for_gemini(v)
            elif k in ("required", "description", "enum"):
                clean[k] = v

        if "type" not in clean:
            clean["type"] = "object"
        return clean

    def _convert_messages_to_gemini(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert Jarvis conversation history into Gemini contents format."""
        gemini_contents = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            # Map assistant role to Gemini 'model'
            gemini_role = "model" if role == "assistant" else "user"
            parts = []

            if isinstance(content, str):
                parts.append({"text": content})
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, str):
                        parts.append({"text": item})
                    elif isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type == "text":
                            parts.append({"text": item.get("text", "")})
                        elif item_type == "tool_use":
                            parts.append({
                                "functionCall": {
                                    "name": item.get("name"),
                                    "args": item.get("input", {}),
                                }
                            })
                        elif item_type == "tool_result":
                            raw_out = item.get("content", "")
                            # Parse output if valid JSON dict
                            resp_payload: Dict[str, Any] = {}
                            if isinstance(raw_out, dict):
                                resp_payload = raw_out
                            elif isinstance(raw_out, str):
                                try:
                                    resp_payload = json.loads(raw_out)
                                    if not isinstance(resp_payload, dict):
                                        resp_payload = {"output": raw_out}
                                except Exception:
                                    resp_payload = {"output": raw_out}
                            else:
                                resp_payload = {"output": str(raw_out)}

                            parts.append({
                                "functionResponse": {
                                    "name": item.get("tool_name") or item.get("tool_use_id", "tool"),
                                    "response": resp_payload,
                                }
                            })
                    elif hasattr(item, "text"):
                        parts.append({"text": item.text})
                    elif hasattr(item, "type") and item.type == "tool_use":
                        parts.append({
                            "functionCall": {
                                "name": item.name,
                                "args": item.input,
                            }
                        })

            if parts:
                gemini_contents.append({
                    "role": gemini_role,
                    "parts": parts,
                })

        return gemini_contents

    def create(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> GeminiResponse:
        """Execute a generateContent call against Gemini API."""
        target_model = model or self.default_model
        # Strip any prefix like 'models/' if provided
        if target_model.startswith("models/"):
            target_model = target_model[len("models/"):]

        url = f"{GEMINI_API_BASE}/models/{target_model}:generateContent"
        params = {"key": self.api_key}

        payload: Dict[str, Any] = {
            "contents": self._convert_messages_to_gemini(messages or []),
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}]
            }

        if tools:
            converted_tools = self._convert_tool_schemas(tools)
            if converted_tools:
                payload["tools"] = converted_tools

        try:
            response = self.client.post(
                url,
                params=params,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to communicate with Google Gemini API: {str(exc)}") from exc

        if response.status_code != 200:
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            error_msg = error_data.get("error", {}).get("message") or response.text
            raise RuntimeError(f"Google Gemini API Error ({response.status_code}): {error_msg}")

        result_json = response.json()
        return self._parse_gemini_response(result_json)

    def _parse_gemini_response(self, data: Dict[str, Any]) -> GeminiResponse:
        """Parse Gemini generateContent JSON response into GeminiResponse."""
        candidates = data.get("candidates", [])
        if not candidates:
            return GeminiResponse(
                content=[GeminiTextBlock("No response generated by Gemini.")],
                stop_reason="end_turn",
                raw_response=data,
            )

        candidate = candidates[0]
        content_obj = candidate.get("content", {})
        parts = content_obj.get("parts", [])

        blocks: List[Union[GeminiTextBlock, GeminiToolBlock]] = []
        has_tool_call = False

        for part in parts:
            if "text" in part:
                blocks.append(GeminiTextBlock(part["text"]))
            elif "functionCall" in part:
                has_tool_call = True
                fn = part["functionCall"]
                blocks.append(GeminiToolBlock(name=fn.get("name", ""), tool_input=fn.get("args", {})))

        stop_reason = "tool_use" if has_tool_call else "end_turn"
        return GeminiResponse(content=blocks, stop_reason=stop_reason, raw_response=data)

    def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: str = "Analyze this image in detail.",
        model: Optional[str] = None,
    ) -> str:
        """Multimodal image analysis using Gemini Vision."""
        target_model = model or self.default_model
        if target_model.startswith("models/"):
            target_model = target_model[len("models/"):]

        url = f"{GEMINI_API_BASE}/models/{target_model}:generateContent"
        params = {"key": self.api_key}

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 0.2,
            },
        }

        try:
            response = self.client.post(
                url,
                params=params,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if response.status_code != 200:
                return f"Gemini Vision API Error ({response.status_code}): {response.text}"
            res_data = response.json()
            parsed = self._parse_gemini_response(res_data)
            return parsed.text
        except Exception as exc:
            return f"Gemini Vision Error: {str(exc)}"

