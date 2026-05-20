"""Prompt templates for all LLM calls."""

EARTHQUAKE_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Event data (JSON):
{event_json}

Write a concise plain-language alert in 3-4 sentences for the general public in India.
Include: what happened, where, potential impact, and one safety action.
Use simple language. Do NOT speculate beyond the data provided."""

FLOOD_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Flood event data (JSON):
{event_json}

Write a concise plain-language flood alert in 3-4 sentences.
Include: basin/district affected, current gauge level vs warning level, expected trend, and one safety action."""

CYCLONE_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Cyclone bulletin data (JSON):
{event_json}

Write a concise plain-language cyclone alert in 3-4 sentences.
Include: cyclone name, current intensity, landfall estimate, and one safety action."""

WILDFIRE_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Wildfire cluster data (JSON):
{event_json}

Write a concise plain-language wildfire alert in 3-4 sentences.
Include: location, number of hotspots, wind direction context, and one safety action."""

LANDSLIDE_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Landslide risk data (JSON):
{event_json}

Write a concise plain-language landslide risk alert in 3-4 sentences.
Include: district, rainfall threshold status, terrain risk level, and one safety action."""

SOS_TRIAGE = """You are a disaster-response triage assistant for India.

Incoming SOS message:
\"\"\"{message}\"\"\"

Extracted location (may be empty): {location}

Rate the urgency 1-5 (5 = immediate life threat) and provide:
1. urgency_score: integer 1-5
2. category: one of [injury, trapped, missing, infrastructure, medical, resource_request, information, other]
3. summary: one sentence describing the situation
4. recommended_action: one sentence on what responders should do

Respond ONLY with valid JSON matching this schema:
{"urgency_score": int, "category": str, "summary": str, "recommended_action": str}"""

GENERIC_EXPLAIN = """You are Alertix AI, an Indian disaster-intelligence assistant.

Event data (JSON):
{event_json}

Write a concise plain-language alert in 3-4 sentences for the general public in India.
Do NOT speculate beyond the data provided."""

TEMPLATE_MAP = {
    "earthquake": EARTHQUAKE_EXPLAIN,
    "flood": FLOOD_EXPLAIN,
    "cyclone": CYCLONE_EXPLAIN,
    "wildfire": WILDFIRE_EXPLAIN,
    "landslide": LANDSLIDE_EXPLAIN,
    "sos": SOS_TRIAGE,
}


def get_template(hazard_type: str) -> str:
    return TEMPLATE_MAP.get(hazard_type.lower(), GENERIC_EXPLAIN)
