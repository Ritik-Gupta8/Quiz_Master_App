from flask import jsonify, request
from flask_login import current_user
from models.models import db, Quiz, QuizAttempt, Score
from routes.utils import role_required
from services.analytics_service import get_admin_summary_data, get_user_summary_data
from services.quiz_service import save_attempt_answer, finalize_quiz_attempt
from datetime import datetime

MAX_QUIZ_ATTEMPTS = 3

def init_api_routes(app):
    @app.route("/api/admin-summary", methods=["GET"])
    @role_required("admin")
    def api_admin_summary():
        data = get_admin_summary_data()
        return jsonify({"success": True, "data": data})

    @app.route("/api/user-summary", methods=["GET"])
    @role_required("user")
    def api_user_summary():
        data = get_user_summary_data(current_user.id)
        return jsonify({"success": True, "data": data})

    @app.route("/api/save-answer/<qid>", methods=["POST"])
    @role_required("user")
    def api_save_answer(qid):
        data = request.get_json()
        question_id = str(data.get("question_id"))
        selected_option = data.get("selected_option")

        attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()
        if not attempt:
            return jsonify({"success": False, "error": "No active attempt found"}), 403

        success, err = save_attempt_answer(attempt, question_id, selected_option)
        if not success:
            return jsonify({"success": False, "error": err}), 403

        return jsonify({"success": True})

    @app.route("/api/submit-quiz/<qid>", methods=["POST"])
    @role_required("user")
    def api_submit_quiz(qid):
        quiz = Quiz.query.get_or_404(qid)
        attempt = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id, status="in_progress").order_by(QuizAttempt.id.desc()).first()

        if not attempt:
            return jsonify({"success": False, "error": "No active quiz attempt found."}), 403

        data = request.get_json() or {}
        total_score, success, message = finalize_quiz_attempt(attempt, data, qid)
        
        if success:
            timestamp = datetime.now()
            new_score = Score(quiz_id=quiz.id, user_id=current_user.id, total_score=total_score, timestamp=timestamp)
            db.session.add(new_score)
            db.session.commit()
            
            completed_count = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()
            remaining = MAX_QUIZ_ATTEMPTS - completed_count

            return jsonify({
                "success": True, 
                "score": total_score, 
                "total_questions": quiz.no_of_questions,
                "remaining_attempts": remaining,
                "message": message
            })
        else:
            db.session.commit()
            return jsonify({"success": False, "error": message}), 400
