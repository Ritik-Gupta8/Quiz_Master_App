from flask import render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required
from datetime import datetime, date
from models.models import db, Subject, Quiz, User, Question, QuizAttempt, Score, UserQuota
from routes.utils import role_required
from services.ai_service import generate_quiz_questions


DEFAULT_SUBJECTS = ["Physics", "Mathematics", "General Knowledge", "Chemistry", "Biology", "English"]
MAX_QUIZ_ATTEMPTS = 3

def init_user_routes(app):
    @app.route("/user")
    @login_required
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
        # --- Scalable Quota & Rate Limiting Logic ---
        quota = UserQuota.query.filter_by(user_id=current_user.id).first()
        if not quota:
            quota = UserQuota(user_id=current_user.id, daily_count=0, last_reset_date=date.today())
            db.session.add(quota)
            db.session.flush()

        # 1. Midnight Reset Check
        if quota.last_reset_date and quota.last_reset_date < date.today():
            quota.daily_count = 0
            quota.last_reset_date = date.today()

        # 2. Hard Daily Limit Check (Max 2 per day)
        if quota.daily_count >= 2:
            flash("You have exhausted your daily limit of 2 quizzes. Please try again tomorrow, or explore quizzes created by others!", "error")
            return redirect(url_for("user_dashboard"))

        # 3. 10-Minute Gen Cooldown Interval Check (600 seconds)
        if quota.last_request_time:
            time_since_last = (datetime.now() - quota.last_request_time).total_seconds()
            if time_since_last < 600:
                minutes_left = int((600 - time_since_last) // 60)
                flash(f"You can generate another quiz in {minutes_left + 1} minutes.", "error")
                return redirect(url_for("user_dashboard"))
        # --------------------------------------------

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

        # Mutate Quota safely alongside everything
        quota.daily_count += 1
        quota.last_request_time = datetime.now()

        db.session.commit()
        flash("Quiz generated successfully! Navigate to 'My Quizzes' to attempt it.", "success")
        return redirect(url_for("user_dashboard"))

    @app.route("/my_quizzes")
    @role_required("user")
    def my_quizzes():
        quizzes = Quiz.query.filter_by(creator_id=current_user.id).order_by(Quiz.id.desc()).all()
        maxed_quizzes_ids = []
        for quiz in quizzes:
            attempts_count = QuizAttempt.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()
            if attempts_count >= MAX_QUIZ_ATTEMPTS:
                maxed_quizzes_ids.append(quiz.id)

        dt_time_now = date.today()
        return render_template("my_quizzes.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now, maxed_quizzes_ids=maxed_quizzes_ids)

    @app.route("/explore_quizzes")
    @role_required("user")
    def explore_quizzes():
        # Filter out quizzes created by the current user
        base_quizzes = Quiz.query.filter(Quiz.creator_id != current_user.id).order_by(Quiz.id.desc()).all()
        
        # Filter out quizzes where the user has exhausted their attempts
        available_quizzes = []
        for quiz in base_quizzes:
            attempts_count = QuizAttempt.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()
            if attempts_count < MAX_QUIZ_ATTEMPTS:
                available_quizzes.append(quiz)
                
        dt_time_now = date.today()
        return render_template("explore_quizzes.html", user=current_user, quizzes=available_quizzes, dt_time_now=dt_time_now)

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
                user_scores = [s for s in u.scores if s.quiz.subject_id == subject.id]
                xp = u.calculate_xp(subject.id)
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

    @app.route("/user_search", methods=["GET", "POST"])
    @role_required("user")
    def search_user():
        if request.method == "POST":
            search_txt = request.form.get("search_txt")
            if not search_txt:  
                return redirect(url_for("user_dashboard"))
            
            # Expanded User Search: matches quiz topic, subject name, difficulty, grade, or creator's name
            search_pattern = f"%{search_txt}%"
            
            # Simple scoring match
            try:
                score_value = int(search_txt)
                scores = Score.query.filter_by(user_id=current_user.id, total_score=score_value).all()
                if scores:
                    return render_template("view_score.html", user=current_user, scores=scores, quizzes=Quiz.query.all())
            except ValueError:
                pass

            # Keyword matches inside Quizzes table directly
            matched_quizzes = Quiz.query.join(Subject).filter(
                db.or_(
                    Quiz.topic.ilike(search_pattern),
                    Subject.name.ilike(search_pattern),
                    Quiz.difficulty.ilike(search_pattern)
                )
            ).order_by(Quiz.id.desc()).all()
            
            # Find Users by Name & compute their global rank/xp
            matched_users_db = User.query.filter(User.role == 1, User.full_name.ilike(search_pattern)).all()
            matched_user_data = []
            
            if matched_users_db:
                all_users = User.query.filter_by(role=1).all()
                global_rankings = []
                # Compute global XP for everyone to establish ranks
                for u in all_users:
                    xp = u.calculate_xp()
                        
                    global_rankings.append({
                        "user": u,
                        "xp": xp
                    })
                
                global_rankings.sort(key=lambda x: x["xp"], reverse=True)
                
                matched_user_ids = [u.id for u in matched_users_db]
                for idx, entry in enumerate(global_rankings):
                    if entry["user"].id in matched_user_ids:
                        matched_user_data.append({
                            "user": entry["user"],
                            "xp": entry["xp"],
                            "rank": idx + 1
                        })
            
            return render_template("user_search_results.html", user=current_user, quizzes=matched_quizzes, matched_users=matched_user_data, search_query=search_txt, dt_time_now=date.today())
            
        return redirect(url_for("user_dashboard"))
