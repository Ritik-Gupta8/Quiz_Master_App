# 🧠 Quiz Master — AI-Powered Quiz Platform

> A full-stack Progressive Web App (PWA) built with Flask, PostgreSQL, Tailwind CSS, and Google Gemini AI. Students can take AI-generated quizzes, track their progress, and compete on dynamic leaderboards.

[![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-black?logo=flask)](https://flask.palletsprojects.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8?logo=tailwindcss)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169e1?logo=postgresql)](https://supabase.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini-AI-8e44ad?logo=google)](https://ai.google.dev/)

---

## ✨ Features Overview

### 👤 For Students (Users)
- **AI Quiz Generation:** Generate tailored MCQ quizzes using Google Gemini 1.5 Flash by selecting a Subject, Grade level, and Difficulty.
- **Fair-Use Quotas:** Users are limited to 2 AI-generated quizzes per day with a 10-minute cooldown to prevent API abuse.
- **Dynamic Difficulty:** 
  - **Easy:** 5 questions, 5-minute timer
  - **Medium:** 10 questions, 10-minute timer
  - **Hard:** 15 questions, 15-minute timer
- **3-Attempt Rule:** Attempt a quiz up to 3 times. The highest score is recorded. After 3 attempts, a "Review" mode is unlocked to see correct answers.
- **XP & Leaderboard:** Earn XP based on your score multiplied by difficulty (Easy 1x, Medium 1.2x, Hard 1.5x). Compete on subject-specific leaderboards.
- **Real-Time Saving:** Answers are saved instantly via AJAX so no progress is lost if the page is refreshed.
- **Interactive Analytics:** View progress history, accuracy trends, and time spent via dynamic Chart.js visualizations.

### 🛠️ For Administrators
- **Global Dashboard:** View total quizzes, active users, average platform scores, and subject-wise metrics.
- **Subject & Quiz Management:** Full CRUD operations over Subjects and Quizzes. (Note: Quizzes are linked directly to Subjects).
- **User Management:** Monitor user activity, search by name/qualification, and securely delete users via cascading database constraints.

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, Flask 3.0.3 |
| **Database** | PostgreSQL (hosted on Supabase), Flask-SQLAlchemy, Flask-Migrate |
| **AI Integration** | Google Gemini 1.5 Flash (`google-generativeai`) |
| **Frontend** | Tailwind CSS v3 (Node/CLI built), Chart.js, Vanilla JS |
| **PWA & Performance** | Service Worker, Manifest, Flask-Compress (Gzip/Brotli), persistent SQL-backed sessions |

---

## 📂 Project Structure

```text
Quiz_Master_App/
├── app.py                    # App factory, Extensions, Route Initializations
├── requirements.txt          # Python dependencies
├── package.json              # Tailwind CSS build scripts
├── tailwind.config.js        # Tailwind configuration & purge paths
├── .env.example              # Environment variables template
│
├── models/
│   └── models.py             # SQLAlchemy models (User, Subject, Quiz, Question, Score, QuizAttempt, UserQuota, QuizCache)
│
├── routes/                   # Modular route controllers
│   ├── auth_routes.py        
│   ├── admin_routes.py       
│   ├── user_routes.py        
│   ├── quiz_routes.py        
│   ├── analytics_routes.py   
│   ├── api_routes.py         
│   └── utils.py              # Role-based decorators
│
├── services/                 # Business logic layer
│   ├── ai_service.py         # Gemini API interaction & parsing
│   ├── quiz_service.py       # Attempt handling & answer saving
│   └── analytics_service.py  # Data aggregation for Chart.js
│
├── templates/                # Jinja2 HTML templates
│
└── static/                   # Static assets
    ├── styles/
    │   ├── tailwind_input.css # Tailwind source file
    │   └── main.css           # Compiled output file
    ├── sw.js                  # Service Worker (PWA caching)
    ├── manifest.json          # PWA Manifest
    └── offline.html           # Offline fallback page
```

---

## 🗄️ Database Models

```text
User ──────────────────────────────────────────────────────┐
│ id, email, password, role (0=admin, 1=user)              │
│ full_name, qualification                                 │
└──┬───────────────────────────────────────────────────────┘
   │
   ├─► Score (quiz_id, user_id, total_score, timestamp)
   │
   ├─► QuizAttempt (quiz_id, user_id, status, start_time, end_time, answers JSON, final_score)
   │
   └─► UserQuota (user_id, daily_count, last_reset_date, last_request_time)

Subject ───────────────────────────────────────────────────┐
│ id, name, description                                    │
└──┬───────────────────────────────────────────────────────┘
   └─► Quiz (subject_id, creator_id, topic, date_of_quiz, time_duration, no_of_questions, difficulty)
       └──► Question (quiz_id, statement, option1-4, correct_option, type)
```

---

## ⚙️ Local Development Setup

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+** (Required for compiling Tailwind CSS)
- **PostgreSQL Database** (We recommend creating a free project on Supabase)

### 2. Setup Repository
```bash
git clone <repository-url>
cd Quiz_Master_App
```

### 3. Create a Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
npm install
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your actual credentials:
```bash
cp .env.example .env
```
```env
GOOGLE_API_KEY=your_gemini_api_key
SECRET_KEY=your_flask_secret_key
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres  # Use Supabase Session Pooler
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_password
FLASK_DEBUG=true
```

### 6. Build Tailwind CSS
You must compile the Tailwind CSS to generate `static/styles/main.css`.
```bash
npm run build:css
```
*(During active UI development, you can use `npm run watch:css` to auto-recompile).*

### 7. Run Database Migrations
We use `Flask-Migrate` to manage PostgreSQL schema changes. Do **not** use `db.create_all()`.
```bash
flask db upgrade
```

### 8. Start the Application
```bash
python app.py
```
Visit `http://127.0.0.1:5000` to start using the app.

---

## 🚀 Deployment to Render.com

### 1. Prepare for Production
Before pushing to GitHub, generate the minified production CSS:
```bash
npm run prod:css
git add .
git commit -m "chore: build production assets"
git push origin main
```

### 2. Render Settings
Create a new **Web Service** on Render and connect your GitHub repository.
- **Root Directory:** *(leave completely empty)*
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`

### 3. Environment Variables
Add the variables from your `.env` file to the Render Environment tab.
> **⚠️ Important:** Ensure your `DATABASE_URL` uses the **Session Pooler** (IPv4 compatible, usually port `6543`) from your Supabase dashboard, since Render's free tier does not support IPv6 direct connections.

### 4. Run Migrations on Render
After your first successful deploy, open the **Render Shell** and run:
```bash
flask db upgrade
```

---

## 🎨 CSS Build Scripts Reference

This project utilizes modern Tailwind CSS without relying on CDNs to ensure zero network latency.

| Command | Action | Use Case |
|---------|--------|----------|
| `npm run build:css` | Generates unminified `main.css` | Initial local setup |
| `npm run watch:css` | Watches `html`/`js`/`py` files for class changes | Active UI development |
| `npm run prod:css` | Generates a minified `main.css` | **Run before deploying to production** |



---


## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.