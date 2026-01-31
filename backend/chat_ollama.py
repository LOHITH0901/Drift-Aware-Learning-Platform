import requests
import json
from sqlalchemy.orm import Session
from .models import Student, StudentTopicState, Event, DriftEvent, Resource
from .recommender import get_recommendations

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "phi3:mini"

def retrieve_enhanced_context(db: Session, student_id: int):
    # 1. Weak Topics
    states = db.query(StudentTopicState).filter(StudentTopicState.student_id == student_id).all()
    weak_topics = [s.topic.name for s in states if s.mastery_probability < 0.6]
    
    # 2. Last 5 Quiz Results
    last_events = db.query(Event).filter_by(student_id=student_id).order_by(Event.timestamp.desc()).limit(5).all()
    history_summary = []
    for e in last_events:
        res = "Correct" if e.is_correct else "Incorrect"
        history_summary.append(f"{e.topic.name}: {res}")
    
    # 3. Drift Status
    recent_drift = db.query(DriftEvent).filter_by(student_id=student_id).order_by(DriftEvent.detected_at.desc()).first()
    drift_status = "Drift Detected Recently" if recent_drift else "Stable"
    
    # 4. Top Recommendations
    recs = get_recommendations(db, student_id)[:3]
    rec_summary = [f"{r['title']} ({r['reason']})" for r in recs]
    
    # 5. Course Content Keywords (Simple Search)
    # Return basic chunks - in real app use vector DB
    # We will search for resources matching weak_topics names
    context_notes = []
    if weak_topics:
        # Simple OR search
        resources = db.query(Resource).filter(Resource.content.contains(weak_topics[0])).limit(2).all()
        for r in resources:
            context_notes.append(f"From {r.title}: {r.content[:200]}...")

    return f"""
    Student Profile:
    - Weak Topics: {', '.join(weak_topics) if weak_topics else 'None'}
    - Recent Performance: {'; '.join(history_summary)}
    - Learning State: {drift_status}
    - Recommended Next Steps: {'; '.join(rec_summary)}
    - Relevant Course Notes:
      {chr(10).join(context_notes)}
    """

def chat_with_ollama(student_id: int, message: str, db: Session):
    context = retrieve_enhanced_context(db, student_id)
    
    system_prompt = f"""You are a helpful AI tutor for a student on the Drift-Aware Learning Platform.
    
    CONTEXT ABOUT STUDENT:
    {context}
    
    INSTRUCTIONS:
    1. Answer the student's question clearly and simply.
    2. Use the provided Student Profile context to personalize your advice (e.g. mention their weak topics or recent mistakes).
    3. Use the 'Relevant Course Notes' as the ground truth for academic content.
    4. If you don't know, say "I don't have that information in the course materials."
    5. Do NOT give medical or mental health advice.
    6. Always end with 2 practice questions related to the topic discussed.
    """

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()['message']['content']
    except Exception as e:
        return f"Error communicating with AI Assistant: {str(e)}. Make sure Ollama is running."

def generate_sub_quiz(subject: str, focus_area: str, start_id: int):
    system_prompt = f"""You are an expert exam setter. 
    Task: Create a 12-question Multiple Choice Quiz for '{subject}'.
    Focus Area: {focus_area}.
    
    RULES:
    1. Output strictly valid JSON.
    2. Questions must be clear and complete (No 'Question text missing').
    3. Provide exactly 4 distinct options per question.
    4. Do not include 'Option A', 'Option B' labels in the option text.
    
    Structure:
    {{
        "questions": [
            {{
                "text": "The actual question goes here?",
                "options": ["First Answer", "Second Answer", "Third Answer", "Fourth Answer"],
                "correct_index": 0,
                "topic": "Concept Name"
            }},
            ...
        ]
    }}
    """
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_prompt}],
        "stream": False, "format": "json"
    }
    try:
        # TIMEOUT increased to 300s for slower Windows machines
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        raw_content = response.json()['message']['content']
        
        # Clean Markdown
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0]
        elif "```" in raw_content:
            raw_content = raw_content.split("```")[1].split("```")[0]
        
        result = json.loads(raw_content.strip())
        
        sanitized_questions = []
        if isinstance(result, dict) and 'questions' in result:
            raw_list = result['questions']
        elif isinstance(result, list):
            raw_list = result
        else:
            return None 

        for q in raw_list:
            if not isinstance(q, dict): continue
            
            # --- STRICT FILTERING ---
            # If crucial data is missing, we DISCARD the question rather than showing "Missing".
            
            # 1. Check Text
            if 'text' not in q or len(q['text']) < 5: 
                continue # Skip bad text
            
            # 2. Check Options
            raw_opts = q.get('options', [])
            clean_opts = []
            if isinstance(raw_opts, list):
                for opt in raw_opts:
                    clean_opts.append(str(opt) if not isinstance(opt, dict) else opt.get('text', ''))
            
            # We strictly need at least 2 valid options to make a question. 
            # Ideally 4. We will fill up to 4 with "None of the above" type fillers if we have at least 2.
            # If < 2 real options, discard.
            clean_opts = [o for o in clean_opts if o and len(str(o)) > 1]
            
            if len(clean_opts) < 2:
                continue 
            
            # Pad with generic destructors if 2 or 3 options
            required_fillers = 4 - len(clean_opts)
            fillers = ["None of the above", "All of the above", "Not applicable"]
            for i in range(required_fillers):
                clean_opts.append(fillers[i])
            
            q['options'] = clean_opts[:4]
            q['id'] = start_id # Assign distinct IDs sequentially later
            start_id += 1
            
            # 3. Fix Correct Index
            try:
                idx = int(q.get('correct_index', 0))
                if idx < 0 or idx >= 4: idx = 0
                q['correct_index'] = idx
            except: q['correct_index'] = 0
            
            sanitized_questions.append(q)
            
        return {"questions": sanitized_questions}

    except Exception as e:
        print(f"Error generation failed: {e}")
        return None         

def generate_assessment_quiz(subject: str):
    questions = []
    
    # Batch 1: Fundamentals
    q1 = generate_sub_quiz(subject, "Fundamentals, Definitions, and Core Concepts", 1)
    if q1 and 'questions' in q1:
        questions.extend(q1['questions'])
        
    # Batch 2: Advanced
    q2 = generate_sub_quiz(subject, "Advanced Topics, Edge Cases, and Real-world Applications", 11)
    if q2 and 'questions' in q2:
        questions.extend(q2['questions'])
        
    if not questions:
        return None
        
    return {"questions": questions}

def analyze_assessment_results(subject: str, score: int, total: int, incorrect_topics: list):
    system_prompt = f"""You are an expert academic advisor.
    Student just took a {subject} exam.
    Score: {score}/{total}.
    Weak Areas (Incorrect Answers): {', '.join(incorrect_topics) if incorrect_topics else 'None - Perfect Score'}.
    
    Task: Provide a JSON analysis.
    Format:
    {{
        "verdict": "Good" | "Average" | "Bad",
        "feedback": "2-3 sentences summary",
        "study_plan": ["Topic 1: specific advice", "Topic 2: specific advice"],
        "mastered_topics": ["List of topics likely mastered based on score"]
    }}
    """
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system_prompt}],
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        content = response.json()['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"Error analyzing results: {e}")
        return {
            "verdict": "Unknown", 
            "feedback": "Could not analyze results.", 
            "study_plan": [], 
            "mastered_topics": []
        }
