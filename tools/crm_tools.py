"""CRM & Lead Management tools for Jarvis - track leads, manage pipeline, record follow-ups."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CRM_FILE = DATA_DIR / "crm_leads.json"


def _ensure_crm_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CRM_FILE.exists():
        CRM_FILE.write_text("[]", encoding="utf-8")


def _load_leads() -> List[Dict[str, Any]]:
    _ensure_crm_file()
    try:
        return json.loads(CRM_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_leads(leads: List[Dict[str, Any]]):
    _ensure_crm_file()
    CRM_FILE.write_text(json.dumps(leads, indent=2), encoding="utf-8")


@register_tool({
    "name": "crm_add_lead",
    "description": "Add a new customer lead or prospective client to the CRM pipeline.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Lead contact full name."},
            "company": {"type": "string", "description": "Company or organization name."},
            "email": {"type": "string", "description": "Contact email address."},
            "phone": {"type": "string", "description": "Contact phone number (optional)."},
            "status": {
                "type": "string",
                "description": "Pipeline status: new, contacted, qualified, proposal, won, lost.",
                "enum": ["new", "contacted", "qualified", "proposal", "won", "lost"],
            },
            "notes": {"type": "string", "description": "Context, notes, or next action items."},
        },
        "required": ["name", "company"],
    },
})
def crm_add_lead(
    name: str,
    company: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    status: str = "new",
    notes: str = "",
) -> Dict[str, Any]:
    """Add a new lead to the CRM."""
    leads = _load_leads()
    lead_id = f"lead_{uuid.uuid4().hex[:6]}"
    now = datetime.now().isoformat()

    lead = {
        "id": lead_id,
        "name": name.strip(),
        "company": company.strip(),
        "email": (email or "").strip(),
        "phone": (phone or "").strip(),
        "status": status.lower(),
        "notes": notes.strip(),
        "created_at": now,
        "updated_at": now,
    }

    leads.append(lead)
    _save_leads(leads)

    return {"success": True, "lead": lead, "message": f"Lead '{name}' added to CRM pipeline."}


@register_tool({
    "name": "crm_list_leads",
    "description": "List CRM leads filtered by status (new, contacted, qualified, proposal, won, lost) or keyword.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter by lead status."},
            "query": {"type": "string", "description": "Search keyword matching name or company."},
        },
        "required": [],
    },
})
def crm_list_leads(status: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """List and filter leads."""
    leads = _load_leads()
    filtered = []

    for lead in leads:
        if status and lead.get("status", "").lower() != status.lower():
            continue
        if query:
            q = query.lower()
            name = lead.get("name", "").lower()
            comp = lead.get("company", "").lower()
            notes = lead.get("notes", "").lower()
            if q not in name and q not in comp and q not in notes:
                continue
        filtered.append(lead)

    return {"success": True, "count": len(filtered), "leads": filtered}


@register_tool({
    "name": "crm_update_lead",
    "description": "Update an existing lead's status, notes, or contact info.",
    "input_schema": {
        "type": "object",
        "properties": {
            "lead_id": {"type": "string", "description": "ID of the lead to update."},
            "status": {"type": "string", "description": "New pipeline status."},
            "notes": {"type": "string", "description": "Additional notes or updates."},
        },
        "required": ["lead_id"],
    },
})
def crm_update_lead(
    lead_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Update lead details."""
    leads = _load_leads()
    found = False

    for lead in leads:
        if lead["id"] == lead_id:
            if status:
                lead["status"] = status.lower()
            if notes:
                existing = lead.get("notes", "")
                lead["notes"] = f"{existing}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}".strip()
            lead["updated_at"] = datetime.now().isoformat()
            found = True
            _save_leads(leads)
            return {"success": True, "lead": lead, "message": f"Lead {lead_id} updated."}

    return {"success": False, "error": f"Lead '{lead_id}' not found."}


@register_tool({
    "name": "crm_get_pipeline_summary",
    "description": "Get an aggregated summary of the sales/leads pipeline by status.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def crm_get_pipeline_summary() -> Dict[str, Any]:
    """Summarize the entire sales pipeline."""
    leads = _load_leads()
    breakdown = {"new": 0, "contacted": 0, "qualified": 0, "proposal": 0, "won": 0, "lost": 0}

    for lead in leads:
        st = lead.get("status", "new").lower()
        if st in breakdown:
            breakdown[st] += 1
        else:
            breakdown[st] = 1

    return {
        "success": True,
        "total_leads": len(leads),
        "pipeline": breakdown,
    }

