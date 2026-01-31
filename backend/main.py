from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from .db import get_db, engine, Base
from .models import Student, Instructor, Topic, Resource, Event, StudentTopicState, DriftEvent, Question
from .bkt import BKTTracker
from .drift import DriftDetector
from .recommender import get_recommendations
from .chat_ollama import chat_with_ollama
from .auth import verify_password, get_password_hash

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Drift-Aware Learning Platform")

# Instantiate Global Detection Manager
drift_manager = DriftDetector()

# --- Pydantic Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    id: int
    username: str
    role: str
    name: str

class QuestionCreate(BaseModel):
    topic_id: int
    text: str
    options: List[str]
    correct_index: int
    difficulty: float

class QuestionResponse(BaseModel):
    id: int
    topic_id: int
    text: str
    options: List[str]
    difficulty: float
    # correct_index hidden for students

class QuizSubmit(BaseModel):
    student_id: int
    question_id: int
    selected_index: int

class ChatRequest(BaseModel):
    student_id: int
    message: str

class ResourceCreate(BaseModel):
    title: str
    content: str
    topic_id: int
    difficulty: float
    tags: str

class AssessmentRequest(BaseModel):
    subject: str

class AssessmentAnalysisRequest(BaseModel):
    subject: str
    score: int
    total: int
    incorrect_topics: List[str]

class StudentRegister(BaseModel):
    username: str
    password: str
    name: str

# --- AUTH ENDPOINTS ---

@app.post("/register/student", response_model=LoginResponse)
def register_student(student: StudentRegister, db: Session = Depends(get_db)):
    if db.query(Student).filter(Student.username == student.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pwd = get_password_hash(student.password)
    db_student = Student(username=student.username, password_hash=hashed_pwd, name=student.name)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    
    return {"id": db_student.id, "username": db_student.username, "role": "student", "name": db_student.name}

@app.post("/login/student", response_model=LoginResponse)
def login_student(creds: LoginRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.username == creds.username).first()
    if not student or not verify_password(creds.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"id": student.id, "username": student.username, "role": "student", "name": student.name}

@app.post("/login/instructor", response_model=LoginResponse)
def login_instructor(creds: LoginRequest, db: Session = Depends(get_db)):
    instructor = db.query(Instructor).filter(Instructor.username == creds.username).first()
    if not instructor or not verify_password(creds.password, instructor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"id": instructor.id, "username": instructor.username, "role": "instructor", "name": instructor.name}

# --- INSTRUCTOR ENDPOINTS ---

@app.post("/questions")
def create_question(q: QuestionCreate, db: Session = Depends(get_db)):
    db_q = Question(
        topic_id=q.topic_id,
        text=q.text,
        options=q.options,
        correct_index=q.correct_index,
        difficulty=q.difficulty
    )
    db.add(db_q)
    db.commit()
    return {"status": "created", "id": db_q.id}

@app.get("/questions", response_model=List[QuestionResponse])
def get_questions(db: Session = Depends(get_db)):
    questions = db.query(Question).all()
    # In a real app we'd filter or map more carefully
    return questions

@app.get("/students")
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    # Return simple list for instructor view
    return [{"id": s.id, "name": s.name, "username": s.username} for s in students]

@app.post("/resources")
def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    db_resource = Resource(**resource.dict())
    db.add(db_resource)
    db.commit()
    return {"status": "created"}

# --- STUDENT ENDPOINTS ---

@app.get("/students/{student_id}/dashboard")
def get_dashboard(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    try:
        # Mastery per topic
        topic_states = db.query(StudentTopicState).filter_by(student_id=student_id).all()
        mastery_data = [{"topic": s.topic.name, "mastery": s.mastery_probability} for s in topic_states]

        # Recommendations
        recs = get_recommendations(db, student_id)

        # Recent Drift
        recent_drifts = db.query(DriftEvent).filter_by(student_id=student_id).order_by(DriftEvent.detected_at.desc()).limit(5).all()
        
        # History for Line Chart (Last 50 events)
        history_events = db.query(Event).filter_by(student_id=student_id).order_by(Event.timestamp.asc()).limit(50).all()
        progress_data = [{"event": i+1, "score": 1.0 if e.is_correct else 0.0, "time": e.timestamp} for i, e in enumerate(history_events)]

        return {
            "student": student.name,
            "mastery": mastery_data,
            "recommendations": recs,
            "drift_events": [{"topic": d.topic_id, "date": d.detected_at} for d in recent_drifts],
            "progress": progress_data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topics")
def list_topics(db: Session = Depends(get_db)):
    topics = db.query(Topic).all()
    return [{"id": t.id, "name": t.name} for t in topics]

@app.get("/quiz/generate")
def generate_quiz_question(topic_id: int, student_id: int, db: Session = Depends(get_db)):
    # Simple logic: get a random question for the topic.
    # Advanced logic (TODO): Pick based on difficulty matching BKT mastery.
    questions = db.query(Question).filter(Question.topic_id == topic_id).all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this topic")
    import random
    q = random.choice(questions)
    return {
        "id": q.id,
        "text": q.text,
        "options": q.options,
        "difficulty": q.difficulty
    }

@app.post("/events/submit_quiz")
def submit_quiz_answer(submission: QuizSubmit, db: Session = Depends(get_db)):
    question = db.query(Question).get(submission.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    is_correct = (submission.selected_index == question.correct_index)
    topic_id = question.topic_id
    
    # --- BKT & Drift Logic (Same as before) ---
    state = db.query(StudentTopicState).filter_by(student_id=submission.student_id, topic_id=topic_id).first()
    topic = db.query(Topic).get(topic_id)
    
    if not state:
        state = StudentTopicState(
            student_id=submission.student_id,
            topic_id=topic_id,
            mastery_probability=topic.default_p_init,
            p_init=topic.default_p_init,
            p_learn=topic.default_p_learn,
            p_guess=topic.default_p_guess,
            p_slip=topic.default_p_slip
        )
        db.add(state)
        # We need to flush to get ID if needed, but for now object is enough
    
    bkt = BKTTracker(state.p_init, state.p_learn, state.p_guess, state.p_slip)
    predicted_prob = bkt.predict_correctness(state.mastery_probability)
    actual = 1.0 if is_correct else 0.0
    error = abs(actual - predicted_prob)

    new_mastery = bkt.update_mastery(state.mastery_probability, is_correct)
    
    is_drift = drift_manager.update(submission.student_id, topic_id, error)
    drift_msg = "Stable"
    
    if is_drift:
        drift_msg = "Drift Detected"
        drift_event = DriftEvent(
            student_id=submission.student_id,
            topic_id=topic_id,
            metric_value=error,
            notes="High prediction error detected. Adapting mastery."
        )
        db.add(drift_event)
        new_mastery = (new_mastery + 0.5) / 2.0 

    state.mastery_probability = new_mastery
    state.last_updated = datetime.utcnow()
    
    # Log Event
    db_event = Event(
        student_id=submission.student_id,
        topic_id=topic_id,
        resource_id=question.id, # Using resource_id to store question ID for now
        event_type="quiz_real",
        is_correct=is_correct,
        prediction_error=error
    )
    db.add(db_event)
    
    db.commit()
    
    return {
        "correct": is_correct,
        "correct_index": question.correct_index,
        "new_mastery": new_mastery,
        "drift_status": drift_msg
    }

class QuizEventCreate(BaseModel):
    student_id: int
    topic_id: int
    is_correct: bool

@app.post("/events/simulate")
def simulate_quiz_event(event: QuizEventCreate, db: Session = Depends(get_db)):
    # 1. Get/Init State
    state = db.query(StudentTopicState).filter_by(student_id=event.student_id, topic_id=event.topic_id).first()
    topic = db.query(Topic).get(event.topic_id)
    
    if not state:
        state = StudentTopicState(
            student_id=event.student_id,
            topic_id=event.topic_id,
            mastery_probability=topic.default_p_init,
            p_init=topic.default_p_init,
            p_learn=topic.default_p_learn,
            p_guess=topic.default_p_guess,
            p_slip=topic.default_p_slip
        )
        db.add(state)
    
    bkt = BKTTracker(state.p_init, state.p_learn, state.p_guess, state.p_slip)
    predicted_prob = bkt.predict_correctness(state.mastery_probability)
    actual = 1.0 if event.is_correct else 0.0
    error = abs(actual - predicted_prob)

    new_mastery = bkt.update_mastery(state.mastery_probability, event.is_correct)
    
    is_drift = drift_manager.update(event.student_id, event.topic_id, error)
    drift_msg = "Stable"
    
    if is_drift:
        drift_msg = "Drift Detected"
        drift_event = DriftEvent(
            student_id=event.student_id,
            topic_id=event.topic_id,
            metric_value=error,
            notes="High prediction error detected. Adapting mastery."
        )
        db.add(drift_event)
        new_mastery = (new_mastery + 0.5) / 2.0 

    state.mastery_probability = new_mastery
    state.last_updated = datetime.utcnow()
    
    # Log Event
    db_event = Event(
        student_id=event.student_id,
        topic_id=event.topic_id,
        event_type="simulation",
        is_correct=event.is_correct,
        prediction_error=error
    )
    db.add(db_event)
    db.commit()
    
    return {
        "new_mastery": new_mastery,
        "drift_status": drift_msg,
        "predicted_prob": predicted_prob,
        "error": error
    }

@app.get("/drifts/all")
def list_all_drifts(db: Session = Depends(get_db)):
    drifts = db.query(DriftEvent).join(Student).join(Topic).order_by(DriftEvent.detected_at.desc()).limit(20).all()
    return [{
        "student": d.student.name,
        "topic": d.topic.name if d.topic else "Unknown",
        "date": d.detected_at,
        "notes": d.notes
    } for d in drifts]

@app.post("/chat")
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        response = chat_with_ollama(request.student_id, request.message, db)
        return {"response": response}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assessment/generate")
def generate_assessment(req: AssessmentRequest):
    # Import locally to avoid circle if at top (though separate modules preferred)
    from .chat_ollama import generate_assessment_quiz
    quiz = generate_assessment_quiz(req.subject)
    if not quiz:
        raise HTTPException(status_code=500, detail="Failed to generate quiz from AI.")
    return quiz

@app.post("/assessment/analyze")
def analyze_assessment(req: AssessmentAnalysisRequest):
    from .chat_ollama import analyze_assessment_results
    analysis = analyze_assessment_results( req.subject, req.score, req.total, req.incorrect_topics)
    return analysis
