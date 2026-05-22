"""
Curated ElevenLabs voice catalog with gender + accent metadata.

This catalog is hand-synced to the voices actually present in the user's
ElevenLabs account (queried via /v1/voices). To add Indian, Asian, or other
accents: open ElevenLabs → Voice Library → search → Add, then re-sync this
file (you can re-run a /v1/voices fetch to get the new IDs).
"""

# Each voice: id, display_name, gender ("male"|"female"), accent, blurb
VOICE_CATALOG: list[dict] = [
    # ── British ─────────────────────────────────────────────────
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel",   "gender": "male",   "accent": "British",    "blurb": "Steady broadcaster"},
    {"id": "JBFqnCBsd6RMkjVDRZzb", "name": "George",   "gender": "male",   "accent": "British",    "blurb": "Warm, captivating"},
    {"id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice",    "gender": "female", "accent": "British",    "blurb": "Clear, engaging"},
    {"id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily",     "gender": "female", "accent": "British",    "blurb": "Velvety actress"},

    # ── American (male) ─────────────────────────────────────────
    {"id": "nPczCjzI2devNBz1zQrb", "name": "Brian",    "gender": "male",   "accent": "American",   "blurb": "Deep, resonant"},
    {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric",     "gender": "male",   "accent": "American",   "blurb": "Smooth, trustworthy"},
    {"id": "iP95p4xoKVk53GoZ742B", "name": "Chris",    "gender": "male",   "accent": "American",   "blurb": "Charming, down-to-earth"},
    {"id": "CwhRBWXzGAHq8TQ4Fs17", "name": "Roger",    "gender": "male",   "accent": "American",   "blurb": "Laid-back, casual"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam",     "gender": "male",   "accent": "American",   "blurb": "Dominant, firm"},
    {"id": "pqHfZKP75CvOlQylNhV4", "name": "Bill",     "gender": "male",   "accent": "American",   "blurb": "Wise, mature, balanced"},
    {"id": "bIHbv24MWmeRgasZH58o", "name": "Will",     "gender": "male",   "accent": "American",   "blurb": "Relaxed optimist"},
    {"id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam",     "gender": "male",   "accent": "American",   "blurb": "Energetic, social"},
    {"id": "SOYHLrjzK2X1ezoPC6cr", "name": "Harry",    "gender": "male",   "accent": "American",   "blurb": "Fierce warrior"},
    {"id": "N2lVS1w4EtoT3dr4eOWO", "name": "Callum",   "gender": "male",   "accent": "American",   "blurb": "Husky trickster"},

    # ── American (female) ───────────────────────────────────────
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah",    "gender": "female", "accent": "American",   "blurb": "Mature, reassuring"},
    {"id": "FGY2WhTYpPnrIDTdsKH5", "name": "Laura",    "gender": "female", "accent": "American",   "blurb": "Enthusiast, quirky"},
    {"id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica",  "gender": "female", "accent": "American",   "blurb": "Playful, bright"},
    {"id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda",  "gender": "female", "accent": "American",   "blurb": "Knowledgable"},
    {"id": "hpp4J3VqNfWAUOO0d1Us", "name": "Bella",    "gender": "female", "accent": "American",   "blurb": "Professional, bright"},

    # ── Australian ──────────────────────────────────────────────
    {"id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie",  "gender": "male",   "accent": "Australian", "blurb": "Deep, confident"},
]

DEFAULT_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel — British male


def find_voice(voice_id: str | None) -> dict | None:
    if not voice_id:
        return None
    return next((v for v in VOICE_CATALOG if v["id"] == voice_id), None)


def list_accents() -> list[str]:
    """Distinct accents, in catalog order."""
    seen = []
    for v in VOICE_CATALOG:
        if v["accent"] not in seen:
            seen.append(v["accent"])
    return seen
