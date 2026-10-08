"""Unit tests for Gemini AI Brain and Hermes 10-Step Autonomous Agent capabilities."""

import json
from unittest.mock import MagicMock, patch
import pytest

from agent.gemini_client import GeminiClient, GeminiTextBlock, GeminiToolBlock, GeminiResponse
from agent.core import Jarvis
from agent.agents.orchestrator import get_orchestrator
from tools.crm_tools import crm_add_lead, crm_list_leads, crm_update_lead, crm_get_pipeline_summary
from tools.email_tools import send_email, draft_email, list_email_drafts
from tools.drive_tools import gdrive_list_files, gdrive_upload_file, gdrive_read_file
from tools.workflow_tools import create_workflow, list_workflows, execute_workflow
from notifications.telegram import send_telegram_message, TelegramBotRunner
from tools.telegram_tools import telegram_send, telegram_check_messages


def test_gemini_client_schema_and_message_conversion():
    """Test GeminiClient schema formatting and message payload preparation."""
    client = GeminiClient(api_key="test_key_gemini")

    tools = [
        {
            "name": "search_database",
            "description": "Searches records.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        }
    ]

    converted = client._convert_tool_schemas(tools)
    assert len(converted) == 1
    decls = converted[0]["function_declarations"]
    assert decls[0]["name"] == "search_database"
    assert "parameters" in decls[0]

    messages = [
        {"role": "user", "content": "Hello Jarvis"},
        {"role": "assistant", "content": "Greetings"},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_name": "search_database",
                    "content": '{"results": ["doc1"]}',
                }
            ],
        },
    ]

    gemini_contents = client._convert_messages_to_gemini(messages)
    assert len(gemini_contents) == 3
    assert gemini_contents[0]["role"] == "user"
    assert gemini_contents[1]["role"] == "model"
    assert "functionResponse" in gemini_contents[2]["parts"][0]


def test_gemini_client_mock_rest_response():
    """Test parsing of Gemini REST response."""
    client = GeminiClient(api_key="test_key")

    mock_json = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Here is the plan."},
                        {"functionCall": {"name": "get_current_time", "args": {}}},
                    ],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }

    parsed = client._parse_gemini_response(mock_json)
    assert parsed.stop_reason == "tool_use"
    assert len(parsed.content) == 2
    assert isinstance(parsed.content[0], GeminiTextBlock)
    assert isinstance(parsed.content[1], GeminiToolBlock)
    assert parsed.content[1].name == "get_current_time"


def test_jarvis_initialization_with_gemini(monkeypatch, tmp_path):
    """Test Jarvis selects GeminiClient when GEMINI_API_KEY is configured."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_key_123")
    monkeypatch.setenv("JARVIS_AI_PROVIDER", "gemini")
    monkeypatch.setenv("JARVIS_DEV_MODE", "false")

    with patch("agent.gemini_client.httpx.Client"):
        jarvis = Jarvis(workspace_root=tmp_path)
        assert isinstance(jarvis.client, GeminiClient)
        assert jarvis.client.api_key == "mock_gemini_key_123"


def test_crm_and_lead_management(tmp_path, monkeypatch):
    """Test Step 07 & 08 CRM tools: adding, listing, updating leads and pipeline stats."""
    test_crm_file = tmp_path / "test_leads.json"
    monkeypatch.setattr("tools.crm_tools.CRM_FILE", test_crm_file)

    add_res = crm_add_lead(
        name="Alice Smith",
        company="Acme Corp",
        email="alice@acme.com",
        status="new",
        notes="Interested in AI automation.",
    )
    assert add_res["success"] is True
    lead_id = add_res["lead"]["id"]

    list_res = crm_list_leads(status="new")
    assert list_res["success"] is True
    assert list_res["count"] == 1
    assert list_res["leads"][0]["name"] == "Alice Smith"

    update_res = crm_update_lead(lead_id, status="qualified", notes="Had initial call.")
    assert update_res["success"] is True
    assert update_res["lead"]["status"] == "qualified"

    summary_res = crm_get_pipeline_summary()
    assert summary_res["success"] is True
    assert summary_res["total_leads"] == 1
    assert summary_res["pipeline"]["qualified"] == 1


def test_email_and_draft_tools(tmp_path, monkeypatch):
    """Test Step 08 Email tools: drafting and queuing emails."""
    test_drafts_file = tmp_path / "test_drafts.json"
    monkeypatch.setattr("tools.email_tools.DRAFTS_FILE", test_drafts_file)

    draft_res = draft_email("test@example.com", "Meeting Follow-up", "Thanks for our call.")
    assert draft_res["success"] is True
    assert "draft_id" in draft_res

    send_res = send_email("test@example.com", "Proposal", "Attached proposal.")
    assert send_res["success"] is True

    drafts_list = list_email_drafts()
    assert drafts_list["success"] is True
    assert drafts_list["count"] >= 2


def test_drive_tools(tmp_path, monkeypatch):
    """Test Step 08 Google Drive / Cloud storage tools."""
    gdrive_dir = tmp_path / "gdrive"
    monkeypatch.setattr("tools.drive_tools.GDRIVE_DIR", gdrive_dir)

    src_file = tmp_path / "sample_doc.txt"
    src_file.write_text("Confidential business plan.", encoding="utf-8")

    upload_res = gdrive_upload_file(str(src_file), "plan.txt")
    assert upload_res["success"] is True

    list_res = gdrive_list_files()
    assert list_res["success"] is True
    assert list_res["count"] == 1
    assert list_res["files"][0]["name"] == "plan.txt"

    read_res = gdrive_read_file("plan.txt")
    assert read_res["success"] is True
    assert "Confidential business plan." in read_res["content"]


def test_workflow_skills_automation(tmp_path, monkeypatch):
    """Test Step 09 Reusable workflow and permanent skill automation."""
    test_wf_file = tmp_path / "test_workflows.json"
    monkeypatch.setattr("tools.workflow_tools.WORKFLOWS_FILE", test_wf_file)

    steps = [
        {"action": "tool", "target": "crm_get_pipeline_summary", "args": {}},
        {"action": "tool", "target": "list_email_drafts", "args": {}},
    ]

    create_res = create_workflow(
        name="daily_ops_check",
        description="Verify pipeline and drafts",
        steps=steps,
        trigger="daily:09:00",
    )
    assert create_res["success"] is True

    workflows = list_workflows()
    assert workflows["success"] is True
    assert any(w["name"] == "daily_ops_check" for w in workflows["workflows"])

    exec_res = execute_workflow("daily_ops_check")
    assert exec_res["success"] is True
    assert exec_res["steps_executed"] == 2


def test_telegram_bridge():
    """Test Step 06 Telegram bridge functions."""
    res = send_telegram_message("Test message")
    assert "success" in res

    runner = TelegramBotRunner()
    reply = runner._handle_incoming_text("/start")
    assert "Jarvis Telegram Bridge" in reply

    reply_status = runner._handle_incoming_text("/status")
    assert "Brain: Gemini" in reply_status

    reply_stop = runner._handle_incoming_text("/stop")
    assert "EMERGENCY STOP" in reply_stop


def test_business_and_competitor_agents_registered():
    """Test Step 07 specialized business & competitor agents in orchestrator."""
    orchestrator = get_orchestrator()
    business_agent = orchestrator.get_agent("business")
    competitor_agent = orchestrator.get_agent("competitor_tracker")

    assert business_agent is not None
    assert "Business & CRM Operations Lead" in business_agent.role
    assert "crm_add_lead" in business_agent.allowed_tools

    assert competitor_agent is not None
    assert "Market Intelligence & Competitor Analyst" in competitor_agent.role
    assert "search_web" in competitor_agent.allowed_tools

