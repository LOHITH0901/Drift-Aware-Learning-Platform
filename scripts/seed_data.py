from sqlalchemy.orm import Session
from backend.db import SessionLocal, engine, Base
from backend.models import Student, Instructor, Topic, Resource, Question
from backend.auth import get_password_hash

def seed_data():
    # DROP ALL TABLES to apply new schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    print("Seeding database with new schema...")

    # Topics
    topics = [
        Topic(name="Algebra", default_p_init=0.4),
        Topic(name="Data Science", default_p_init=0.3),
        Topic(name="History", default_p_init=0.5)
    ]
    db.add_all(topics)
    db.commit()

    # Resources
    r1 = Resource(title="Algebra Basics", content="Intro to variables.", topic_id=topics[0].id, difficulty=0.2)
    r2 = Resource(title="Python Series", content="Pandas and Numpy.", topic_id=topics[1].id, difficulty=0.4)
    db.add_all([r1, r2])

    # Questions (Real data for new Study Zone)
    questions = [
        Question(
            topic_id=topics[0].id,
            text="What is x if 2x + 4 = 10?",
            options=["2", "3", "4", "5"],
            correct_index=1, # "3"
            difficulty=0.3
        ),
        Question(
            topic_id=topics[0].id,
            text="Solve for y: y = x^2 where x=3",
            options=["6", "9", "12", "30"],
            correct_index=1, # "9"
            difficulty=0.4
        ),
        Question(
            topic_id=topics[1].id,
            text="Which library is used for DataFrames?",
            options=["Numpy", "Pandas", "Matplotlib", "Seaborn"],
            correct_index=1, # "Pandas"
            difficulty=0.2
        )
    ]
    db.add_all(questions)

    # Users
    hashed_pwd = get_password_hash("password123")
    
    # Students
    s1 = Student(username="student1", password_hash=hashed_pwd, name="Alice Student")
    s2 = Student(username="student2", password_hash=hashed_pwd, name="Bob Learner")
    
    # Instructors
    i1 = Instructor(username="admin", password_hash=hashed_pwd, name="Dr. Smith")
    
    db.add_all([s1, s2, i1])
    db.commit()
    
    print("Seeding complete.")
    print("Users: student1/password123, student2/password123")
    print("Instructor: admin/password123")
    db.close()

if __name__ == "__main__":
    seed_data()
