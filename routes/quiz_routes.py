from flask import render_template, request, url_for, redirect, flash
from flask_login import current_user
import json
from datetime import datetime, timezone, timedelta
from models.models import db, Quiz, Question, QuizAttempt, Score
from routes.utils import role_required
from services.quiz_service import save_attempt_answer, finalize_quiz_attempt

MAX_QUIZ_ATTEMPTS = 3

def init_quiz_routes(app):
    @app.route("/start_quiz/<qid>")
    @role_required("user")
    def start_quiz(qid):
        quiz = Quiz.query.get_or_404(qid)
        questions = Question.query.filter_by(quiz_id=qid).all()

        all_attempts = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).all()
        completed_attempts = [a for a in all_attempts if a.status in ["submitted", "expired"]]
        active_attempt = next((a for a in all_attempts if a.status == "in_progress"), None)

        if active_attempt:
            end_time_str = active_attempt.end_time.isoformat()
            current_answers = json.loads(active_attempt.answers)
            attempt_num = len(completed_attempts) + 1
            return render_template("start_quiz.html", user=current_user, quiz=quiz, questions=questions,
                                   end_time=end_time_str, current_answers=current_answers,
                                   attempt_num=attempt_num, max_attempts=MAX_QUIZ_ATTEMPTS)

        if len(completed_attempts) >= MAX_QUIZ_ATTEMPTS:
            flash(f"You have reached the maximum of {MAX_QUIZ_ATTEMPTS} attempts for this quiz.", "warning")
            return redirect(url_for("view_score"))

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

        attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()

        if not attempt:
            return json.dumps({"success": False, "error": "No active attempt found"}), 403

        success, err = save_attempt_answer(attempt, question_id, selected_option)
        if not success:
            return json.dumps({"success": False, "error": err}), 403

        return json.dumps({"success": True})

    @app.route("/submit_quiz/<qid>", methods=["POST"])
    @role_required("user")
    def submit_quiz(qid):
        quiz = Quiz.query.get_or_404(qid)
        attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()

        if not attempt:
            flash("No active quiz attempt found.", "danger")
            return redirect(url_for("user_dashboard"))

        total_score, success, message = finalize_quiz_attempt(attempt, request.form, qid)
        
        if success:
            timestamp = datetime.now()
            new_score = Score(quiz_id=quiz.id, user_id=current_user.id, total_score=total_score, timestamp=timestamp)
            db.session.add(new_score)
            db.session.commit()
            
            completed_count = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()
            remaining = MAX_QUIZ_ATTEMPTS - completed_count

            all_scores_for_quiz = Score.query.filter_by(quiz_id=quiz.id, user_id=current_user.id).all()
            best = max(all_scores_for_quiz, key=lambda s: s.total_score)
            if remaining > 0:
                flash(f"Attempt {completed_count}/{MAX_QUIZ_ATTEMPTS} done! Score: {total_score}/{quiz.no_of_questions}. "
                      f"Best so far: {best.total_score}/{quiz.no_of_questions}. {remaining} attempt(s) remaining.", "success")
            else:
                flash(f"All {MAX_QUIZ_ATTEMPTS} attempts used! Final score: {total_score}/{quiz.no_of_questions}. "
                      f"Best score: {best.total_score}/{quiz.no_of_questions}.", "info")
        else:
            db.session.commit()
            flash(message, "danger")

        return redirect(url_for("view_score"))

    @app.route("/review_quiz/<qid>")
    @role_required("user")
    def review_quiz(qid):
        quiz = Quiz.query.get_or_404(qid)
        
        all_attempts = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).all()
        completed_attempts = [a for a in all_attempts if a.status in ["submitted", "expired"]]
        
        if len(completed_attempts) < MAX_QUIZ_ATTEMPTS:
            flash("You can only review answers after using all your attempts.", "warning")
            return redirect(url_for("view_score"))
            
        latest_attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="submitted").order_by(QuizAttempt.end_time.desc()).first()
        if not latest_attempt:
            latest_attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="expired").order_by(QuizAttempt.end_time.desc()).first()
            
        if not latest_attempt:
            flash("No completed attempts found to review.", "warning")
            return redirect(url_for("view_score"))
            
        questions = Question.query.filter_by(quiz_id=qid).all()
        answers = json.loads(latest_attempt.answers)
        
        return render_template("review_quiz.html", user=current_user, quiz=quiz, questions=questions, answers=answers, attempt=latest_attempt)
