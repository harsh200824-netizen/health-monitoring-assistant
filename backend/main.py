#backend/main.py
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import csv
import io
import json
import math
import xml.etree.ElementTree as ET

from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

from backend.workflow import health_workflow
from backend.database.database import (
    init_db,
    get_health_summary,
    get_medications,
    get_dose_log,
    get_metrics,
    add_metric,
    get_fitness_activities,
    add_fitness_activity,
    get_fitness_summary,
    add_health_goal,
    get_health_goals,
    get_health_goal_progress,
)
from src.database import get_connection, migrate_user_id

from backend.analytics import get_health_analytics
from backend.insights import generate_health_insights
from backend.agent import run_agent
from backend.reports import generate_health_report
from backend.tools.medicine_tools import check_medication_interactions

# Week 5-6 (Track A, Option A2): Medication & Wellness Tracker
from backend.wellness.router import router as wellness_router
from backend.wellness.schema import init_wellness_db

from backend.wellness.schema_b import init_schema_b



app = FastAPI(
    title="Smart Health Assistant API",
    description="Backend API for the Track B Smart Health Assistant",
    version="1.0.0",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"user_id": user_id, "role": role}


ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize database
init_db()
migrate_user_id()
init_wellness_db()
init_schema_b()          # Track B tables

app.include_router(wellness_router)


# ---------- Request models ----------

class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty.")
        if any(ord(char) < 32 and char not in "\\n\\r\\t" for char in value):
            raise ValueError("Question contains unsupported control characters.")
        return value


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class FitnessActivityRequest(BaseModel):
    activity_type: str = Field(min_length=1, max_length=50)
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    steps: Optional[int] = Field(default=None, ge=0, le=200000)
    distance_km: Optional[float] = Field(default=None, ge=0, le=1000)
    calories_burned: Optional[int] = Field(default=None, ge=0, le=20000)
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=24)
    notes: str = Field(default="", max_length=500)


class HealthGoalRequest(BaseModel):
    goal_type: str = Field(min_length=1, max_length=50)
    target_value: float = Field(gt=0, le=1000000)
    unit: str = Field(min_length=1, max_length=30)


class MedicationInteractionRequest(BaseModel):
    medications: list[str] = Field(min_length=1)


# ---------- Basic endpoints ----------

@app.get("/")
def home():
    return {"message": "Smart Health Assistant API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ---------- Authentication ----------

@app.post("/register", status_code=201)
def register_user(request: RegisterRequest):
    username = request.username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username cannot be empty.",
        )

    conn = get_connection()

    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Username already exists.",
            )

        password_hash = hash_password(request.password)

        cursor = conn.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, 'patient')
            """,
            (username, password_hash),
        )

        conn.commit()

        return {
            "message": "User registered successfully",
            "user_id": cursor.lastrowid,
            "username": username,
            "role": "patient",
        }
    finally:
        conn.close()


@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    username = form_data.username.strip()

    conn = get_connection()
    try:
        user = conn.execute(
            """
            SELECT id, username, password_hash, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    finally:
        conn.close()

    if user is None or not verify_password(
        form_data.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(user["id"]), user["role"])

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ---------- Health data ----------

@app.get("/health/summary")
def health_summary(current_user: dict = Depends(get_current_user)):
    return get_health_summary(current_user["user_id"])


@app.get("/medications")
def medications(current_user: dict = Depends(get_current_user)):
    # FIX: Pass the logged-in user's ID.
    return get_medications(
        user_id=current_user["user_id"],
        active_only=True,
    )


@app.get("/dose-history")
def dose_history(current_user: dict = Depends(get_current_user)):
    return get_dose_log()


@app.get("/health-metrics")
def health_metrics(current_user: dict = Depends(get_current_user)):
    return get_metrics()


@app.get("/analytics")
def analytics(current_user: dict = Depends(get_current_user)):
    return get_health_analytics(
        user_id=current_user["user_id"]
    )


@app.get("/insights")
def health_insights(
    current_user: dict = Depends(get_current_user)
):
    return generate_health_insights(
        user_id=current_user["user_id"]
    )


# ---------- AI assistant ----------

@app.post("/ask")
@app.post("/workflow")
def ask_question(
    request: QuestionRequest,
    current_user: dict = Depends(get_current_user),
):
    result = health_workflow.invoke({
        "question": request.question,
        "user_id": current_user["user_id"],
    })
    return result["result"]


# ---------- Fitness tracking ----------

@app.get("/fitness-activities")
def fitness_activities(current_user: dict = Depends(get_current_user)):
    return get_fitness_activities()


@app.post("/fitness-activities")
def create_fitness_activity(
    request: FitnessActivityRequest,
    current_user: dict = Depends(get_current_user),
):
    activity_type = request.activity_type.strip()

    if not activity_type:
        raise HTTPException(
            status_code=422,
            detail="Activity type cannot be empty.",
        )

    measurements = [
        request.duration_minutes,
        request.steps,
        request.distance_km,
        request.calories_burned,
        request.sleep_hours,
    ]

    if all(value is None for value in measurements):
        raise HTTPException(
            status_code=422,
            detail="Provide at least one fitness measurement.",
        )

    activity_id = add_fitness_activity(
        user_id=current_user["user_id"],
        activity_type=activity_type,
        duration_minutes=request.duration_minutes,
        steps=request.steps,
        distance_km=request.distance_km,
        calories_burned=request.calories_burned,
        sleep_hours=request.sleep_hours,
        notes=request.notes,
    )

    return {
        "message": "Fitness activity saved successfully.",
        "id": activity_id,
    }


@app.get("/fitness-summary")
def fitness_summary(current_user: dict = Depends(get_current_user)):
    return get_fitness_summary()


# ---------- Health goals ----------

@app.get("/health-goals")
def health_goals(current_user: dict = Depends(get_current_user)):
    return get_health_goals()


@app.post("/health-goals")
def create_health_goal(
    request: HealthGoalRequest,
    current_user: dict = Depends(get_current_user),
):
    goal_type = request.goal_type.strip()
    unit = request.unit.strip()

    if not goal_type or not unit:
        raise HTTPException(
            status_code=422,
            detail="Goal type and unit cannot be empty.",
        )

    goal_id = add_health_goal(
        goal_type=goal_type,
        target_value=request.target_value,
        unit=unit,
    )

    return {
        "message": "Health goal created successfully.",
        "id": goal_id,
    }


@app.get("/health-goals/progress")
def health_goal_progress(current_user: dict = Depends(get_current_user)):
    return get_health_goal_progress()


# ---------- Medication interactions ----------

@app.post("/medication-interactions")
def medication_interactions(
    request: MedicationInteractionRequest,
    current_user: dict = Depends(get_current_user),
):
    medication_names = [
        name.strip()
        for name in request.medications
        if name.strip()
    ]

    if not medication_names:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one medication name.",
        )

    return check_medication_interactions(medication_names)


# ---------- Health data import ----------

@app.post("/health-data/import")
async def import_health_data(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    filename = (file.filename or "").lower()
    content = await file.read()

    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File must be smaller than 2 MB.",
        )

    try:
        if filename.endswith(".json"):
            data = json.loads(content.decode("utf-8"))

        elif filename.endswith(".csv"):
            text_data = content.decode("utf-8-sig")
            data = list(csv.DictReader(io.StringIO(text_data)))

        elif filename.endswith(".xml"):
            root = ET.fromstring(content)
            data = [
                {child.tag: child.text for child in item}
                for item in root
            ]

        else:
            raise HTTPException(
                status_code=400,
                detail="Only JSON, CSV, and XML files are supported.",
            )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        ET.ParseError,
        csv.Error,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable health data file.",
        )

    if isinstance(data, dict):
        records = data.get(
            "records",
            data.get("health_data", data),
        )
        if isinstance(records, dict):
            records = [records]
    elif isinstance(data, list):
        records = data
    else:
        raise HTTPException(
            status_code=400,
            detail="File must contain health metric records.",
        )

    if not isinstance(records, list):
        raise HTTPException(
            status_code=400,
            detail="Invalid health record structure.",
        )

    imported = 0
    skipped = 0

    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue

        metric_type = (
            record.get("metric_type")
            or record.get("type")
            or record.get("name")
        )
        value = record.get("value")
        unit = record.get("unit") or ""

        if metric_type is None or value is None:
            skipped += 1
            continue

        metric_type = str(metric_type).strip()
        unit = str(unit).strip()

        if (
            not metric_type
            or len(metric_type) > 100
            or len(unit) > 30
        ):
            skipped += 1
            continue

        try:
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                skipped += 1
                continue
        except (ValueError, TypeError):
            skipped += 1
            continue

        add_metric(metric_type, numeric_value, unit)
        imported += 1

    return {
        "message": "Health data import completed.",
        "filename": filename,
        "format": filename.rsplit(".", 1)[-1],
        "imported_records": imported,
        "skipped_records": skipped,
    }


# ---------- Health report ----------

@app.get("/health-report")
def health_report(current_user: dict = Depends(get_current_user)):
    return generate_health_report(user_id=current_user["user_id"])