from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    topic_states = relationship("StudentTopicState", back_populates="student")
    events = relationship("Event", back_populates="student")
    drift_events = relationship("DriftEvent", back_populates="student")

class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    # Default BKT parameters for this topic
    default_p_init = Column(Float, default=0.5)
    default_p_learn = Column(Float, default=0.1)
    default_p_guess = Column(Float, default=0.2)
    default_p_slip = Column(Float, default=0.1)

    resources = relationship("Resource", back_populates="topic")
    student_states = relationship("StudentTopicState", back_populates="topic")
    questions = relationship("Question", back_populates="topic")

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text) # The actual educational content
    topic_id = Column(Integer, ForeignKey("topics.id"))
    difficulty = Column(Float, default=0.5) # 0.0 to 1.0
    tags = Column(String) # Comma-separated tags

    topic = relationship("Topic", back_populates="resources")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"))
    text = Column(String)
    options = Column(JSON) # List of strings ["Option A", "Option B", ...]
    correct_index = Column(Integer) # Index of correct option (0-3)
    difficulty = Column(Float, default=0.5)

    topic = relationship("Topic", back_populates="questions")

class StudentTopicState(Base):
    __tablename__ = "student_topic_states"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    
    # Current BKT State
    mastery_probability = Column(Float, default=0.5)
    
    # Per-student encoded BKT params (initially copied from Topic defaults)
    p_init = Column(Float)
    p_learn = Column(Float)
    p_guess = Column(Float)
    p_slip = Column(Float)

    last_updated = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="topic_states")
    topic = relationship("Topic", back_populates="student_states")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=True)
    
    event_type = Column(String) # 'quiz', 'view'
    is_correct = Column(Boolean, nullable=True) # For quizzes
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Debug info
    prediction_error = Column(Float, nullable=True) # Computed error for drift detection

    student = relationship("Student", back_populates="events")
    topic = relationship("Topic")

class DriftEvent(Base):
    __tablename__ = "drift_events"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    detected_at = Column(DateTime, default=datetime.utcnow)
    metric_value = Column(Float) # The ADWIN statistic or error rate
    notes = Column(String) # Description of adaptation action taken

    student = relationship("Student", back_populates="drift_events")
    topic = relationship("Topic")
