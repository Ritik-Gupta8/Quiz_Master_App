from flask import Flask,render_template,request,url_for,redirect, session
from models.models import *
from flask import current_app as app
from datetime import datetime,date,timedelta,timezone
import matplotlib 
matplotlib.use('Agg')   
import matplotlib.pyplot as plt
import numpy as np  
from sqlalchemy import func


#starting route
@app.route("/") #home route
def home():
    return render_template("index.html")

#admin login route
@app.route("/login",methods=["GET","POST"]) #user login
def signin():
    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")

        usr=User.query.filter_by(email=uname,password=pwd).first()
        if usr and usr.role==0: #Existed and admin
            return redirect(url_for("admin_dashboard",name=uname))
        elif usr and usr.role==1: #Existed and user
            return redirect(url_for("user_dashboard", name=uname, uid=usr.id)) 
        else:
            return render_template("login.html",msg="Invalid email or password. Please try again.")


    return render_template("login.html")
# Registration Route
@app.route("/register",methods=["GET","POST"]) #user registration
def signup():
    if request.method=="POST":
        uname=request.form.get("user_name")
        pwd=request.form.get("password")
        full_name=request.form.get("full_name")
        qualification=request.form.get("qualification")
     
        usr=User.query.filter_by(email=uname).first()
        if usr:
            return render_template("register.html",msg="This email is already registered. Please log in or use a different email.")

        new_usr=User(email=uname,password=pwd,full_name=full_name,qualification=qualification)
        db.session.add(new_usr)
        db.session.commit()
        return render_template("login.html",msg1="Thank you for registering! Try logging in now.")

    return render_template("register.html")

#common route for admin
@app.route("/admin/<name>") #admin dashboard
def admin_dashboard(name):
    subjects=get_subjects()
    return render_template("admin_dashboard.html",name=name,subjects=subjects)

@app.route('/user_details/<name>')
def user_deatils(name):
    users = User.query.filter(User.id != 1).all()  
    return render_template('user_details.html', users=users,name=name)

# Subject add,get routes for admin
@app.route("/subject/<name>",methods=["POST","GET"])
def add_subject(name):
    if request.method=="POST":
        sname=request.form.get("name")
        description=request.form.get("description")
 
        new_subject=Subject(name=sname, description=description)
        db.session.add(new_subject)
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=name))

    return render_template("add_subject.html",name=name)

#@app.route("/chapter/<subject_id>/<name>",methods=["POST","GET"])
def add_chapter(name,subject_id):
    if request.method=="POST":
        cname=request.form.get("name")
        description=request.form.get("description")
 
        new_chapter=Chapter(name=cname, description=description,subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=name))

    return render_template("add_chapter.html",subject_id=subject_id,name=name)

# Chapter add,get routes for admin
@app.route("/edit_subject/<id>/<name>",methods=["GET","POST"])
def edit_subject(id,name):
    s=get_subject(id)
    if request.method=="POST":
        sname=request.form.get("sname")
        description=request.form.get("description")
        s.name=sname
        s.description=description
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=name))
    
    return render_template("edit_subject.html",subject=s,name=name)

# Delete subject route for admin
@app.route("/delete_subject/<id>/<name>",methods=["GET","POST"])
def delete_subject(id,name):
    s=get_subject(id)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for("admin_dashboard",name=name))

# Chapter edit,get routes for admin
@app.route("/edit_chapter/<id>/<name>",methods=["GET","POST"])
def edit_chapter(id,name):
    c=get_chapter(id)

    if request.method=="POST":
        cname=request.form.get("cname")
        description=request.form.get("description")
        c.name=cname
        c.description=description
        db.session.commit()
        return redirect(url_for("admin_dashboard",name=name))
    
    return render_template("edit_chapter.html",chapter=c,name=name)

# Delete chapter route for admin
@app.route("/delete_chapter/<id>/<name>",methods=["GET","POST"])
def delete_chapter(id,name):
    c=get_chapter(id)
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for("admin_dashboard",name=name))

# Quiz add,get routes for admin
@app.route("/quiz_management/<name>")
def quiz_management(name):
    quizzes = Quiz.query.all()
    return render_template("quiz_management.html", name=name, quizzes=quizzes)
   
# Add quiz route for admin

@app.route("/add_quiz/<name>/<chapter_id>", methods=["POST", "GET"])
def add_quiz(name, chapter_id):
    if request.method == "POST":
        cid = request.form.get("chapter_id") 
        date_of_quiz = request.form.get("date_of_quiz")
        time_duration = request.form.get("time_duration")
        no_of_questions = request.form.get("no_of_questions")
        date = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()

        new_quiz = Quiz(chapter_id=cid, date_of_quiz=date, no_of_questions=no_of_questions, time_duration=time_duration)
        db.session.add(new_quiz)
        db.session.commit()
        return redirect(url_for("quiz_management", name=name))

    chapters = Chapter.query.all()
    chapter = Chapter.query.get_or_404(chapter_id)
    return render_template("add_quiz.html", name=name, chapters=chapters, selected_chapter_id=chapter_id, selected_chapter_name=chapter.name)

# Edit quiz route for admin
@app.route("/edit_quiz/<id>/<name>",methods=["GET","POST"])
def edit_quiz(id, name):
    q=get_quiz(id)
   
    if request.method=="POST":
        cid = request.form.get("chapter_id")
        date_of_quiz = request.form.get("date_of_quiz")
        date = datetime.strptime(date_of_quiz, "%Y-%m-%d").date()
        time_duration = request.form.get("time_duration")
        no_of_questions = request.form.get("no_of_questions")
        q.chapter_id=cid
        q.date_of_quiz=date
        q.time_duration=time_duration
        q.no_of_questions=no_of_questions
        db.session.commit()
        return redirect(url_for("quiz_management",name=name))
    
    chapters = Chapter.query.all()
    return render_template("edit_quiz.html",name=name,quiz=q,chapters=chapters)

# Delete quiz route for admin
@app.route("/delete_quiz/<id>/<name>", methods=["GET", "POST"])
def delete_quiz(id, name):  
    q = get_quiz(id)
    if q:
        db.session.delete(q)
        db.session.commit()
    return redirect(url_for("quiz_management", name=name))

# Question add,get routes for admin
@app.route("/add_question/<quiz_id>/<name>", methods=["POST", "GET"])
def add_question(quiz_id, name):
    if request.method=="POST":
        question=request.form.get("question_statement")
        type=request.form.get("question_type")
        option1=request.form.get("option1")
        option2=request.form.get("option2")
        option3=request.form.get("option3")
        option4=request.form.get("option4")
        correct_option=request.form.get("correct_option")

        new_question=Question(question_statement=question,question_type=type,quiz_id=quiz_id,option1=option1,option2=option2,option3=option3,option4=option4,correct_option=correct_option)
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for("quiz_management",name=name))
    
    return render_template("add_question.html", quiz_id=quiz_id ,name=name)

# Edit question route for admin
@app.route("/edit_question/<id>/<name>",methods=["GET","POST"])
def edit_question(id,name):
    q=get_question(id)

    if request.method=="POST":
        question=request.form.get("question_statement")
        type=request.form.get("question_type")
        option1=request.form.get("option1")
        option2=request.form.get("option2")
        option3=request.form.get("option3")
        option4=request.form.get("option4")
        correct_option=request.form.get("correct_option")
        q.question_statement=question
        q.question_type=type
        q.option1=option1
        q.option2=option2
        q.option3=option3
        q.option4=option4
        q.correct_option=correct_option
        db.session.commit()
        return redirect(url_for("quiz_management",name=name))
    
    return render_template("edit_question.html",question=q,name=name)
# Delete question route for admin
@app.route("/delete_question/<id>/<name>",methods=["GET","POST"])
def delete_question(id,name):
    q=get_question(id)
    db.session.delete(q)
    db.session.commit()
    return redirect(url_for("quiz_management",name=name))

# Search route for admin
@app.route("/search/<name>", methods=["GET", "POST"])
def search(name):
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        if not search_txt:  
            return redirect(url_for("admin_dashboard", name=name))
        by_user = search_by_user(search_txt)
        by_subject = search_by_subject(search_txt)
        by_quiz = search_by_quiz(search_txt)
        if by_user:
            return render_template("user_details.html", name=name, users=by_user)
        elif by_subject:
            return render_template("admin_dashboard.html", name=name, subjects=by_subject)
        elif by_quiz:
            return render_template("quiz_management.html", name=name, quizzes=by_quiz)
    return redirect(url_for("admin_dashboard", name=name))

# Search functions
def search_by_user(search_txt):
    users = User.query.filter(User.full_name.ilike(f"%{search_txt}%")).all()
    return users
# Search by subject name
def search_by_subject(search_txt):
    subjects=Subject.query.filter(Subject.name.ilike(f"%{search_txt}%")).all()
    return subjects

def search_by_quiz(search_txt):
    quizzes = Quiz.query.join(Chapter).filter(Chapter.name.ilike(f"%{search_txt}%")).all()
    return quizzes

# Admin summary route
@app.route("/admin_summary/<name>")
def admin_summary(name):
    plot = get_admin_summary() 
    plot.savefig("./static/images/admin_summary.jpeg")
    plot.clf()
    return render_template("admin_summary.html",name=name)

# Admin summary plot function
def get_admin_summary():
    subjects = Subject.query.all()
    summary = {}
    for subject in subjects:
        top_score = (
            db.session.query(func.max(Score.total_score)).join(Quiz, Score.quiz_id == Quiz.id).join(Chapter, Quiz.chapter_id == Chapter.id).filter(Chapter.subject_id == subject.id).scalar() or 0)
        summary[subject.name] = top_score  
    x_names = list(summary.keys())
    y_scores = list(summary.values())

    plt.figure(figsize=(10, 5))
    plt.bar(x_names, y_scores, color="blue" , width=0.4)
    plt.xlabel("Subjects",fontsize=14, fontweight="bold")
    plt.ylabel("Top Score",fontsize=14, fontweight="bold")
    plt.ylim(0, max(y_scores) + 2) 
    return plt 

#  ----------------------------------------------------User wok from here ----------------------------------------------------

#common route for user          
@app.route("/user/<uid>/<name>")
def user_dashboard(uid, name): # user id and name
    user = User.query.get_or_404(uid)
    quizzes = Quiz.query.join(Question).group_by(Quiz.id).all()
    dt_time_now = date.today()
    return render_template("user_dashboard.html", user=user, name=name, quizzes=quizzes, dt_time_now=dt_time_now)

# Start quiz route for user
@app.route("/start_quiz/<qid>/<uid>/<name>")
def start_quiz(qid, uid, name):
    user = User.query.get_or_404(uid)
    quiz = Quiz.query.get_or_404(qid)
    questions = Question.query.filter_by(quiz_id=qid).all()

    hours, minutes = map(int, quiz.time_duration.split(":"))  
    end_time = datetime.now(timezone.utc) + timedelta(hours=hours, minutes=minutes)
    end_time_str = end_time.isoformat()  # Send in ISO 8601 format with 'Z'

    session["quiz_end_time"] = end_time_str
    return render_template("start_quiz.html", user=user, quiz=quiz, questions=questions, name=user.email, end_time=end_time_str)

# Submit quiz route for user
@app.route("/submit_quiz/<qid>/<uid>/<name>", methods=["POST"])
def submit_quiz(qid, uid, name):
    user = User.query.get_or_404(uid)  
    quiz = Quiz.query.get_or_404(qid)
    questions = Question.query.filter_by(quiz_id=qid).all()

    end_time_str = session.get("quiz_end_time")
    if end_time_str:
        end_time = datetime.fromisoformat(end_time_str)
        if datetime.now(timezone.utc) > end_time:
            return "Time is up! Your answers were not submitted in time.", 403  

    total_score = sum(1 for q in questions if request.form.get(f"answer_{q.id}") == getattr(q, q.correct_option))
    timestamp = datetime.now() 
    existing_score = Score.query.filter_by(quiz_id=quiz.id, user_id=user.id).first()
    if existing_score:
        existing_score.total_score = total_score
        existing_score.timestamp = timestamp 
    else:
        new_score = Score(quiz_id=quiz.id, user_id=user.id, total_score=total_score, timestamp=timestamp)
        db.session.add(new_score)
    
    db.session.commit()
    return redirect(url_for("user_dashboard", uid=uid, name=name))

# View score route for user
@app.route("/view_score/<uid>/<name>")
def view_score(uid, name):
    user = User.query.get_or_404(uid) 
    scores = Score.query.filter_by(user_id=uid).all() 
    quizzes = Quiz.query.filter(Quiz.id.in_([score.quiz_id for score in scores])).all()  
    dt_time_now = datetime.now().date() 

    return render_template("view_score.html", user=user, quizzes=quizzes, dt_time_now=dt_time_now, name=name, scores=scores)

# Search score route for user
@app.route("/user_search/<uid>/<name>", methods=["GET", "POST"])
def search_user(name, uid):
    user = User.query.get_or_404(uid)  
    if request.method == "POST":
        search_txt = request.form.get("search_txt")
        if not search_txt:  
            return redirect(url_for("user_dashboard", uid=uid, name=name))
        subject_by_score = search_subject_by_score(search_txt, int(uid)) 
        if subject_by_score:
            return render_template("view_score.html", name=name, user=user, scores=subject_by_score, quizzes=Quiz.query.all())
    return redirect(url_for("user_dashboard", uid=uid, name=name))

# Search function for user
def search_subject_by_score(search_txt, user_id):
    score_value = int(search_txt)  
    scores = Score.query.filter_by(user_id=user_id, total_score=score_value).all()
    return scores

# User summary
@app.route("/user_summary/<uid>/<name>")
def user_summary(uid, name): # user id and name
    user = User.query.get_or_404(uid) 
    plot = get_user_summary(uid)
    plot.savefig("./static/images/user_summary.jpeg")
    plot.clf()
    return render_template("user_summary.html", user=user, name=name)

# User summary plot
def get_user_summary(user_id):
    subjects = Subject.query.all()
    summary = {}
    for subject in subjects:
        quiz_count = (
            db.session.query(Score).join(Quiz, Score.quiz_id == Quiz.id).join(Chapter, Quiz.chapter_id == Chapter.id) .filter(Chapter.subject_id == subject.id, Score.user_id == user_id).count())
        summary[subject.name] = quiz_count 
    x_names = list(summary.keys())
    y_counts = list(summary.values())
    plt.bar(x_names, y_counts, color="blue", width=0.4)
    plt.title("Quizzes Attempted Per Subject",fontsize=14, fontweight="bold")
    plt.xlabel("Subjects",fontsize=14, fontweight="bold")
    plt.ylabel("Attempted Quizzes",fontsize=14, fontweight="bold")
    plt.yticks(np.arange(0, max(y_counts) + 1, 1))  
    return plt
# Helper functions to get objects
def get_subjects():
    subjects=Subject.query.all()
    return subjects

# Helper functions to get objects by id
def get_subject(id):
    subject=Subject.query.filter_by(id=id).first()
    return subject
# Helper functions to get objects by id
def get_chapter(id):
    chapter=Chapter.query.filter_by(id=id).first()
    return chapter

# Helper functions to get objects by id
def get_quiz(id):
    quiz=Quiz.query.filter_by(id=id).first()
    return quiz

# Helper functions to get objects by id
def get_question(id):
    question=Question.query.filter_by(id=id).first()
    return question
