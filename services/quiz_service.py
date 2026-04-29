import json
from datetime import datetime, timezone, timedelta
from models.models import db, QuizAttempt, Question

def calculate_score(final_answers, questions):
    """Calculate the score from final answers mapping."""
    total_score = 0
    for q in questions:
        if final_answers.get(str(q.id)) == getattr(q, q.correct_option):
            total_score += 1
    return total_score

def save_attempt_answer(attempt, question_id, selected_option):
    """Saves a single answer to an in-progress attempt."""
    if datetime.now(timezone.utc) > attempt.end_time.replace(tzinfo=timezone.utc):
        attempt.status = "expired"
        db.session.commit()
        return False, "Quiz time has expired"

    answers = json.loads(attempt.answers)
    answers[question_id] = selected_option
    attempt.answers = json.dumps(answers)
    db.session.commit()
    return True, None

def finalize_quiz_attempt(attempt, form_data, quiz_id):
    """Calculates everything, scores the attempt, and saves it."""
    # Final time check (allow 10 second buffer)
    now_utc = datetime.now(timezone.utc)
    if now_utc > attempt.end_time.replace(tzinfo=timezone.utc) + timedelta(seconds=10):
        attempt.status = "expired"
        success = False
        message = "Submission failed: Time has expired."
    else:
        attempt.status = "submitted"
        # Update end_time to actual submission time for accurate analytics
        # Strip tzinfo for consistency with how SQLAlchemy stores DateTime in this app
        attempt.end_time = now_utc.replace(tzinfo=None)
        success = True
        message = "Quiz submitted successfully!"

    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    stored_answers = json.loads(attempt.answers)

    final_answers = {}
    for q in questions:
        # Form overrides stored answers, to catch last second clicks
        val = form_data.get(f"answer_{q.id}") or stored_answers.get(str(q.id))
        final_answers[str(q.id)] = val

    attempt.answers = json.dumps(final_answers)
    total_score = calculate_score(final_answers, questions)
    attempt.final_score = total_score
    
    return total_score, success, message
