# 🎓 Drift-Aware Adaptive Learning Platform

> **A Smart Learning System that Adapts to You!** 🚀  
> This platform uses Artificial Intelligence to create personalized quizzes, track your learning progress, and detect when you are forgetting topics (Concept Drift).

---

## 🟢 Quick Start (The Easy Way)
Follow these simple steps to run the project on your Mac.

### 1. Prerequisites
Before you start, make sure you have these installed:
- **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
- **Ollama**: This powers the AI. [Download & Install](https://ollama.com/)
  - *After installing, open your terminal and run:* `ollama run phi3:mini`

### 2. Setup
Open your terminal in this folder and run:
```bash
chmod +x setup.sh start.sh
./setup.sh
```
*This will install all necessary libraries for you.*

### 3. Run the App
To start the platform, simply run:
```bash
./start.sh
```
This will automatically:
1. Start the Brain (Backend Server)
2. Open the App (Frontend Dashboard) in your browser.

---

## 🎮 How to Use
1. **Login**:
   - **Student**: username `student`, password `student`
   - **Instructor**: username `admin`, password `admin`
2. **Take a Quiz**: Go to **Course Assessment**, type a subject (e.g., "Python Basics"), and click Generate.
3. **View Progress**: Check your Dashboard to see your mastery scores.

---

## 🛠️ For Developers (Manual Run)
If you prefer running commands manually:

**Backend:**
```bash
python3 -m uvicorn backend.main:app --reload
```

**Frontend:**
```bash
python3 -m streamlit run frontend/app.py
```

---

## 🤖 Tech Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **AI**: Ollama (Phi-3 Mini)
- **Database**: SQLite
- **Learning Algorithms**: River (Online Machine Learning), BKT (Bayesian Knowledge Tracing)

---
*Created by LOHITH0901*
