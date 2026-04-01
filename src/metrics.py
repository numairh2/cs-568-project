"""Event logging for user study and interaction tracking."""

import json
import time
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
STUDY_LOG = DATA_DIR / "study_data.jsonl"


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def generate_participant_id():
    """Generate a short unique participant ID."""
    return uuid.uuid4().hex[:8]


def track_event(participant_id, event_type, data=None):
    """Append a single event to the study log file.

    Args:
        participant_id: Unique ID for this participant/session.
        event_type: One of: condition_assigned, clause_viewed,
                    explanation_requested, explanation_rated,
                    comprehension_answer, likert_response,
                    feedback_submitted, study_completed.
        data: Dict of event-specific payload.
    """
    _ensure_data_dir()
    event = {
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "participant_id": participant_id,
        "event_type": event_type,
        "data": data or {},
    }
    with open(STUDY_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")


def load_events():
    """Load all logged events. Returns a list of dicts."""
    if not STUDY_LOG.exists():
        return []
    events = []
    with open(STUDY_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def load_events_by_type(event_type):
    """Load events filtered by type."""
    return [e for e in load_events() if e["event_type"] == event_type]


def get_participant_events(participant_id):
    """Load all events for a specific participant."""
    return [e for e in load_events() if e["participant_id"] == participant_id]
