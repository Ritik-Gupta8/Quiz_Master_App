from flask import Flask,render_template,request,url_for,redirect, session, flash, abort
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from models.models import *
from flask import current_app as app
from datetime import datetime,date,timedelta,timezone
from controllers.gemini_service import generate_quiz_questions
from sqlalchemy import func
import os
import json

# Default subjects always shown to users (merged with DB subjects)
DEFAULT_SUBJECTS = ["Physics", "Mathematics", "General Knowledge", "Chemistry", "Biology", "English"]

def role_required(role_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("signin"))
            
            # 0 for Admin, 1 for User
            role_map = {"admin": 0, "user": 1}
            required_role = role_map.get(role_name)
            
            if current_user.role != required_role:
                flash("Access Denied: You do not have permission to view this page.", "danger")
                return redirect(url_for("home"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator



@app.route("/") 
def home():
    return render_template("index.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear() # Clear server-side session as well
    flash("You have been logged out.", "info")
    return redirect(url_for("signin"))

@app.route("/login",methods=["GET","POST"])
def signin():
    if current_user.is_authenticated:
        if current_user.role == 0:
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")

        usr=User.query.filter_by(email=uname).first()
        if not usr:
            flash("User not found. Please check your email or register a new account.", "danger")
            return render_template("login.html")
            
        if check_password_hash(usr.password, pwd):
            login_user(usr)
            if usr.role==0:
                return redirect(url_for("admin_dashboard"))
            elif usr.role==1:
                return redirect(url_for("user_dashboard")) 
        else:
            flash("Incorrect password. Please try again.", "danger")
            return render_template("login.html")

    return render_template("login.html")

@app.route("/register",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")
        full_name=request.form.get("full_name")
        qualification=request.form.get("qualification")
     
        usr=User.query.filter_by(email=uname).first()
        if usr:
            return render_template("register.html",msg="This email is already registered. Please log in or use a different email.")

        hashed_pwd = generate_password_hash(pwd, method='pbkdf2:sha256')
        new_usr=User(email=uname,password=hashed_pwd,full_name=full_name,qualification=qualification)
        db.session.add(new_usr)
        db.session.commit()
        return render_template("login.html",msg1="Thank you for registering! Try logging in now.")

    return render_template("register.html")

@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    subjects=get_subjects()
    return render_template("admin_dashboard.html", subjects=subjects)

@app.route('/user_details')
@role_required("admin")
def user_deatils():
    users = User.query.filter(User.role != 0).all()  
    return render_template('user_details.html', users=users)

@app.route("/subject",methods=["POST","GET"])
@role_required("admin")
def add_subject():
    if request.method=="POST":
        sname=request.form.get("name").strip()
        description=request.form.get("description")

        # Check for duplicate subject name (case-insensitive)
        existing = Subject.query.filter(Subject.name.ilike(sname)).first()
        if existing:
            flash(f"Subject '{existing.name}' already exists in the database!", "warning")
            return render_template("add_subject.html", subject_exists=True, existing_name=existing.name)

        new_subject=Subject(name=sname, description=description)
        db.session.add(new_subject)
        db.session.commit()
        flash(f"Subject '{sname}' added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_subject.html")



@app.route("/edit_subject/<id>",methods=["GET","POST"])
@role_required("admin")
def edit_subject(id):
    s=get_subject(id)
    if request.method=="POST":
        sname=request.form.get("sname")
        description=request.form.get("description")
        s.name=sname
        s.description=description
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    
    return render_template("edit_subject.html",subject=s)

@app.route("/delete_subject/<id>",methods=["GET","POST"])
@role_required("admin")
def delete_subject(id):
    s=get_subject(id)
    if s:
        db.session.delete(s)
        db.session.commit()
    return redirect(url_for("admin_dashboard"))



@app.route("/quiz_management")
@role_required("admin")
def quiz_management():
    quizzes = Quiz.query.all()
    return render_template("quiz_management.html", quizzes=quizzes)




@app.route("/edit_quiz/<id>",methods=["GET","POST"])
@role_required("admin")
def edit_quiz(id):
    q=get_quiz(id)
   
    if request.method=="POST":
        sid = request.form.get("subject_id")
        topic = request.form.get("topic", "General Topic")
        date_of_quiz = request.form.get("date_of_quiz")
        date = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
        time_duration = request.form.get("time_duration")
        no_of_questions = request.form.get("no_of_questions")
        q.subject_id=sid
        q.topic=topic
        q.date_of_quiz=date
        q.time_duration=time_duration
        q.no_of_questions=no_of_questions
        q.difficulty=request.form.get("difficulty", "Medium")
        db.session.commit()
        return redirect(url_for("quiz_management"))
    
    subjects = Subject.query.all()
    return render_template("edit_quiz.html",quiz=q,subjects=subjects)

@app.route("/delete_quiz/<id>", methods=["GET", "POST"])
@role_required("admin")
def delete_quiz(id):  
    q = get_quiz(id)
    if q:
        db.session.delete(q)
        db.session.commit()
    return redirect(url_for("quiz_management"))



@app.route("/generate_ai_quiz", methods=["GET", "POST"])
@role_required("admin")
def generate_ai_quiz():
    # Difficulty → (num_questions, time_duration)
    DIFFICULTY_CONFIG = {
        "Easy":   (5,  "00:05"),
        "Medium": (10, "00:10"),
        "High":   (15, "00:15"),
    }

    if request.method == "POST":
        subject_name = request.form.get("subject_name", "").strip()
        subject_id = request.form.get("subject_id", "").strip()
        level = request.form.get("level", "Medium")
        grade = request.form.get("grade", "10th")

        # Auto-configure based on difficulty
        num_questions, time_duration = DIFFICULTY_CONFIG.get(level, (10, "00:10"))
        topic = f"AI Quiz ({grade} Grade)"

        # Resolve subject: if subject_id provided use it, else find/create by name
        if subject_id:
            subject = Subject.query.get_or_404(subject_id)
        elif subject_name:
            subject = Subject.query.filter(Subject.name.ilike(subject_name)).first()
            if not subject:
                subject = Subject(name=subject_name, description=f"AI Generated Subject for {subject_name}")
                db.session.add(subject)
                db.session.flush()
        else:
            flash("Please select or enter a subject.", "error")
            return redirect(url_for("generate_ai_quiz"))

        # Call Gemini AI
        results = generate_quiz_questions(subject.name, "General Topics", num_questions, level, grade)

        if isinstance(results, dict) and "error" in results:
            flash(f"AI Generation Failed: {results['error']}", "error")
            return redirect(url_for("generate_ai_quiz"))

        # Create a new Quiz
        new_quiz = Quiz(
            subject_id=subject.id,
            creator_id=current_user.id,
            topic=topic,
            date_of_quiz=date.today(),
            no_of_questions=len(results),
            time_duration=time_duration,
            difficulty=level
        )
        db.session.add(new_quiz)
        db.session.flush()

        # Add questions
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
        flash(f"Quiz generated for {subject.name} ({level}) — {len(results)} questions, {time_duration} duration!", "success")
        return redirect(url_for("quiz_management"))

    # Merge default subjects with DB subjects (avoid duplicates)
    db_subjects = Subject.query.all()
    db_subject_names_lower = {s.name.lower() for s in db_subjects}
    extra_defaults = [s for s in DEFAULT_SUBJECTS if s.lower() not in db_subject_names_lower]
    has_api_key = os.environ.get("GOOGLE_API_KEY") is not None
    return render_template("generate_ai_quiz.html", subjects=db_subjects, default_subjects=extra_defaults, has_api_key=has_api_key)

@app.route("/user_generate_ai_quiz", methods=["POST"])
@role_required("user")
def user_generate_ai_quiz():
    # Difficulty → (num_questions, time_duration)
    DIFFICULTY_CONFIG = {
        "Easy":   (5,  "00:05"),
        "Medium": (10, "00:10"),
        "High":   (15, "00:15"),
    }

    grade = request.form.get("grade", "10th")
    subject_name = request.form.get("subject", "General Knowledge").strip()
    difficulty = request.form.get("difficulty", "Medium")

    num_questions, duration = DIFFICULTY_CONFIG.get(difficulty, (10, "00:10"))

    # Find or create subject
    subject = Subject.query.filter(Subject.name.ilike(subject_name)).first()
    if not subject:
        subject = Subject(name=subject_name, description=f"AI Generated Subject for {subject_name}")
        db.session.add(subject)
        db.session.flush()

    topic = f"AI Practice ({grade} Grade)"

    # Generate questions with grade context
    results = generate_quiz_questions(subject.name, "General Topics", num_questions, difficulty, grade)

    if isinstance(results, dict) and "error" in results:
        flash(f"AI Generation Failed: {results['error']}", "error")
        return redirect(url_for("user_dashboard"))

    # Create the Quiz
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

    # Add Questions
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

@app.route("/search", methods=["GET", "POST"])
@role_required("admin")
def search():
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        if not search_txt:  
            return redirect(url_for("admin_dashboard"))
        by_user = search_by_user(search_txt)
        by_subject = search_by_subject(search_txt)
        by_quiz = search_by_quiz(search_txt)
        if by_user:
            return render_template("user_details.html", users=by_user)
        elif by_subject:
            return render_template("admin_dashboard.html", subjects=by_subject)
        elif by_quiz:
            return render_template("quiz_management.html", quizzes=by_quiz)
    return redirect(url_for("admin_dashboard"))

def search_by_user(search_txt):
    users = User.query.filter(User.full_name.ilike(f"%{search_txt}%")).all()
    return users

def search_by_subject(search_txt):
    subjects=Subject.query.filter(Subject.name.ilike(f"%{search_txt}%")).all()
    return subjects

def search_by_quiz(search_txt):
    quizzes = Quiz.query.join(Subject).filter(Subject.name.ilike(f"%{search_txt}%")).all()
    return quizzes

@app.route("/admin_summary")
@role_required("admin")
def admin_summary():
    # 1. Quizzes Created
    total_quizzes = Quiz.query.count()
    
    # 2. Active Users (Students)
    active_users = User.query.filter(User.role == 1).count()
    
    # 3. Average Score
    avg_score = db.session.query(func.avg(Score.total_score)).scalar() or 0
    
    # 4. Subject-wise Performance
    subjects = Subject.query.all()
    subject_performance = []
    for s in subjects:
        # Calculate average percentage score for this subject
        avg = db.session.query(func.avg(Score.total_score * 100.0 / Quiz.no_of_questions))\
            .join(Quiz, Score.quiz_id == Quiz.id)\
            .filter(Quiz.subject_id == s.id).scalar() or 0
        subject_performance.append({"name": s.name, "value": round(float(avg), 2)})
    
    # 5. Difficulty-wise Performance
    difficulties = ["Easy", "Medium", "High"]
    difficulty_performance = []
    for d in difficulties:
        avg = db.session.query(func.avg(Score.total_score * 100.0 / Quiz.no_of_questions))\
            .join(Quiz, Score.quiz_id == Quiz.id)\
            .filter(Quiz.difficulty == d).scalar() or 0
        difficulty_performance.append({"name": d, "value": round(float(avg), 2)})

    data = {
        "total_quizzes": total_quizzes,
        "active_users": active_users,
        "avg_score": round(float(avg_score), 2),
        "subject_performance": subject_performance,
        "difficulty_performance": difficulty_performance
    }
    
    return render_template("admin_summary.html", data=data)

@app.route("/user")
@role_required("user")
def user_dashboard():
    quizzes = Quiz.query.filter_by(creator_id=current_user.id).all()
    dt_time_now = date.today()
    # Merge DB subjects with default subjects for the quiz generator dropdown
    db_subjects = Subject.query.all()
    db_subject_names_lower = {s.name.lower() for s in db_subjects}
    extra_defaults = [s for s in DEFAULT_SUBJECTS if s.lower() not in db_subject_names_lower]
    return render_template("user_dashboard.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now, db_subjects=db_subjects, default_subjects=extra_defaults)

@app.route("/explore_quizzes")
@role_required("user")
def explore_quizzes():
    quizzes = Quiz.query.all()
    dt_time_now = date.today()
    return render_template("explore_quizzes.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now)

MAX_QUIZ_ATTEMPTS = 3

@app.route("/start_quiz/<qid>")
@role_required("user")
def start_quiz(qid):
    quiz = Quiz.query.get_or_404(qid)
    questions = Question.query.filter_by(quiz_id=qid).all()

    # Check all attempts for this user+quiz
    all_attempts = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).all()
    completed_attempts = [a for a in all_attempts if a.status in ["submitted", "expired"]]
    active_attempt = next((a for a in all_attempts if a.status == "in_progress"), None)

    if active_attempt:
        # Resume existing in-progress attempt
        end_time_str = active_attempt.end_time.isoformat()
        current_answers = json.loads(active_attempt.answers)
        attempt_num = len(completed_attempts) + 1
        return render_template("start_quiz.html", user=current_user, quiz=quiz, questions=questions,
                               end_time=end_time_str, current_answers=current_answers,
                               attempt_num=attempt_num, max_attempts=MAX_QUIZ_ATTEMPTS)

    # No active attempt — check if limit reached
    if len(completed_attempts) >= MAX_QUIZ_ATTEMPTS:
        flash(f"You have reached the maximum of {MAX_QUIZ_ATTEMPTS} attempts for this quiz.", "warning")
        return redirect(url_for("view_score"))

    # Create new attempt
    hours, minutes = map(int, quiz.time_duration.split(":"))
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(hours=hours, minutes=minutes)

    attempt = QuizAttempt(
        quiz_id=qid,
        user_id=current_user.id,
        status="in_progress",
        start_time=start_time,
        end_time=end_time,
        answers="{}"
    )
    db.session.add(attempt)
    db.session.commit()

    end_time_str = end_time.isoformat()
    current_answers = {}
    attempt_num = len(completed_attempts) + 1

    return render_template("start_quiz.html", user=current_user, quiz=quiz, questions=questions,
                           end_time=end_time_str, current_answers=current_answers,
                           attempt_num=attempt_num, max_attempts=MAX_QUIZ_ATTEMPTS)

@app.route("/save_answer/<qid>", methods=["POST"])
@role_required("user")
def save_answer(qid):
    data = request.get_json()
    question_id = str(data.get("question_id"))
    selected_option = data.get("selected_option")

    # Always use the latest in_progress attempt
    attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()

    if not attempt:
        return json.dumps({"success": False, "error": "No active attempt found"}), 403

    if datetime.now(timezone.utc) > attempt.end_time.replace(tzinfo=timezone.utc):
        attempt.status = "expired"
        db.session.commit()
        return json.dumps({"success": False, "error": "Quiz time has expired"}), 403

    answers = json.loads(attempt.answers)
    answers[question_id] = selected_option
    attempt.answers = json.dumps(answers)
    db.session.commit()

    return json.dumps({"success": True})

@app.route("/submit_quiz/<qid>", methods=["POST"])
@role_required("user")
def submit_quiz(qid):
    quiz = Quiz.query.get_or_404(qid)
    # Get the latest in_progress attempt
    attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()

    if not attempt:
        flash("No active quiz attempt found.", "danger")
        return redirect(url_for("user_dashboard"))

    # Final time check (allow 10 second buffer)
    if datetime.now(timezone.utc) > attempt.end_time.replace(tzinfo=timezone.utc) + timedelta(seconds=10):
        attempt.status = "expired"
        flash("Submission failed: Time has expired.", "danger")
    else:
        attempt.status = "submitted"

    # Merge form answers with stored answers (form takes precedence for the final submit)
    questions = Question.query.filter_by(quiz_id=qid).all()
    stored_answers = json.loads(attempt.answers)

    final_answers = {}
    for q in questions:
        val = request.form.get(f"answer_{q.id}") or stored_answers.get(str(q.id))
        final_answers[str(q.id)] = val

    attempt.answers = json.dumps(final_answers)

    # Calculate score
    total_score = 0
    for q in questions:
        if final_answers.get(str(q.id)) == getattr(q, q.correct_option):
            total_score += 1

    attempt.final_score = total_score

    # Always INSERT a new Score row — we keep ALL attempts.
    # The view_score page will find and display the HIGHEST score.
    timestamp = datetime.now()
    new_score = Score(quiz_id=quiz.id, user_id=current_user.id, total_score=total_score, timestamp=timestamp)
    db.session.add(new_score)

    db.session.commit()

    # Count completed attempts for feedback
    completed_count = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).filter(
        QuizAttempt.status.in_(["submitted", "expired"])).count()
    remaining = MAX_QUIZ_ATTEMPTS - completed_count

    # Tell user their score and remaining attempts
    all_scores_for_quiz = Score.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).all()
    best = max(all_scores_for_quiz, key=lambda s: s.total_score)
    if remaining > 0:
        flash(f"Attempt {completed_count}/{MAX_QUIZ_ATTEMPTS} done! Score: {total_score}/{quiz.no_of_questions}. "
              f"Best so far: {best.total_score}/{quiz.no_of_questions}. {remaining} attempt(s) remaining.", "success")
    else:
        flash(f"All {MAX_QUIZ_ATTEMPTS} attempts used! Final score: {total_score}/{quiz.no_of_questions}. "
              f"Best score: {best.total_score}/{quiz.no_of_questions}.", "info")

    return redirect(url_for("view_score"))

@app.route("/view_score")
@role_required("user")
def view_score():
    # Get ALL score rows for this user
    all_scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.timestamp.asc()).all()

    # Group by quiz_id — keep the BEST (highest) score per quiz for display
    best_score_map = {}       # quiz_id -> Score object with highest total_score
    all_scores_by_quiz = {}   # quiz_id -> list of all Score objects (for history)
    for score in all_scores:
        all_scores_by_quiz.setdefault(score.quiz_id, []).append(score)
        if score.quiz_id not in best_score_map or score.total_score > best_score_map[score.quiz_id].total_score:
            best_score_map[score.quiz_id] = score

    quiz_ids = list(best_score_map.keys())
    best_scores = list(best_score_map.values())
    quizzes = Quiz.query.filter(Quiz.id.in_(quiz_ids)).all() if quiz_ids else []
    dt_time_now = datetime.now().date()

    # Build attempt counts per quiz
    attempt_counts = {}
    for qid in quiz_ids:
        attempt_counts[qid] = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).filter(
            QuizAttempt.status.in_(["submitted", "expired"])).count()

    return render_template("view_score.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now,
                           scores=best_scores, attempt_counts=attempt_counts, max_attempts=MAX_QUIZ_ATTEMPTS,
                           all_scores_by_quiz=all_scores_by_quiz)

@app.route("/review_quiz/<qid>")
@role_required("user")
def review_quiz(qid):
    quiz = Quiz.query.get_or_404(qid)
    
    # Verify user has completed max attempts
    all_attempts = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).all()
    completed_attempts = [a for a in all_attempts if a.status in ["submitted", "expired"]]
    
    if len(completed_attempts) < MAX_QUIZ_ATTEMPTS:
        flash("You can only review answers after using all your attempts.", "warning")
        return redirect(url_for("view_score"))
        
    # Get the latest attempt
    latest_attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="submitted").order_by(QuizAttempt.end_time.desc()).first()
    
    if not latest_attempt:
        latest_attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="expired").order_by(QuizAttempt.end_time.desc()).first()
        
    if not latest_attempt:
        flash("No completed attempts found to review.", "warning")
        return redirect(url_for("view_score"))
        
    questions = Question.query.filter_by(quiz_id=qid).all()
    answers = json.loads(latest_attempt.answers)
    
    return render_template("review_quiz.html", user=current_user, quiz=quiz, questions=questions, answers=answers, attempt=latest_attempt)

@app.route("/user_search", methods=["GET", "POST"])
@role_required("user")
def search_user():
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        if not search_txt:  
            return redirect(url_for("user_dashboard"))
        subject_by_score = search_subject_by_score(search_txt, current_user.id) 
        if subject_by_score:
            return render_template("view_score.html", user=current_user, scores=subject_by_score, quizzes=Quiz.query.all())
    return redirect(url_for("user_dashboard"))

def search_subject_by_score(search_txt, user_id):
    try:
        score_value = int(search_txt)  
    except ValueError:
        return []
    scores = Score.query.filter_by(user_id=user_id, total_score=score_value).all()
    return scores

@app.route("/user_summary")
@role_required("user")
def user_summary():
    user_id = current_user.id
    
    # 1. Quiz History (last 5)
    recent_attempts = QuizAttempt.query.filter_by(user_id=user_id, status="submitted")\
        .order_by(QuizAttempt.end_time.desc()).limit(5).all()
    quiz_history = []
    for a in recent_attempts:
        quiz_history.append({
            "quiz": a.quiz.topic,
            "score": a.final_score,
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
            .join(Quiz, QuizAttempt.quiz_id == Quiz.id)\
            .filter(QuizAttempt.user_id == user_id, Quiz.subject_id == s.id, QuizAttempt.status == "submitted").scalar() or 0
        subject_scores.append({"name": s.name, "value": round(float(avg), 2)})
        
    # 4. Time Spent (Average in minutes per attempt)
    time_data = []
    for a in trend_attempts:
        duration = (a.end_time - a.start_time).total_seconds() / 60.0
        time_data.append({
            "quiz": a.quiz.topic,
            "minutes": round(duration, 2)
        })

    data = {
        "quiz_history": quiz_history,
        "accuracy_trend": accuracy_trend,
        "subject_scores": subject_scores,
        "time_data": time_data
    }
    
    return render_template("user_summary.html", user=current_user, data=data)

def get_subjects():
    subjects=Subject.query.all()
    return subjects

def get_subject(id):
    subject=Subject.query.filter_by(id=id).first()
    return subject



def get_quiz(id):
    quiz=Quiz.query.filter_by(id=id).first()
    return quiz


