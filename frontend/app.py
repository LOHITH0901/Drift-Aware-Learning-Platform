import streamlit as st
import requests
import pandas as pd
import altair as alt

# --- CONFIG ---
API_URL = "http://localhost:8000"
st.set_page_config(page_title="Drift-Aware Learning Platform", layout="wide", page_icon="🎓")

# --- STYLING ---
st.markdown("""
<style>
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #333;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        color: #888;
    }
    .stApp {
        background-color: #0E1117;
    }
    .login-container {
        max-width: 400px;
        margin: auto;
        padding: 50px;
        border: 1px solid #333;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'token' not in st.session_state:
    st.session_state['token'] = None

# --- AUTH FUNCTIONS ---
def login(username, password, role):
    endpoint = "/login/student" if role == "Student" else "/login/instructor"
    try:
        resp = requests.post(f"{API_URL}{endpoint}", json={"username": username, "password": password})
        if resp.status_code == 200:
            data = resp.json()
            st.session_state['user'] = data
            st.session_state['role'] = data['role']
            st.rerun()
        else:
            st.error("Invalid credentials")
    except Exception as e:
        st.error(f"Connection error: {e}")

def logout():
    st.session_state['user'] = None
    st.session_state['role'] = None
    st.rerun()

# --- DATA FUNCTIONS ---
def get_student_data(student_id):
    try:
        resp = requests.get(f"{API_URL}/students/{student_id}/dashboard")
        return resp.json() if resp.status_code == 200 else None
    except: return None

def get_all_topics():
    try:
        resp = requests.get(f"{API_URL}/topics")
        return resp.json() if resp.status_code == 200 else []
    except: return []

def get_all_students():
    try:
        resp = requests.get(f"{API_URL}/students")
        return resp.json() if resp.status_code == 200 else []
    except: return []

def generate_quiz_question(topic_id, student_id):
    try:
        resp = requests.get(f"{API_URL}/quiz/generate", params={"topic_id": topic_id, "student_id": student_id})
        return resp.json() if resp.status_code == 200 else None
    except: return None

def submit_quiz_answer(student_id, question_id, selected_index):
    try:
        resp = requests.post(f"{API_URL}/events/submit_quiz", json={
            "student_id": student_id,
            "question_id": question_id,
            "selected_index": selected_index
        })
        return resp.json() if resp.status_code == 200 else None
    except: return None

def create_question_api(topic_id, text, options, correct_index, difficulty):
    try:
        resp = requests.post(f"{API_URL}/questions", json={
            "topic_id": topic_id,
            "text": text,
            "options": options,
            "correct_index": correct_index,
            "difficulty": difficulty
        })
        return True if resp.status_code == 200 else False
    except: return False

def get_all_questions():
    try:
        resp = requests.get(f"{API_URL}/questions")
        return resp.json() if resp.status_code == 200 else []
    except: return []

def register(username, password, name):
    try:
        resp = requests.post(f"{API_URL}/register/student", json={"username": username, "password": password, "name": name})
        if resp.status_code == 200:
            data = resp.json()
            st.session_state['user'] = data
            st.session_state['role'] = data['role']
            st.success("Registration successful! Logging in...")
            st.rerun()
        else:
            st.error(f"Registration failed: {resp.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Connection error: {e}")

# --- MAIN APP ---

if not st.session_state['user']:
    # LOGIN SCREEN
    st.title("🔐 Educational Portal Login")
    
    tab_login, tab_register = st.tabs(["Login", "Register (New Student)"])
    
    with tab_login:
        col1, col2 = st.columns([1, 1])
        with col1:
            role_select = st.radio("I am a:", ["Student", "Instructor"])
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Sign In"):
                login(username, password, role_select)
            
            st.info("Demo Credits:\nStudent: student1 / password123\nInstructor: admin / password123")

    with tab_register:
        st.subheader("Create Student Account")
        with st.form("reg_form"):
            new_user = st.text_input("Choose Username")
            new_pass = st.text_input("Choose Password", type="password")
            full_name = st.text_input("Full Name")
            
            if st.form_submit_button("Register"):
                if new_user and new_pass and full_name:
                    register(new_user, new_pass, full_name)
                else:
                    st.error("Please fill all fields")
else:
    # LOGGED IN
    user = st.session_state['user']
    role = st.session_state['role']

    with st.sidebar:
        st.title(f"👤 {user['name']}")
        st.caption(f"Role: {role.capitalize()}")
        if st.button("Logout"):
            logout()
        st.divider()

    # --- STUDENT PORTAL ---
    if role == "student":
        st.sidebar.header("Navigation")
        page = st.sidebar.radio("Go to:", ["Dashboard", "Study Zone (Real Quiz)", "AI Tutor", "Course Assessment"])
        
        student_id = user['id']

        if page == "Dashboard":
            st.title("📊 My Learning Dashboard")
            data = get_student_data(student_id)
            if data:
                # 1. Top Metrics
                recent_drifts = data.get('drift_events', [])
                mastery_list = data.get('mastery', [])
                mastery_df = pd.DataFrame(mastery_list)
                
                if not mastery_list:
                    st.info("👋 Welcome! It looks like you haven't taken any quizzes yet.")
                    st.markdown("### 👉 Go to the **Study Zone** in the sidebar to start your learning journey!")
                    
                    # Show simulated empty metrics
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Average Mastery", "0%")
                    c2.metric("Learning State", "Ready")
                    c3.metric("Quizzes Taken", "0")
                else:
                    avg_mastery = mastery_df['mastery'].mean() if not mastery_df.empty else 0.0
                    
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{avg_mastery:.0%}</div>
                            <div class="metric-label">Average Mastery</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        color = "red" if recent_drifts else "green"
                        status = "Drift Detected" if recent_drifts else "Stable"
                        st.markdown(f"""
                        <div class="metric-card" style="border-color: {color};">
                            <div class="metric-value" style="color: {color};">{status}</div>
                            <div class="metric-label">Learning State</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-value">{len(data.get('progress', []))}</div>
                            <div class="metric-label">Quizzes Taken</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.divider()

                # 2. Charts Row
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.subheader("📊 Mastery by Topic")
                    if not mastery_list:
                        st.info("No mastery data available yet.")
                    else:
                        chart = alt.Chart(mastery_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                            x=alt.X('topic', axis=alt.Axis(labelAngle=0)),
                            y=alt.Y('mastery', scale=alt.Scale(domain=[0, 1])),
                            color=alt.condition(
                                alt.datum.mastery < 0.6,
                                alt.value('#FF4B4B'),  # Red for low mastery
                                alt.value('#00C0F2')   # Blue for high
                            ),
                            tooltip=['topic', 'mastery']
                        ).properties(height=350)
                        st.altair_chart(chart, use_container_width=True)

                with col_right:
                    st.subheader("📈 Progress Over Time")
                    progress_data = data.get('progress', [])
                    if progress_data:
                        prog_df = pd.DataFrame(progress_data)
                        # Calculate rolling average for smoothness
                        prog_df['rolling_avg'] = prog_df['score'].rolling(5, min_periods=1).mean()
                        
                        line = alt.Chart(prog_df).mark_line(point=True, color='#00FF00').encode(
                            x=alt.X('event', title='Quiz Attempt'),
                            y=alt.Y('score', title='Score', scale=alt.Scale(domain=[0, 1])),
                            tooltip=['event', 'score']
                        )
                        
                        rolling = alt.Chart(prog_df).mark_line(color='white', strokeDash=[5, 5]).encode(
                            x='event',
                            y='rolling_avg'
                        )
                        
                        st.altair_chart((line + rolling).properties(height=350), use_container_width=True)
                    else:
                        st.info("No quiz history yet. Start learning!")
        
        elif page == "Study Zone (Real Quiz)":
            st.title("⚡ Interactive Quiz")
            
            topics = get_all_topics()
            t_map = {t['id']: t['name'] for t in topics}
            t_id = st.selectbox("Select Topic to Practice", list(t_map.keys()), format_func=lambda x: t_map[x])
            
            if 'current_question' not in st.session_state:
                st.session_state['current_question'] = None
            
            if st.button("Generate New Question"):
                q = generate_quiz_question(t_id, student_id)
                if q:
                    st.session_state['current_question'] = q
                    st.session_state['quiz_submitted'] = False
                else:
                    st.warning("No questions found for this topic.")
            
            q = st.session_state.get('current_question')
            if q:
                st.markdown(f"### {q['text']}")
                
                # Use radio but maintain state
                choice = st.radio("Choose correct answer:", q['options'], key=f"q_{q['id']}")
                
                if st.button("Submit Answer"):
                    sel_idx = q['options'].index(choice)
                    res = submit_quiz_answer(student_id, q['id'], sel_idx)
                    
                    if res:
                        if res['correct']:
                            st.success(f"✅ Correct! New Mastery: {res['new_mastery']:.2f}")
                            st.balloons()
                        else:
                            st.error(f"❌ Incorrect. Correct answer was Option {res['correct_index']+1}. New Mastery: {res['new_mastery']:.2f}")
                        
                        if res['drift_status'] != "Stable":
                            st.warning("⚠️ Concept Drift Detected! We are adjusting your learning path.")
                            
                        # Clear question after delay? Manual for now.
                        st.session_state['quiz_submitted'] = True
        
        elif page == "AI Tutor":
            st.title("🤖 Personal AI Tutor")
            # Chat UI logic (same as before)
            if 'messages' not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Ask a question about your topics..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            resp = requests.post(f"{API_URL}/chat", json={"student_id": student_id, "message": prompt})
                            if resp.status_code == 200:
                                reply = resp.json()['response']
                            else:
                                reply = "Sorry, I'm having trouble connecting to my brain."
                        except Exception as e:
                            reply = f"Error: {e}"
                        
                        st.markdown(reply)
                
                st.session_state.messages.append({"role": "assistant", "content": reply})

        elif page == "Course Assessment":
            st.title("🎓 AI Course Assessment")
            st.markdown("Generates a comprehensive 20-question exam for any subject to test your mastery.")

            subject = st.text_input("Enter Subject / Course Name", placeholder="e.g. Python Programming, Linear Algebra")
            
            if 'assessment_quiz' not in st.session_state:
                st.session_state['assessment_quiz'] = None
                st.session_state['assessment_answers'] = {}
            
            if st.button("Generate Assessment"):
                if subject:
                    with st.spinner(f"AI is designing a syllabus-wide exam for {subject}..."):
                        try:
                            resp = requests.post(f"{API_URL}/assessment/generate", json={"subject": subject})
                            if resp.status_code == 200:
                                st.session_state['assessment_quiz'] = resp.json()
                                st.session_state['assessment_answers'] = {} # Reset answers
                            else:
                                st.error("Failed to generate assessment. Try again.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please enter a subject.")

            # Display Quiz
            quiz_data = st.session_state.get('assessment_quiz')
            if quiz_data:
                questions = quiz_data.get('questions', [])
                st.divider()
                st.subheader(f"📝 Exam: {subject}")
                
                with st.form("assessment_form"):
                    for idx, q in enumerate(questions):
                        # Use .get with safe fallbacks
                        q_id = q.get('id', idx + 1)
                        q_text = q.get('text', 'Question text missing')
                        q_options = q.get('options', [])
                        if not q_options: q_options = ["Yes", "No"] # Fallback

                        st.markdown(f"**{idx+1}. {q_text}**")
                        
                        # Unique key: "am_q_" + loop_index
                        # We map loop_index -> q_id for answers
                        ans = st.radio(f"Select Answer for Q{idx+1}", q_options, key=f"am_q_{idx}")
                        st.session_state['assessment_answers'][q_id] = ans
                        st.write("---")
                    
                    submitted = st.form_submit_button("Submit Assessment")
                    
                    if submitted:
                        score = 0
                        incorrect_topics = []
                        total = len(questions)
                        
                        for idx, q in enumerate(questions):
                            q_id = q.get('id', idx + 1)
                            # Retrieve answer using the q_id we stored
                            user_ans = st.session_state['assessment_answers'].get(q_id)
                            
                            correct_idx = int(q.get('correct_index', 0))
                            options = q.get('options', [])
                            
                            correct_ans = None
                            if options and 0 <= correct_idx < len(options):
                                correct_ans = options[correct_idx]
                                
                            if user_ans and user_ans == correct_ans:
                                score += 1
                            else:
                                incorrect_topics.append(q.get('topic', 'General'))
                        
                        st.session_state['assessment_result'] = {
                            "score": score,
                            "total": total,
                            "incorrect_topics": incorrect_topics,
                            "subject": subject
                        }

                # Show Results if submitted
                if 'assessment_result' in st.session_state:
                    res = st.session_state['assessment_result']
                    st.divider()
                    st.subheader("📊 Results Analysis")
                    
                    col1, col2 = st.columns(2)
                    col1.metric("Final Score", f"{res['score']} / {res['total']}")
                    percentage = (res['score'] / res['total']) * 100
                    col2.metric("Percentage", f"{percentage:.1f}%")
                    
                    if st.button("Get AI Analysis & Study Plan"):
                         with st.spinner("AI is grading your exam and writing a study plan..."):
                            try:
                                payload = {
                                    "subject": res['subject'],
                                    "score": res['score'],
                                    "total": res['total'],
                                    "incorrect_topics": res['incorrect_topics']
                                }
                                analysis_resp = requests.post(f"{API_URL}/assessment/analyze", json=payload)
                                if analysis_resp.status_code == 200:
                                    report = analysis_resp.json()
                                    
                                    # Render Report
                                    verdict_color = "green" if report['verdict'] == "Good" else "orange" if report['verdict'] == "Average" else "red"
                                    st.markdown(f"### Verdict: :{verdict_color}[{report['verdict']}]")
                                    st.info(report['feedback'])
                                    
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        st.markdown("### 🔴 Topics to Study")
                                        for t in report['study_plan']:
                                            st.write(f"- {t}")
                                    with c2:
                                        st.markdown("### 🟢 Mastered Topics")
                                        for t in report['mastered_topics']:
                                            st.write(f"- {t}")
                                    
                                else:
                                    st.error("Failed to get analysis.")
                            except Exception as e:
                                st.error(f"Connection Error: {e}")

    # --- INSTRUCTOR PORTAL ---
    elif role == "instructor":
        st.sidebar.header("Admin Controls")
        page = st.sidebar.radio("Go to:", ["Student Overview", "Question Bank", "Drift Monitoring"])
        
        if page == "Student Overview":
            st.title("👨‍🏫 Student Analytics")
            students = get_all_students()
            df = pd.DataFrame(students)
            st.dataframe(df, use_container_width=True)
            
            st.write("Select a student ID to view detail:")
            sid = st.number_input("Student ID", min_value=1, step=1)
            if st.button("View Dashboard"):
                s_data = get_student_data(sid)
                if s_data:
                    st.success(f"Viewing data for {s_data['student']}")
                    st.json(s_data) # Simple view for instructor
                else:
                    st.error("Student not found")

        elif page == "Question Bank":
            st.title("📝 Question Management")
            
            tab_view, tab_add = st.tabs(["View Questions", "Add Question"])
            
            with tab_view:
                qs = get_all_questions()
                if qs:
                    st.dataframe(pd.DataFrame(qs)[['id', 'text', 'topic_id', 'difficulty']], use_container_width=True)
                else:
                    st.info("No questions in bank.")

            with tab_add:
                st.subheader("Create New Question")
                q_text = st.text_input("Question Text")
                
                c1, c2 = st.columns(2)
                with c1:
                    op1 = st.text_input("Option 1")
                    op2 = st.text_input("Option 2")
                with c2:
                    op3 = st.text_input("Option 3")
                    op4 = st.text_input("Option 4")
                
                correct = st.selectbox("Correct Option", ["Option 1", "Option 2", "Option 3", "Option 4"])
                corr_idx = ["Option 1", "Option 2", "Option 3", "Option 4"].index(correct)
                
                topics = get_all_topics()
                t_map = {t['id']: t['name'] for t in topics}
                tid = st.selectbox("Topic", list(t_map.keys()), format_func=lambda x: t_map[x])
                
                diff = st.slider("Difficulty", 0.0, 1.0, 0.5)
                
                if st.button("Save Question"):
                    if create_question_api(tid, q_text, [op1, op2, op3, op4], corr_idx, diff):
                        st.success("Question created!")
                    else:
                        st.error("Failed.")

        elif page == "Drift Monitoring":
            st.title("📉 System Drift Events")
            # Reuse logic
            resp = requests.get(f"{API_URL}/drifts/all")
            if resp.status_code == 200:
                st.dataframe(pd.DataFrame(resp.json()), use_container_width=True)
