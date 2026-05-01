# 🎓 SRES — Student Registration & Enrollment System

A full-featured web application for managing student registrations, course enrollments, and academic administration. Built with **Python (Flask)**, **SQLite**, and vanilla **HTML/CSS**.

---

## ✨ Features

### Student Portal
- **Registration & Login** — Secure sign-up with hashed passwords
- **Dashboard** — View enrolled courses, pending requests, and credit summary
- **Course Catalog** — Browse available courses and submit enrollment requests
- **Profile Management** — Update personal details and change password
- **Enrollment Tracking** — Monitor approval status of all enrollment requests

### Admin Panel
- **Dashboard** — At-a-glance statistics (students, courses, enrollments)
- **Student Management** — Search, view, and delete student records
- **Course Management** — Add, edit, and delete courses with capacity limits
- **Enrollment Approvals** — Approve or reject pending enrollment requests
- **Reports** — Course-wise and program-wise analytics

---

## 🛠️ Tech Stack

| Layer      | Technology               |
|------------|--------------------------|
| Backend    | Python 3, Flask          |
| Database   | SQLite                   |
| Frontend   | HTML5, CSS3, Jinja2      |
| Auth       | Werkzeug (password hash) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/SRES.git
   cd SRES
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate        # Linux / macOS
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```
   Or on Windows, simply double-click `run.bat`.

5. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## 🔑 Default Admin Credentials

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

> ⚠️ Change the default admin password after first login in a production environment.

---

## 📁 Project Structure

```
SRES/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── run.bat                 # Windows quick-start script
├── static/
│   └── css/
│       └── style.css       # Application styles
└── templates/
    ├── base.html           # Base layout template
    ├── index.html          # Landing page
    ├── admin/
    │   ├── base.html       # Admin layout
    │   ├── login.html      # Admin login
    │   ├── dashboard.html  # Admin dashboard
    │   ├── students.html   # Student management
    │   ├── courses.html    # Course listing
    │   ├── course_form.html# Add/Edit course form
    │   ├── enrollments.html# Enrollment management
    │   └── reports.html    # Reports & analytics
    └── student/
        ├── login.html      # Student login
        ├── register.html   # Student registration
        ├── dashboard.html  # Student dashboard
        ├── profile.html    # Profile management
        ├── courses.html    # Course catalog
        └── enrollments.html# Enrollment history
```

---

## 📸 Screenshots

> _Add screenshots of the landing page, student dashboard, and admin panel here._

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
