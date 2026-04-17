from flask import render_template
from flask_login import current_user
from datetime import datetime
from models.models import Quiz, Score, QuizAttempt
from routes.utils import role_required
from services.analytics_service import get_admin_summary_data, get_user_summary_data

MAX_QUIZ_ATTEMPTS = 3

def init_analytics_routes(app):
    @app.route("/admin_summary")
    @role_required("admin")
    def admin_summary():
        data = get_admin_summary_data()
        return render_template("admin_summary.html", data=data)

    @app.route("/user_summary")
    @role_required("user")
    def user_summary():
        data = get_user_summary_data(current_user.id)
        return render_template("user_summary.html", user=current_user, data=data)

    @app.route("/view_score")
    @role_required("user")
    def view_score():
        all_scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.timestamp.asc()).all()

        best_score_map = {}
        all_scores_by_quiz = {}
        for score in all_scores:
            all_scores_by_quiz.setdefault(score.quiz_id, []).append(score)
            if score.quiz_id not in best_score_map or score.total_score > best_score_map[score.quiz_id].total_score:
                best_score_map[score.quiz_id] = score

        quiz_ids = list(best_score_map.keys())
        best_scores = list(best_score_map.values())
        quizzes = Quiz.query.filter(Quiz.id.in_(quiz_ids)).all() if quiz_ids else []
        dt_time_now = datetime.now().date()

        attempt_counts = {}
        for qid in quiz_ids:
            attempt_counts[qid] = QuizAttempt.query.filter_by(quiz_id=qid, user_id=current_user.id).filter(
                QuizAttempt.status.in_(["submitted", "expired"])).count()

        return render_template("view_score.html", user=current_user, quizzes=quizzes, dt_time_now=dt_time_now,
                               scores=best_scores, attempt_counts=attempt_counts, max_attempts=MAX_QUIZ_ATTEMPTS,
                               all_scores_by_quiz=all_scores_by_quiz)
