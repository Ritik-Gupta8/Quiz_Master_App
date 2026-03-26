# 🎓 Quiz Master App

A robust **Flask‑based AI Quiz Generator** that enables educators to instantly create grade‑specific, multi‑choice quizzes powered by **Google Gemini 1.5 Flash**. The application features an intuitive web interface for managing subjects, chapters, and quizzes with persistent SQLite storage and visual performance summaries.

---

## 🛠️ Tech Stack

### Backend & Core
- **Framework**: [Flask 3.0.3](https://flask.palletsprojects.com/)
- **ORM & Database**: [Flask-SQLAlchemy 3.1.1](https://flask-sqlalchemy.palletsprojects.com/) / [SQLAlchemy 2.0.27](https://www.sqlalchemy.org/) (SQLite3)
- **Environment**: [python-dotenv 1.0.1](https://pypi.org/project/python-dotenv/)
- **OS Compatibility**: Windows, Linux, macOS

### AI Integration
- **Model**: [Google Gemini 1.5 Flash](https://deepmind.google/technologies/gemini/)
- **SDK**: [google-generativeai 0.8.3](https://pypi.org/project/google-generativeai/)

### Data Visualization & Utilities
- **Charts**: [Matplotlib 3.9.0+](https://matplotlib.org/)
- **Data**: [NumPy 2.1.0+](https://numpy.org/)
- **Image Processing**: [Pillow 10.2.0+](https://python-pillow.org/)

### Frontend
- **Templating**: [Jinja2](https://jinja.palletsprojects.com/)
- **Styling**: Modern CSS with Utility Classes (Tailwind‑inspired)
- **Responsiveness**: Fully responsive layout for desktop and mobile

---

## ✨ Key Features

- **🤖 AI Quiz Generation**: Instantly generate up to 20 questions based on Subject, Chapter, Grade, and Difficulty level.
- **📚 Academic Hierarchy**: Organize content by Subjects → Chapters → Quizzes.
- **📊 Interactive Dashboards**: 
  - **Admin**: Manage all content, view user details, and see subject-wise performance charts.
  - **User**: Take quizzes with a persistent session-based timer and view past performance.
- **📈 Data Visualization**: Automated generation of performance summaries using Matplotlib.
- **🔐 Secure Access**: Session-based authentication and role-based access control (Admin/User).

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisite
Ensure you have **Python 3.10+** installed.

### 2. Setup Repository
```bash
git clone <repo-url>
cd Quiz_Master_App
```

### 3. Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a `.env` file in the root directory:
```dotenv
GOOGLE_API_KEY=your-gemini-api-key
SECRET_KEY=your-flask-secret-key
```

### 6. Initialize Database
Run this one-liner to create the SQLite schema:
```bash
python -c "from models.models import db; from app import setup_app; setup_app(); db.create_all()"
```

### 7. Run Application
```bash
python app.py
```
Visit `http://127.0.0.1:5000/` to start using the app.

---

## 📂 Project Structure

```text
Quiz_Master_App/
├── app.py                 # Core App Factory & Configuration
├── controllers/
│   ├── controllers.py    # Route Handlers & Business Logic
│   └── gemini_service.py # Gemini AI Integration Layer
├── models/
│   └── models.py         # SQLAlchemy Database Models
├── static/                # Images, CSS, and JS Assets
├── templates/             # Jinja2 HTML Layouts & Views
├── .env.example           # Configuration Template
└── requirements.txt       # Project Dependencies
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.