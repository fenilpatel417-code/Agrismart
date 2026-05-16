# 🌾 AgriSmart — AI Crop Disease Detection

> An AI-powered agricultural assistant built with **FastAPI** and **Google Gemini 2.5 Flash** that helps farmers detect crop diseases, identify plants, and get expert growing advice — all for free.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🦠 **Disease Detection** | Upload a crop photo to instantly diagnose diseases with severity ratings |
| 🌿 **Crop Identification** | Identify any plant/crop with growing conditions and economic value |
| 📈 **Growth Optimization** | Get top 5 expert tips to grow crops faster and healthier |
| 💊 **Treatment Plans** | Step-by-step chemical & organic treatment instructions |
| 🧪 **Fertilizer Guide** | NPK ratio recommendations and fertilization schedules |
| 🤖 **AI Chatbot** | Conversational farming assistant with memory across messages |
| 📜 **Scan History** | View all past analyses stored locally in SQLite |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.13 |
| **Backend Framework** | FastAPI 0.115 |
| **ASGI Server** | Uvicorn |
| **AI Model** | Google Gemini 2.5 Flash (multimodal) |
| **AI SDK** | google-genai |
| **Database** | SQLite + SQLAlchemy ORM |
| **Templating** | Jinja2 |
| **Image Processing** | Pillow (PIL) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Deployment** | Heroku (Procfile included) |

---

## 📁 Project Structure

```
agrismart3/
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies
├── Procfile                 # Heroku deployment config
├── .env                     # API key (keep secret!)
├── .env.example             # Template for .env
├── agrismart.db             # SQLite database (auto-created)
│
├── routers/                 # API route handlers
│   ├── detection.py         # /api/detect — image analysis
│   ├── chatbot.py           # /chat — AI chatbot
│   └── history.py           # /api/history — scan history
│
├── services/
│   └── gemini_service.py    # Gemini AI integration & prompts
│
├── database/
│   ├── db.py                # SQLAlchemy engine & session
│   └── models.py            # ScanHistory ORM model
│
├── templates/               # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── detect.html
│   ├── chatbot.html
│   └── history.html
│
└── static/                  # CSS and uploaded images
    ├── css/
    └── uploads/
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- A free Google Gemini API key → [Get one here](https://aistudio.google.com)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/agrismart.git
cd agrismart
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure your API key
Copy the example env file and add your key:
```bash
copy .env.example .env
```
Edit `.env`:
```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Run the server
```bash
# Option A — if uvicorn is in your PATH
uvicorn main:app --reload

# Option B — using Python directly (always works)
python -m uvicorn main:app --reload
```

### 5. Open in browser
```
http://127.0.0.1:8000
```

---

## 🌐 Pages & Routes

| URL | Page |
|---|---|
| `http://127.0.0.1:8000/` | 🏠 Home |
| `http://127.0.0.1:8000/detect` | 🔬 Disease Detection |
| `http://127.0.0.1:8000/chatbot` | 🤖 AI Chatbot |
| `http://127.0.0.1:8000/history` | 📜 Scan History |
| `http://127.0.0.1:8000/docs` | 📄 Auto API Docs (Swagger UI) |

---

## 🤖 How the AI Works

AgriSmart uses **zero-shot multimodal AI** — no custom model training required:

1. User uploads a crop image
2. The image + a structured expert prompt are sent to **Gemini 2.5 Flash**
3. Gemini acts as a specialized expert (plant pathologist, botanist, etc.)
4. The response is parsed and displayed in a structured format
5. Results are saved to the local SQLite database

The chatbot maintains **conversation memory** by sending the last 10 messages as history with every request.

---

## ☁️ Deploying to Heroku

```bash
heroku create your-app-name
heroku config:set GEMINI_API_KEY=your_key_here
git push heroku main
```

The `Procfile` is already configured:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Google Gemini](https://deepmind.google/technologies/gemini/) — AI model powering all analysis
- [FastAPI](https://fastapi.tiangolo.com/) — modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) — Python SQL toolkit
