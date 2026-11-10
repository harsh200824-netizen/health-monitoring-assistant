"""Short research summaries: fetch from NLM / OpenFDA, then ask Gemini to summarise.

Gemini only rewrites the text the APIs returned. It is told not to add facts,
diagnose, or recommend doses.
"""

import os

from dotenv import load_dotenv

from backend.services.api_services import search_health_information, search_drug_label
from backend.services.http_client import ExternalAPIError

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _ask_gemini(prompt):
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)
    reply = llm.invoke(prompt)
    content = reply.content
    if isinstance(content, str):
        return content
    return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)


def summarise_topic(topic):
    """Return a short summary of related conditions and, if found, a drug label."""
    topic = (topic or "").strip()
    if not topic:
        return {"error": "Topic is empty."}

    sources = []
    try:
        conditions = search_health_information(topic)["results"]
        sources.append("Related conditions (NLM): " + ", ".join(conditions))
    except ExternalAPIError as exc:
        sources.append(f"NLM lookup failed: {exc.message}")

    try:
        label = search_drug_label(topic)
        sources.append(
            f"FDA label for {label['drug']}: Purpose: {label['purpose']}. "
            f"Warnings: {label['warnings']}"
        )
    except ExternalAPIError:
        pass  # topic is not a drug name; that is fine

    if not os.getenv("GOOGLE_API_KEY"):
        return {"topic": topic, "summary": None, "sources": sources,
                "error": "GOOGLE_API_KEY is not set in .env."}

    prompt = (
        "Summarise the following source text for a patient in 3 short sentences. "
        "Use only the facts given. Do not add medical advice or doses. "
        "End with: 'Ask your doctor or pharmacist for personal advice.'\n\n"
        + "\n".join(sources)
    )
    try:
        summary = _ask_gemini(prompt)
    except Exception as exc:
        return {"topic": topic, "summary": None, "sources": sources,
                "error": f"Gemini could not respond: {exc}"}

    return {"topic": topic, "summary": summary.strip(), "sources": sources, "error": None}