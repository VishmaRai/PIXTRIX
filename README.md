# PIXTRIX 🎨 – AI Image Generation Web App

PIXTRIX is a Flask-based web application that allows users to generate AI-powered images using the DreamShaper-8 model hosted on Google Colab.  
The model is exposed via **ngrok API** and integrated into the Flask backend.  
It includes authentication, payment integration, credit system, and an admin dashboard.

---

## 🚀 Features

- **AI Image Generation** using DreamShaper-8 (Stable Diffusion)
- Model hosted on **Google Colab** with **ngrok API** for real-time requests
- **User Authentication** (Sign up / Login)
- **Credit-Based System** – users spend credits for image generation
- **Payment Gateway Integration** (eSewa)
- **Responsive UI** with Bootstrap
- **Admin Dashboard**  
  - Manage credits and prices  
  - View payment history  
  - Monitor image generation stats
- **Email Notifications** for users
- **Environment Variables** for sensitive data

---

## 🛠️ Tech Stack

**Frontend:**
- HTML5, CSS3, JavaScript
- Bootstrap 5

**Backend:**
- Flask (Python)
- Jinja2 Templating
- Flask-Mail for email notifications

**Database:**
- SQLite / MySQL

**AI Model:**
- DreamShaper-8 (Stable Diffusion)  
  Hosted in **Google Colab**  
  Exposed via **ngrok API**

**Admin Panel:**
- SB Admin 2 Bootstrap Template

---

## 📦 Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/VishmaRai/PIXTRIX.git   
```
### 2️⃣ Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```
### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```
### 4️⃣ Setup .env File
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Database URL
DATABASE_URI=sqlite:///database.db

# API Endpoint from ngrok (Colab)
MODEL_API_URL=https://<ngrok-url>.ngrok-free.app/generate
```
### ⚡ Run FlaskDreamShaper.ipynb on Google Colab
  - Copy the ngrok URL and update .env file.
  
### ▶️ Run the Flask App
```bash
flask run
```
Access the app at http://127.0.0.1:5000
