"""Read a medicine label photo with Gemini vision.

The photo is sent to Gemini once, the text is returned, and nothing is saved.
This is reading printed text only. It is not a diagnosis or dosing advice.
"""

import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_BYTES = 4 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

PROMPT = (
    "This is a photo of a medicine label or box. Read only the printed text. "
    "Return these lines: Medicine name, Strength, Printed directions, Expiry date. "
    "If something is not clearly readable, write 'unclear' instead of guessing. "
    "Do not add medical advice, doses or any information that is not printed on the label."
)


def read_label(image_bytes, mime_type):
    if mime_type not in ALLOWED_TYPES:
        return {"error": "Please upload a JPG, PNG or WEBP image."}
    if not image_bytes:
        return {"error": "The file is empty."}
    if len(image_bytes) > MAX_BYTES:
        return {"error": "Image must be smaller than 4 MB."}
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error": "GOOGLE_API_KEY is not set in .env."}

    import base64
    from langchain_google_genai import ChatGoogleGenerativeAI

    encoded = base64.b64encode(image_bytes).decode("ascii")
    message = HumanMessage(content=[
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": f"data:{mime_type};base64,{encoded}"},
    ])

    try:
        llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)
        reply = llm.invoke([message])
    except Exception as exc:
        return {"error": f"Gemini could not read the image: {exc}"}

    content = reply.content
    text = content if isinstance(content, str) else "".join(
        p.get("text", "") if isinstance(p, dict) else str(p) for p in content
    )
    return {
        "result": text.strip(),
        "note": "Text read from the photo. Check it against the box, and ask a pharmacist before taking any medicine.",
    }