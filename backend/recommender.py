from sqlalchemy.orm import Session
from .models import Student, Resource, StudentTopicState, DriftEvent, Topic
from datetime import datetime, timedelta
import random

def get_recommendations(db: Session, student_id: int):
    # 1. Get student's weak topics (Mastery < 0.6)
    # 2. Check for recent drift events (last 24 hours)
    # 3. For drifted topics, recommend easier resources.
    # 4. For weak topics, recommend medium resources.
    # 5. For mastered topics, recommend hard resources (or skip).
    
    student = db.query(Student).get(student_id)
    if not student:
        return []

    recommendations = []
    
    # Get recent drift events
    recent_drift_cutoff = datetime.utcnow() - timedelta(days=1)
    drifted_topics = db.query(DriftEvent).filter(
        DriftEvent.student_id == student_id,
        DriftEvent.detected_at >= recent_drift_cutoff
    ).all()
    drifted_topic_ids = {d.topic_id for d in drifted_topics}

    # Iterate over topic states
    topic_states = db.query(StudentTopicState).filter_by(student_id=student_id).all()
    
    for state in topic_states:
        topic_id = state.topic_id
        mastery = state.mastery_probability
        
        # Determine target difficulty
        if topic_id in drifted_topic_ids:
            target_difficulty_range = (0.0, 0.4) # Go back to basics
            reason = "Drift detected - Reviewing Basics"
        elif mastery < 0.4:
            target_difficulty_range = (0.0, 0.5)
            reason = "Low Mastery - Foundational"
        elif mastery < 0.7:
            target_difficulty_range = (0.4, 0.7)
            reason = "Building Mastery - Intermediate"
        else:
            target_difficulty_range = (0.7, 1.0)
            reason = "Mastered - Advanced Challenge"

        # Fetch resources
        resources = db.query(Resource).filter(
            Resource.topic_id == topic_id,
            Resource.difficulty >= target_difficulty_range[0],
            Resource.difficulty <= target_difficulty_range[1]
        ).limit(2).all()
        
        for r in resources:
            recommendations.append({
                "resource_id": r.id,
                "title": r.title,
                "topic": r.topic.name,
                "difficulty": r.difficulty,
                "reason": reason
            })
            
    # Fallback/Explore: Use TF-IDF to find resources similar to weak topics
    if len(recommendations) < 5:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Get all resources
        all_resources = db.query(Resource).all()
        
        # Simple check: do we have enough resources to recommend?
        if all_resources:
             # Create corpus: Topic Names + Weak Topic Names
             weak_topic_names = [s.topic.name for s in topic_states if s.mastery_probability < 0.6]
             query = " ".join(weak_topic_names)
             
             if query:
                 res_texts = [f"{r.title} {r.tags} {r.topic.name}" for r in all_resources]
                 vectorizer = TfidfVectorizer()
                 tfidf_matrix = vectorizer.fit_transform(res_texts + [query])
                 
                 # Compute similarity of query (last item) vs all resources
                 cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
                 
                 # Get top indices
                 import numpy as np
                 top_indices = np.argsort(cosine_sim[0])[::-1]
                 
                 # Helper to track seen IDs locally for this loop if needed, 
                 # but we deduplicate globally later anyway.
                 local_seen = {r['resource_id'] for r in recommendations}
                 
                 for idx in top_indices:
                     r = all_resources[idx]
                     if r.id not in local_seen:
                         recommendations.append({
                             "resource_id": r.id,
                             "title": r.title,
                             "topic": r.topic.name,
                             "difficulty": r.difficulty,
                             "reason": "AI Recommended (Content Match)"
                         })
                         local_seen.add(r.id)
                         if len(recommendations) >= 5:
                             break

    # Deduplicate final check
    final_recs = []
    seen_ids = set()
    for r in recommendations:
        if r['resource_id'] not in seen_ids:
            final_recs.append(r)
            seen_ids.add(r['resource_id'])

    return final_recs
