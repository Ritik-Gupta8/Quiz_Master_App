from flask import render_template, request, url_for, redirect, flash
from flask_login import current_user
from datetime import datetime, date
from models.models import db, Subject, Quiz, User, Question, QuizAttempt, Score
from routes.utils import role_required
from services.ai_service import generate_quiz_questions


DEFAULT_SUBJECTS = ["Physics", "Mathematics", "General Knowledge", "Chemistry", "Biology", "English"]
MAX_QUIZ_ATTEMPTS = 3

def init_user_routes(app):
    @app.route("/user")
    @role_required("user")
    def user_dashboard():
        dt_time_now = date.today()
        db_subjects = Subject.query.all()
        db_subject_names_lower = {s.name.lower() for s in db_subjects}
        extra_defaults = [s for s in DEFAULT_SUBJECTS if s.lower() not in db_subject_names_lower]
        return render_template("user_dashboard.html", user=current_user, dt_time_now=dt_time_now, db_subjects=db_subjects, default_subjects=extra_defaults)

    @app.route("/user_generate_ai_quiz", methods=["POST"])
    @role_required("user")
    def user_generate_ai_quiz():
        DIFFICULTY_CONFIG = {
            "Easy":   (5,  "00:05"),
            "Medium": (10, "00:10"),
            "High":   (15, "00:15"),
        }

        grade = request.form.get("grade", "10th")
        subject_name = request.form.get("subject", "General Knowledge").strip()
        difficulty = request.form.get("difficulty", "Medium")

        num_questions, duration = DIFFICULTY_CONFIG.get(difficulty, (10, "00:10"))

        subject = Subject.query.filter(Subject.name.ilike(subject_name)).first()
        if not subject:
            subject = Subject(name=subject_name, description=f"AI Generated Subject for {subject_name}")
            db.session.add(subject)
            db.session.flush()

        topic = f"AI Practice ({grade} Grade)"
        results = generate_quiz_questions(subject.name, "General Topics", num_questions, difficulty, grade)

        if isinstance(results, dict) and "error" in results:
            flash(f"AI Generation Failed: {results['error']}", "error")
            return redirect(url_for("user_dashboard"))

        new_quiz = Quiz(
            subject_id=subject.id,
            creator_id=current_user.id,
            topic=topic,
            date_of_quiz=date.today(),
            no_of_questions=len(results),
            time_duration=duration,
            difficulty=difficulty
        )
        db.session.add(new_quiz)
        db.session.flush()

        for q_data in results:
            new_question = Question(
                question_statement=q_data.get("question_statement"),
                question_type="MCQ",
                quiz_id=new_quiz.id,
                option1=q_data.get("option1"),
                option2=q_data.get("option2"),
                option3=q_data.get("option3"),
                option4=q_data.get("option4"),
                correct_option=q_data.get("correct_option")
            )
            db.session.add(new_question)

        db.session.commit()
        return redirect(url_for("start_quiz", qid=new_quiz.id))

    @app.route("/my_quizzes")
    @role_required("user")
    def my_quizzes():
        quizzes = Quiz.query.filter_by(creator_id=current_user.id).order_by(Quiz.id.desc()).all()
        dt_time_now = date.today()
        return render_template("my_quizzes.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now)

    @app.route("/explore_quizzes")
    @role_required("user")
    def explore_quizzes():
        quizzes = Quiz.query.order_by(Quiz.id.desc()).all()
        dt_time_now = date.today()
        return render_template("explore_quizzes.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now)

    @app.route("/completed_quizzes")
    @role_required("user")
    def completed_quizzes():
        all_quizzes = Quiz.query.order_by(Quiz.id.desc()).all()
        completed = []
        for quiz in all_quizzes:
            attempts_count = QuizAttempt.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()
            if attempts_count >= MAX_QUIZ_ATTEMPTS:
                completed.append(quiz)
                
        dt_time_now = date.today()
        return render_template("completed_quizzes.html", user=current_user, quizzes=completed, dt_time_now=dt_time_now)

    @app.route("/leaderboard")
    @role_required("user")
    def leaderboard():
        subjects = Subject.query.all()
        all_users = User.query.filter_by(role=1).all()
        
        subject_boards = []
        
        for subject in subjects:
            rankings = []
            for u in all_users:
                user_scores = db.session.query(Score).join(Quiz).filter(
                    Score.user_id == u.id,
                    Quiz.subject_id == subject.id
                ).all()
                
                xp = 0
                for s in user_scores:
                    multiplier = 1.0
                    if s.quiz.difficulty == 'Medium':
                        multiplier = 1.2
                    elif s.quiz.difficulty == 'High':
                        multiplier = 1.5
                    xp += int((s.total_score / s.quiz.no_of_questions) * 100 * multiplier) if s.quiz.no_of_questions else 0
                    
                if xp > 0:
                    rankings.append({
                        "user": u,
                        "xp": xp,
                        "quizzes_taken": len(user_scores)
                    })
                    
            rankings.sort(key=lambda x: x["xp"], reverse=True)
            
            user_rank = None
            user_entry = None
            for idx, entry in enumerate(rankings):
                if entry["user"].id == current_user.id:
                    user_rank = idx + 1
                    user_entry = entry
                    break
                    
            if rankings:
                subject_boards.append({
                    "subject": subject,
                    "top_three": rankings[:3],
                    "user_rank": user_rank,
                    "user_entry": user_entry
                })
                
        return render_template("leaderboard.html", user=current_user, subject_boards=subject_boards)

    @app.route("/search", methods=["GET", "POST"])
    @role_required("admin")
    def search():
        if request.method == "POST":
            search_txt = request.form.get("search_txt")
            if not search_txt:  
                return redirect(url_for("admin_dashboard"))
            
            by_user = User.query.filter(User.full_name.ilike(f"%{search_txt}%")).all()
            by_subject = Subject.query.filter(Subject.name.ilike(f"%{search_txt}%")).all()
            by_quiz = Quiz.query.join(Subject).filter(Subject.name.ilike(f"%{search_txt}%")).all()
            
            if by_user:
                return render_template("user_details.html", users=by_user)
            elif by_subject:
                return render_template("admin_dashboard.html", subjects=by_subject)
            elif by_quiz:
                return render_template("quiz_management.html", quizzes=by_quiz)
        return redirect(url_for("admin_dashboard"))

    @app.route("/user_search", methods=["GET", "POST"])
    @role_required("user")
    def search_user():
        if request.method == "POST":
            search_txt = request.form.get("search_txt")
            if not search_txt:  
                return redirect(url_for("user_dashboard"))
            try:
                score_value = int(search_txt)  
            except ValueError:
                return redirect(url_for("user_dashboard"))
                
            scores = Score.query.filter_by(user_id=current_user.id, total_score=score_value).all()
            if scores:
                return render_template("view_score.html", user=current_user, scores=scores, quizzes=Quiz.query.all())
        return redirect(url_for("user_dashboard"))
