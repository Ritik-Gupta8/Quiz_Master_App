from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Integer, default=1)
    full_name = db.Column(db.String(255), nullable=False)
    qualification = db.Column(db.String(255), nullable=True)

    scores = db.relationship("Score", cascade="all,delete", backref="user", lazy=True)
    quizzes_created = db.relationship("Quiz", backref="creator", lazy=True)

    def calculate_xp(self, subject_id=None):
        best_scores = {}
        for s in self.scores:
            if subject_id and s.quiz.subject_id != subject_id:
                continue
            qid = s.quiz_id
            if qid not in best_scores or s.total_score > best_scores[qid].total_score:
                best_scores[qid] = s
                
        xp = 0
        for qid, s in best_scores.items():
            multiplier = 1.0
            if s.quiz.difficulty == 'Medium':
                multiplier = 1.2
            elif s.quiz.difficulty == 'High':
                multiplier = 1.5
            if s.quiz.no_of_questions > 0:
                xp += int((s.total_score / s.quiz.no_of_questions) * 100 * multiplier)
        return xp

    def __repr__(self):
        return f"<User {self.id}: {self.full_name}>"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    quizzes = db.relationship("Quiz", cascade="all,delete", backref="subject", lazy=True)

    def __repr__(self):
        return f"<Subject {self.id}: {self.name}>"

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    topic = db.Column(db.String(255), nullable=False, default="General AI Quiz")
    date_of_quiz = db.Column(db.Date, nullable=False)
    time_duration = db.Column(db.String(50), nullable=False)
    no_of_questions = db.Column(db.Integer, nullable=False) 
    difficulty = db.Column(db.String(20), default="Medium")

    questions = db.relationship("Question", cascade="all,delete", backref="quiz", lazy=True)
    scores = db.relationship("Score", cascade="all,delete", backref="quiz", lazy=True)
    attempts = db.relationship("QuizAttempt", cascade="all,delete", backref="quiz", lazy=True)

    @property
    def formatted_topic(self):
        if "AI Quiz (" in self.topic or "AI Practice (" in self.topic:
            grade_part = self.topic.split('(')[-1].replace(')', '')
            return f"{self.subject.name} - {grade_part}"
        return f"{self.subject.name} - {self.topic}"

    def __repr__(self):
        return f"<Quiz {self.id}: subject={self.subject_id}, topic={self.topic}>"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    question_statement = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.Text, nullable=False)
    option1 = db.Column(db.String(200), nullable=False)  
    option2 = db.Column(db.String(200), nullable=False) 
    option3 = db.Column(db.String(200), nullable=False)  
    option4 = db.Column(db.String(200), nullable=False)  
    correct_option = db.Column(db.String(200), nullable=False) 

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    total_score = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Score {self.id}: quiz={self.quiz_id}, user={self.user_id}, score={self.total_score}>"

class UserQuota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    last_request_time = db.Column(db.DateTime, nullable=True)
    daily_count = db.Column(db.Integer, default=0)
    last_reset_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<UserQuota {self.id}: user={self.user_id}, daily_count={self.daily_count}>"

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quiz.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(20), default="in_progress") # in_progress, submitted, expired
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    answers = db.Column(db.Text, default="{}") # JSON string of answers
    final_score = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<QuizAttempt {self.id}: user={self.user_id}, quiz={self.quiz_id}, status={self.status}>"

class QuizCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt_hash = db.Column(db.String(255), unique=True, nullable=False)
    generated_json = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<QuizCache {self.id}: hash={self.prompt_hash}>"