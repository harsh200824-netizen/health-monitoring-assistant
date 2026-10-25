import datetime as dt
import io
import math
import os
import struct
import wave

import pandas as pd
import streamlit as st

from src.database import (
    init_db,
    now_local,
    add_medication,
    delete_medication,
    get_metrics,
    get_dose_log,
    log_dose,
)
from src.scheduler import get_schedule_status, get_alerts, format_time_12h
from src.chatbot import handle_message, METRIC_LABELS, HELP_TEXT, STATUS_ICONS

st.set_page_config(page_title="Health Monitoring Assistant", page_icon="💊", layout="wide")

# On Streamlit Cloud the API key comes from Secrets
try:
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
except Exception:
    pass

init_db()


def make_beep():
    """Make a 3-beep alarm sound in memory (no audio file needed)."""
    rate = 44100
    frames = bytearray()
    for _ in range(3):
        for i in range(int(rate * 0.25)):
            value = int(12000 * math.sin(2 * math.pi * 880 * i / rate))
            frames += struct.pack("<h", value)
        frames += b"\x00\x00" * int(rate * 0.15)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


BEEP = make_beep()


@st.fragment(run_every=30)
def show_alerts():
    """Checks reminders every 30 seconds, shows banners, toast and beep."""
    if "played" not in st.session_state:
        st.session_state.played = set()
    today = now_local().strftime("%Y-%m-%d")
    play_sound = False

    for alert in get_alerts():
        if alert["level"] == "due":
            st.warning(alert["message"])
            key = (today, alert["message"])
            if key not in st.session_state.played:
                st.session_state.played.add(key)
                st.toast(alert["message"], icon="⏰")
                play_sound = True
        else:
            st.error(alert["message"])

    if play_sound:
        st.audio(BEEP, format="audio/wav", autoplay=True)


if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! 👋 I'm your health monitoring assistant. Tell me your medicines and readings.\n\n" + HELP_TEXT,
        }
    ]

# ---------- Sidebar ----------
with st.sidebar:
    st.header("💊 Health Assistant")
    st.caption("Track medicines, reminders and health readings.")
    st.info("For tracking and reminders only. Not medical advice.")
    if st.button("🔄 Refresh reminders"):
        st.rerun()
    if st.button("🧹 Clear chat"):
        del st.session_state["messages"]
        st.rerun()

st.title("Health Monitoring Assistant")

alert_box = st.container()

tab_chat, tab_meds, tab_metrics, tab_history = st.tabs(
    ["💬 Chat", "💊 Medications", "📈 Health metrics", "🧾 Dose history"]
)

# ---------- Chat tab ----------
with tab_chat:
    chat_box = st.container()
    prompt = st.chat_input("e.g. Remind me to take Metformin 500mg at 9am")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Thinking..."):
            reply = handle_message(prompt, st.session_state.messages[1:-1])
        st.session_state.messages.append({"role": "assistant", "content": reply})
    with chat_box:
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

# ---------- Medications tab ----------
with tab_meds:
    with st.expander("➕ Add a medication"):
        with st.form("add_med_form", clear_on_submit=True):
            name = st.text_input("Medicine name")
            dosage = st.text_input("Dosage (e.g. 500mg)")
            med_time = st.time_input("Reminder time", value=dt.time(9, 0))
            submitted = st.form_submit_button("Add medication")
        if submitted:
            if not name.strip():
                st.error("Please enter a medicine name.")
            else:
                add_medication(name.strip().title(), dosage.strip(), med_time.strftime("%H:%M"))
                st.success(f"Added {name.strip().title()}")

    st.subheader("Today's schedule")
    schedule = get_schedule_status()
    if not schedule:
        st.info("No medications yet. Add one above or use the chat.")
    for med in schedule:
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1.5, 1.5])
        c1.write(f"**{med['name']}** {med['dosage'] or ''}")
        c2.write(format_time_12h(med["time"]))
        c3.write(f"{STATUS_ICONS[med['status']]} {med['status'].title()}")
        if med["status"] != "taken":
            if c4.button("Taken", key=f"taken_{med['id']}"):
                log_dose(med["id"])
                st.rerun()
        if c5.button("Delete", key=f"del_{med['id']}"):
            delete_medication(med["id"])
            st.rerun()

# ---------- Health metrics tab ----------
with tab_metrics:
    metrics = get_metrics()
    if not metrics:
        st.info("No readings yet. In the chat, type: BP was 120/80")
    else:
        df = pd.DataFrame(metrics)
        types = sorted(df["metric_type"].unique())
        selected = st.selectbox(
            "Metric", types, format_func=lambda t: METRIC_LABELS.get(t, t)
        )
        sub = df[df["metric_type"] == selected].copy()
        sub["recorded_at"] = pd.to_datetime(sub["recorded_at"])
        sub = sub.sort_values("recorded_at")

        latest = sub.iloc[-1]
        st.metric("Latest reading", f"{latest['value']} {latest['unit']}")

        if selected == "blood_pressure":
            parts = sub["value"].str.split("/", expand=True)
            sub["Systolic"] = pd.to_numeric(parts[0], errors="coerce")
            sub["Diastolic"] = pd.to_numeric(parts[1], errors="coerce")
            chart_cols = ["Systolic", "Diastolic"]
        else:
            sub["Value"] = pd.to_numeric(sub["value"], errors="coerce")
            chart_cols = ["Value"]

        st.line_chart(sub.set_index("recorded_at")[chart_cols])
        st.dataframe(
            sub[["recorded_at", "value", "unit"]].sort_values("recorded_at", ascending=False),)