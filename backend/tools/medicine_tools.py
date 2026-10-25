
from backend.database.database import get_medications


def medication_tool():
    """Get the patient's active medications."""
    return get_medications(active_only=True)


def check_medication_interactions(medications):
    """
    Demonstration-only medication interaction checker.

    This does not use a verified drug-interaction database and
    must not be used to decide whether medications are safe together.
    """
    if not medications:
        return {
            "status": "no_medications",
            "message": "No medications were provided for checking.",
            "interactions": [],
            "medical_review_required": True,
        }

    names = []
    for medication in medications:
        if isinstance(medication, dict):
            name = medication.get("name") or medication.get("medication_name")
        else:
            name = str(medication)

        if name:
            names.append(str(name).strip())

    return {
        "status": "not_verified",
        "medications_checked": names,
        "interactions": [],
        "message": (
            "No verified interaction database is connected. "
            "An empty result does not mean these medications are safe "
            "to take together. Ask a pharmacist or doctor to review them."
        ),
        "medical_review_required": True,
    }
