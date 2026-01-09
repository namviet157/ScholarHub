## UniHub

Academic document sharing platform for students. Upload, explore, and learn with AI-powered tools.

### Features
- **Document sharing**: Upload PDFs with metadata (university, faculty, course)
- **Community**: Vote, comment, and favorite documents
- **AI tools**: Auto-generate quizzes, summaries, and keywords from PDFs
- **User profiles**: Registration, avatar uploads, password management

### Tech Stack
- **Backend**: FastAPI + asyncpg
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage
- **AI**: Transformers, KeyBERT, NLTK
- **Frontend**: Vanilla JS + CSS

### Quick Start

```bash
# Clone
git clone https://github.com/namviet157/UniHub.git
cd UniHub

# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure .env
DATABASE_URL=postgresql://postgres:xxx@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-service-key
SECRET_KEY=your-secret-key

# Run
uvicorn app:app --reload
```

Visit http://localhost:8000

### Project Structure
```
UniHub/
├── app.py              # FastAPI backend
├── config.py           # Configuration (edit this!)
├── schema.sql          # Database schema
├── make_quiz.py        # Quiz generator
├── summarizer.py       # PDF summarizer
├── keywords.py         # Keyword extractor
├── requirements.txt    # Dependencies
├── public/             # Frontend
│   ├── index.html
│   ├── css/styles.css
│   └── js/*.js
└── uploads/            # Temp storage
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/register` | POST | Register user |
| `/api/login` | POST | Login |
| `/api/me` | GET | Current user |
| `/documents/` | GET | List documents |
| `/uploadfile/` | POST | Upload document |
| `/api/documents/{id}/comments` | GET/POST | Comments |
| `/api/documents/{id}/votes` | GET/POST | Votes |
| `/api/generate-quiz-from-file` | POST | Generate quiz |

### Deploy on Render

1. Create Web Service from GitHub
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add environment variables

### License
MIT
