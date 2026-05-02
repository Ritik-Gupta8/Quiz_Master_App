from flask import render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required
from datetime import datetime, date
import os
from models.models import db, Subject, Quiz, User, Question, QuizAttempt, UserQuota
from routes.utils import role_required
from services.ai_service import generate_quiz_questions

DEFAULT_SUBJECTS = ["Physics", "Mathematics", "General Knowledge", "Chemistry", "Biology", "English"]

def init_admin_routes(app):
    @app.route("/admin")
    @login_required
    @role_required("admin")
    def admin_dashboard():
        subjects = Subject.query.all()
        return render_template("admin_dashboard.html", subjects=subjects)

    @app.route('/user_details')
    @role_required("admin")
    def user_deatils():
        users = User.query.filter(User.role != 0).all()  
        return render_template('user_details.html', users=users)

    @app.route('/user_activity')
    @role_required("admin")
    def user_activity():
        users = User.query.filter(User.role != 0).all()
        activity_data = []

        for u in users:
            scores = u.scores
            total_xp = u.calculate_xp()
            
            subject_counts = {}
            for s in scores:
                subj_name = s.quiz.subject.name
                subject_counts[subj_name] = subject_counts.get(subj_name, 0) + 1
                
            breakdown = ", ".join([f"{subj} ({count})" for subj, count in subject_counts.items()])
            if not breakdown:
                breakdown = "No activity yet"

            activity_data.append({
                "user": u,
                "total_xp": total_xp,
                "total_attempts": len(scores),
                "breakdown": breakdown
            })

        # Sort by XP descending (highest XP top)
        activity_data.sort(key=lambda x: x["total_xp"], reverse=True)
        
        # Assign rank based on sorted list
        for idx, item in enumerate(activity_data):
            item["rank"] = idx + 1

        return render_template('user_activity.html', activity=activity_data)

    @app.route("/subject", methods=["POST", "GET"])
    @role_required("admin")
    def add_subject():
        if request.method == "POST":
            sname = request.form.get("name").strip()
            description = request.form.get("description")

            existing = Subject.query.filter(Subject.name.ilike(sname)).first()
            if existing:
                flash(f"Subject '{existing.name}' already exists in the database!", "warning")
                return render_template("add_subject.html", subject_exists=True, existing_name=existing.name)

            new_subject = Subject(name=sname, description=description)
            db.session.add(new_subject)
            db.session.commit()
            flash(f"Subject '{sname}' added successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        return render_template("add_subject.html")

    @app.route("/edit_subject/<id>", methods=["GET", "POST"])
    @role_required("admin")
    def edit_subject(id):
        s = Subject.query.filter_by(id=id).first()
        if request.method == "POST":
            s.name = request.form.get("sname")
            s.description = request.form.get("description")
            db.session.commit()
            return redirect(url_for("admin_dashboard"))
        
        return render_template("edit_subject.html", subject=s)

    @app.route("/delete_subject/<id>", methods=["GET", "POST"])
    @role_required("admin")
    def delete_subject(id):
        s = Subject.query.filter_by(id=id).first()
        if s:
            db.session.delete(s)
            db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.route("/quiz_management")
    @role_required("admin")
    def quiz_management():
        quizzes = Quiz.query.all()
        return render_template("quiz_management.html", quizzes=quizzes)



    @app.route("/delete_quiz/<id>", methods=["GET", "POST"])
    @role_required("admin")
    def delete_quiz(id):  
        q = Quiz.query.filter_by(id=id).first()
        if q:
            db.session.delete(q)
            db.session.commit()
        return redirect(url_for("quiz_management"))

    @app.route("/generate_ai_quiz", methods=["GET", "POST"])
    @role_required("admin")
    def generate_ai_quiz():
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

            num_questions, time_duration = DIFFICULTY_CONFIG.get(level, (10, "00:10"))
            topic = f"AI Quiz ({grade} Grade)"

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

            results = generate_quiz_questions(subject.name, "General Topics", num_questions, level, grade)

            if isinstance(results, dict) and "error" in results:
                flash(f"AI Generation Failed: {results['error']}", "error")
                return redirect(url_for("generate_ai_quiz"))

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

        db_subjects = Subject.query.all()
        db_subject_names_lower = {s.name.lower() for s in db_subjects}
        extra_defaults = [s for s in DEFAULT_SUBJECTS if s.lower() not in db_subject_names_lower]
        has_api_key = os.environ.get("GOOGLE_API_KEY") is not None
        return render_template("generate_ai_quiz.html", subjects=db_subjects, default_subjects=extra_defaults, has_api_key=has_api_key)

    @app.route("/search", methods=["GET", "POST"])
    @role_required("admin")
    def search():
        if request.method == "POST":
            search_txt = request.form.get("search_txt")
            if not search_txt:  
                return redirect(url_for("admin_dashboard"))
            
            search_pattern = f"%{search_txt}%"
            
            # Admin Search User by name or qualification
            by_user = User.query.filter(
                db.or_(
                    User.full_name.ilike(search_pattern),
                    User.qualification.ilike(search_pattern)
                )
            ).all()

            # Admin Search Subjects by name
            by_subject = Subject.query.filter(Subject.name.ilike(search_pattern)).all()
            
            # Admin Search Quizzes by topic or subject name
            by_quiz = Quiz.query.join(Subject).filter(
                db.or_(
                    Quiz.topic.ilike(search_pattern),
                    Subject.name.ilike(search_pattern)
                )
            ).all()
            
            return render_template("admin_search_results.html", 
                                   users=by_user, 
                                   subjects=by_subject, 
                                   quizzes=by_quiz, 
                                   search_query=search_txt)
            
        return redirect(url_for("admin_dashboard"))

    @app.route("/delete_user/<int:id>", methods=["POST", "GET"])
    @role_required("admin")
    def delete_user(id):
        if current_user.id == id:
            flash("Action prohibited: You cannot delete your own administrator account.", "error")
            return redirect(url_for("user_deatils"))
            
        user = User.query.get_or_404(id)
        
        try:
            # Clean up associated records that might not have cascade delete
            UserQuota.query.filter_by(user_id=id).delete()
            QuizAttempt.query.filter_by(user_id=id).delete()
            
            # Orphan quizzes created by this user
            for quiz in user.quizzes_created:
                quiz.creator_id = None
                
            db.session.delete(user)
            db.session.commit()
            flash(f"User '{user.full_name}' has been successfully removed from the system.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting the user: {str(e)}", "error")
            
        return redirect(url_for("user_deatils"))
