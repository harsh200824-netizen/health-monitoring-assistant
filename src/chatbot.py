from src.agent import agent_available, run_agent

METRIC_LABELS = {
    "blood_pressure": "Blood pressure",
    "blood_sugar": "Blood sugar",
    "weight": "Weight",
    "temperature": "Temperature",
    "heart_rate": "Heart rate",
}

STATUS_ICONS = {"taken": "✅", "due": "⏰", "missed": "⚠️", "upcoming": "🕒"}

HELP_TEXT = """Just talk to me normally. For example:

- *Remind me to take Metformin 500mg at 9am*
- *I took my Metformin*
- *BP was 150/95 and pulse 88 today*
- *What is due or missed right now?*
- *Show my weight history*

*This app is for tracking and reminders only. It is not medical advice.*"""


def handle_message(text, history=None):
    if not agent_available():
        return "⚠️ The AI agent is not set up. Add GOOGLE_API_KEY to the .env file (or to Streamlit Secrets)."
    try:
        return run_agent(text, history or [])
    except Exception as e:
        return f"⚠️ The AI agent had a problem: {e}"