import requests
import random
import time

API_URL = "http://localhost:8000"

def simulate():
    # Ensure student exists via seed or just use ID=1
    student_id = 1
    topic_id = 1 # Algebra
    
    print("Starting simulation for Student 1 on Topic 1...")
    
    # Phase 1: High Performance (20 events)
    print("Phase 1: High Mastery (Success Rate 90%)")
    for i in range(20):
        is_correct = random.random() < 0.9
        try:
            resp = requests.post(f"{API_URL}/events/simulate", json={
                "student_id": student_id,
                "topic_id": topic_id,
                "is_correct": is_correct
            })
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}")
                continue
                
            data = resp.json()
            print(f"Event {i+1}: Correct={is_correct} | Mastery={data['new_mastery']:.3f} | Drift={data['drift_status']}")
        except Exception as e:
            print(f"Connection failed: {e}")
        time.sleep(0.1)

    # Phase 2: Drift (Concept Drift - sudden drop in performance)
    print("\nPhase 2: Concept Drift (Success Rate 20%) - Student forgets or gets distracted")
    for i in range(20, 50):
        is_correct = random.random() < 0.2
        try:
            resp = requests.post(f"{API_URL}/events/simulate", json={
                "student_id": student_id,
                "topic_id": topic_id,
                "is_correct": is_correct
            })
            if resp.status_code != 200:
                print(f"Error {resp.status_code}: {resp.text}")
                continue

            data = resp.json()
            print(f"Event {i+1}: Correct={is_correct} | Mastery={data['new_mastery']:.3f} | Drift={data['drift_status']}")
            if data['drift_status'] == "Drift Detected":
                print("!!! DRIFT DETECTED - SYSTEM ADAPTING !!!")
        except Exception as e:
            print(f"Connection failed: {e}")
        time.sleep(0.1)

if __name__ == "__main__":
    print("Make sure server is running on localhost:8000")
    simulate()
