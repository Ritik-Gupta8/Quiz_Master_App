from sqlalchemy import func
from models.models import db, Quiz, QuizAttempt, Score, Subject, User

def get_admin_summary_data():
    """Aggregates all global app data for the Admin Dashboard."""
    total_quizzes = Quiz.query.count()
    active_users = User.query.filter(User.role == 1).count()
    
    avg_score = db.session.query(
        func.avg(Score.total_score * 100.0 / Quiz.no_of_questions)
    ).select_from(Score).join(Quiz, Score.quiz_id == Quiz.id).scalar() or 0
    
    # Subject-wise Performance
    subjects = Subject.query.all()
    subject_performance = []
    for s in subjects:
        avg = db.session.query(func.avg(Score.total_score * 100.0 / Quiz.no_of_questions))\
            .select_from(Score)\
            .join(Quiz, Score.quiz_id == Quiz.id)\
            .filter(Quiz.subject_id == s.id).scalar() or 0
        subject_performance.append({"name": s.name, "value": round(float(avg), 2)})
    
    # Difficulty-wise Performance
    difficulties = ["Easy", "Medium", "High"]
    difficulty_performance = []
    for d in difficulties:
        avg = db.session.query(func.avg(Score.total_score * 100.0 / Quiz.no_of_questions))\
            .select_from(Score)\
            .join(Quiz, Score.quiz_id == Quiz.id)\
            .filter(Quiz.difficulty == d).scalar() or 0
        difficulty_performance.append({"name": d, "value": round(float(avg), 2)})

    return {
        "total_quizzes": total_quizzes,
        "active_users": active_users,
        "avg_score": round(float(avg_score), 2),
        "subject_performance": subject_performance,
        "difficulty_performance": difficulty_performance
    }

def get_user_summary_data(user_id):
    """Aggregates a single user's data for their Dashboard Progress."""
    # 1. Quiz History (last 5)
    recent_attempts = QuizAttempt.query.filter_by(user_id=user_id, status="submitted")\
        .order_by(QuizAttempt.end_time.desc()).limit(5).all()
    quiz_history = []
    for a in recent_attempts:
        percentage = round((a.final_score / a.quiz.no_of_questions) * 100, 2) if a.quiz.no_of_questions else 0
        quiz_history.append({
            "quiz": a.quiz.formatted_topic,
            "score": percentage,
            "total": a.quiz.no_of_questions
        })
        
    # 2. Accuracy Trend (Percentage over last 10 attempts)
    trend_attempts = QuizAttempt.query.filter_by(user_id=user_id, status="submitted")\
        .order_by(QuizAttempt.end_time.asc()).limit(10).all()
    accuracy_trend = []
    for a in trend_attempts:
        accuracy = (a.final_score / a.quiz.no_of_questions) * 100
        accuracy_trend.append({
            "date": a.end_time.strftime("%d %b"),
            "value": round(accuracy, 2)
        })
        
    # 3. Score by Subject
    subjects = Subject.query.all()
    subject_scores = []
    for s in subjects:
        avg = db.session.query(func.avg(QuizAttempt.final_score * 100.0 / Quiz.no_of_questions))\
            .select_from(QuizAttempt)\
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)\
            .filter(QuizAttempt.user_id == user_id, Quiz.subject_id == s.id, QuizAttempt.status == "submitted").scalar() or 0
        subject_scores.append({"name": s.name, "value": round(float(avg), 2)})
        
    # 4. Time Spent (Average in minutes per attempt)
    time_data = []
    for a in trend_attempts:
        duration = (a.end_time - a.start_time).total_seconds() / 60.0
        time_data.append({
            "quiz": a.quiz.formatted_topic,
            "minutes": round(duration, 2)
        })

    return {
        "quiz_history": quiz_history,
        "accuracy_trend": accuracy_trend,
        "subject_scores": subject_scores,
        "time_data": time_data
    }
