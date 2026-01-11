import os
import shutil
import hashlib
import uuid
import importlib.util
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncpg
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL_RAW = os.getenv("SUPABASE_URL")
SUPABASE_URL = SUPABASE_URL_RAW.rstrip("/") if SUPABASE_URL_RAW else ""  # For string formatting
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR")
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET")
AVATAR_BUCKET = os.getenv("AVATAR_BUCKET")

def load_module(name, path):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except:
        return None

quiz_module = load_module("make_quiz", "make_quiz.py")
summarizer_module = load_module("summarizer", "summarizer.py")
keywords_module = load_module("keywords", "keywords.py")

QuizGenerator = getattr(quiz_module, "AdvancedEnglishQuizGenerator", None)
Summarizer = getattr(summarizer_module, "ExtendedLectureSummarizer", None)
KeywordExtractor = getattr(keywords_module, "KeywordExtractor", None)

quiz_gen, summarizer, kw_extractor = None, None, None

# PDF Library
PDF_LIB = None
try:
    import PyPDF2
    PDF_LIB = "PyPDF2"
except:
    try:
        import pdfplumber
        PDF_LIB = "pdfplumber"
    except:
        pass

# =============================================================================
# MODELS
# =============================================================================

class UserRegister(BaseModel):
    fullname: str
    email: EmailStr
    university: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    fullname: str
    email: str
    university: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

class CommentCreate(BaseModel):
    text: str

# =============================================================================
# UTILS
# =============================================================================

VN_MAP = str.maketrans(
    "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    "AAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD"
)

def safe_filename(name): 
    return name.translate(VN_MAP).replace(' ', '_').replace(',', '_')

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Debug-mode: use auto_error=False so we can log missing Authorization instead of FastAPI returning 403 early
security = HTTPBearer(auto_error=False)
security_opt = HTTPBearer(auto_error=False)

def hash_pw(pw):
    if len(pw.encode()) > 72:
        pw = hashlib.sha256(pw.encode()).hexdigest()
    return pwd_ctx.hash(pw)

def verify_pw(plain, hashed):
    try:
        if len(plain.encode()) > 72:
            plain = hashlib.sha256(plain.encode()).hexdigest()
        return pwd_ctx.verify(plain, hashed)
    except:
        return False

def make_token(email):
    exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": email, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

# =============================================================================
# DATABASE
# =============================================================================

pool: Optional[asyncpg.Pool] = None
storage: Optional[Client] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: initialize optional resources (DB pool, storage) and clean them up.
    No stdout logging to keep console clean in production.
    """
    global pool, storage

    # Initialize database pool (optional)
    pool = None
    if DATABASE_URL:
        try:
            # Disable statement cache to avoid issues with pgbouncer/connection pooling
            pool = await asyncpg.create_pool(
                DATABASE_URL, 
                min_size=1, 
                max_size=10,
                statement_cache_size=0  # Disable prepared statements cache
            )

            # Test connection
            try:
                async with pool.acquire() as conn:
                    await conn.execute("SELECT 1")
            except Exception:
                # If test query fails, don't keep a broken pool
                print("❌ DATABASE INIT FAILED:", Exception)
                await pool.close()
                pool = None
        except Exception as e:
            print("❌ DATABASE INIT FAILED:", e)
            pool = None
    # Initialize Supabase storage (optional)
    storage = None

    if SUPABASE_URL_RAW and SUPABASE_KEY:
        try:
            # Supabase client requires URL with trailing slash
            supabase_url_for_client = SUPABASE_URL_RAW.rstrip("/") + "/"
            storage = create_client(supabase_url_for_client, SUPABASE_KEY)
        except Exception:
            storage = None

    try:
        yield
    finally:
        # Cleanup
        if pool:
            try:
                await pool.close()
            except Exception:
                pass

# =============================================================================
# AUTH
# =============================================================================

async def get_user(request: Request, cred: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    # Debug log (no secrets)
    try:
        import json, time
        ah = request.headers.get("authorization")
        open(r'd:\Documents\GitHub\UniHub\.cursor\debug.log', 'a', encoding='utf-8').write(
            json.dumps({
                "sessionId": "debug-session",
                "runId": "pre-fix",
                "hypothesisId": "A",
                "location": "app.py:get_user",
                "message": "Auth header received",
                "data": {
                    "path": request.url.path,
                    "method": request.method,
                    "has_authorization_header": ah is not None,
                    "auth_scheme_prefix": (ah.split(" ", 1)[0] if ah else None),
                    "content_type": request.headers.get("content-type"),
                },
                "timestamp": int(time.time() * 1000),
            }) + "\n"
        )
    except Exception:
        pass

    if cred is None:
        # Missing/invalid Authorization header (previously surfaced as 403 by HTTPBearer)
        raise HTTPException(401, "Missing Authorization header")
    try:
        data = jwt.decode(cred.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = data.get("sub")
    except JWTError as e:
        # Debug log (no secrets)
        try:
            import json, time
            open(r'd:\Documents\GitHub\UniHub\.cursor\debug.log', 'a', encoding='utf-8').write(
                json.dumps({
                    "sessionId": "debug-session",
                    "runId": "pre-fix",
                    "hypothesisId": "C",
                    "location": "app.py:get_user",
                    "message": "JWT decode failed",
                    "data": {"error": str(e)},
                    "timestamp": int(time.time() * 1000),
                }) + "\n"
            )
        except Exception:
            pass
        raise HTTPException(401, "Invalid token")
    
    # If database is not available, return minimal user info from token
    if not pool:
        # Return a minimal user dict from JWT token (for upload when DB is down)
        return {
            "id": str(uuid.uuid4()),  # Generate a temporary ID
            "email": email,
            "fullname": email.split("@")[0],  # Use email prefix as fallback
            "university": "",
            "created_at": datetime.utcnow()
        }
    
    # Database is available - must query from database
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        
        if not row:
            raise HTTPException(401, "User not found")
        return dict(row)
    except (asyncpg.exceptions.InvalidSQLStatementNameError, asyncpg.exceptions.PostgresError) as e:
        # Database error - re-raise to prevent silent failures
        # This ensures we know when database operations fail
        raise HTTPException(503, f"Database error: {str(e)}")
    except Exception as e:
        # Other unexpected errors
        raise HTTPException(500, f"Internal server error: {str(e)}")

# =============================================================================
# APP
# =============================================================================

app = FastAPI(title="UniHub API", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.get("/api/health")
async def health():
    ok = False
    db_error = None
    if pool:
        try:
            async with pool.acquire() as c:
                await c.execute("SELECT 1")
                ok = True
        except Exception as e:
            db_error = str(e)
    else:
        db_error = "Database pool not initialized"
    
    return {
        "status": "ok" if ok else "degraded",
        "database": ok,
        "database_error": db_error if not ok else None
    }

@app.post("/api/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister):
    async with pool.acquire() as conn:
        if await conn.fetchrow("SELECT 1 FROM users WHERE email = $1", data.email):
            raise HTTPException(400, "Email exists")
        now = datetime.utcnow()
        row = await conn.fetchrow(
            "INSERT INTO users (fullname, email, university, password, created_at) VALUES ($1,$2,$3,$4,$5) RETURNING id",
            data.fullname, data.email, data.university, hash_pw(data.password), now
        )
    return TokenResponse(access_token=make_token(data.email), token_type="bearer",
        user=UserResponse(id=str(row["id"]), fullname=data.fullname, email=data.email, university=data.university, created_at=now))

@app.post("/api/login", response_model=TokenResponse)
async def login(data: UserLogin):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", data.email)
    if not row or not verify_pw(data.password, row["password"]):
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=make_token(data.email), token_type="bearer",
        user=UserResponse(id=str(row["id"]), fullname=row["fullname"], email=row["email"], university=row["university"], created_at=row["created_at"]))

@app.get("/api/me")
async def me(user: dict = Depends(get_user)):
    data = {"id": str(user["id"]), "fullname": user["fullname"], "email": user["email"], "university": user["university"], "created_at": user["created_at"]}
    if user.get("major"):
        data["major"] = user["major"]
    
    # Avatar URL from Supabase Storage (if exists)
    if storage and SUPABASE_URL:
        # Try common extensions - frontend will handle 404 if not found
        for ext in ['.jpg', '.png', '.gif', '.webp']:
            avatar_path = f"avatars/{user['id']}{ext}"
            data["avatar_url"] = f"{SUPABASE_URL}/storage/v1/object/public/{AVATAR_BUCKET}/{avatar_path}"
            break
    
    return data

@app.put("/api/profile/update")
async def update_profile(user: dict = Depends(get_user), fullname: Optional[str] = Form(None), 
    university: Optional[str] = Form(None), major: Optional[str] = Form(None), avatar: Optional[UploadFile] = File(None)):
    sets, params = [], []
    for name, val in [("fullname", fullname), ("university", university), ("major", major)]:
        if val:
            sets.append(f"{name} = ${len(params)+1}")
            params.append(val)
    if sets:
        params.append(user["email"])
        async with pool.acquire() as conn:
            await conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE email = ${len(params)}", *params)
    
    avatar_url = None
    if avatar:
        if not storage:
            raise HTTPException(503, "Storage not configured")
        
        ext = os.path.splitext(avatar.filename)[1] or '.jpg'
        avatar_path = f"avatars/{user['id']}{ext}"
        
        # Delete old avatars
        if storage:
            try:
                for e in ['.jpg', '.png', '.gif', '.webp']:
                    old_path = f"avatars/{user['id']}{e}"
                    try:
                        storage.storage.from_(AVATAR_BUCKET).remove([old_path])
                    except:
                        pass
            except:
                pass
        
        # Upload new avatar
        content = await avatar.read()
        try:
            storage.storage.from_(AVATAR_BUCKET).upload(avatar_path, content, {"content-type": avatar.content_type or "image/jpeg", "upsert": "true"})
            avatar_url = f"{SUPABASE_URL}/storage/v1/object/public/{AVATAR_BUCKET}/{avatar_path}"
        except Exception as e:
            raise HTTPException(500, f"Avatar upload failed: {e}")
    
    return {"message": "Updated", "avatar_url": avatar_url}

@app.post("/api/profile/change-password")
async def change_pw(data: ChangePassword, user: dict = Depends(get_user)):
    if not verify_pw(data.current_password, user["password"]):
        raise HTTPException(401, "Wrong password")
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET password = $1 WHERE email = $2", hash_pw(data.new_password), user["email"])
    return {"message": "Changed"}

# =============================================================================
# DOCUMENT ROUTES
# =============================================================================

def doc_dict(row, votes=0, comments=0, extra=None):
    d = {
        "id": str(row["id"]), "_id": str(row["id"]),
        "filename": row["filename"], 
        "storage_path": row.get("storage_path", ""),
        "content_type": row.get("content_type"),
        "size_bytes": row.get("size_bytes", 0),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "uploaded_by": str(row["uploaded_by"]) if row.get("uploaded_by") else None,
        "source_type": row.get("source_type", "upload"),
        "vote_count": votes, 
        "comment_count": comments, 
        "priority_score": votes * 2 + comments
    }
    if extra:
        d.update(extra)
    return d

@app.post("/uploadfile")
async def upload(file: UploadFile = File(...), user: dict = Depends(get_user)):
    
    if not storage:
        raise HTTPException(503, "Storage not configured")
    
    try:
        content = await file.read()
        safe = safe_filename(file.filename)
        storage_path = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{safe}"
        
        # Upload file to storage
        try:
            storage.storage.from_(STORAGE_BUCKET).upload(
                safe, content, 
                {"content-type": file.content_type or "application/octet-stream", "upsert": "true"}
            )
        except Exception as e:
            if "exists" not in str(e).lower():
                raise HTTPException(500, f"Upload failed: {e}")
        
        # Save to database if available
        doc_id = None
        if not pool:
            # Database not available, but file uploaded successfully
            return {
                "status": "success",
                "id": None,
                "url": storage_path,
                "filename": file.filename
            }
        
        # Database is available - must save to database
        try:
            # Handle user ID - could be UUID object from asyncpg or string
            user_id = user["id"]
            if isinstance(user_id, uuid.UUID):
                # Already a UUID object from asyncpg
                user_uuid = user_id
            elif isinstance(user_id, str):
                # Convert string to UUID
                try:
                    user_uuid = uuid.UUID(user_id)
                except (ValueError, TypeError):
                    raise HTTPException(500, "Invalid user ID format")
            else:
                # Try to convert to UUID
                try:
                    user_uuid = uuid.UUID(str(user_id))
                except (ValueError, TypeError):
                    raise HTTPException(500, "Invalid user ID format")
            
            # Insert into database - only new schema fields
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO documents (filename, storage_path, content_type, size_bytes, uploaded_by, source_type)
                    VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
                """, file.filename, storage_path, file.content_type, len(content), user_uuid, "upload")
                
                if not row:
                    raise HTTPException(500, "Failed to insert document into database")
                
                doc_id = str(row["id"])
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log the error for debugging
            import traceback
            error_details = f"Database save failed: {str(e)}\n{traceback.format_exc()}"
            # Raise error instead of silently failing
            raise HTTPException(500, f"Failed to save document to database: {str(e)}")
        
        return {"status": "success", "id": doc_id, "url": storage_path, "filename": file.filename}
    finally:
        await file.close()

@app.get("/documents/")
async def list_docs():
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM documents ORDER BY created_at DESC")
        result = []
        for r in rows:
            # Note: votes and comments tables may not exist in new schema
            # If they don't exist, these queries will fail - we'll catch and use 0
            try:
                v = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id = $1", r["id"]) or 0
            except:
                v = 0
            try:
                c = await conn.fetchval("SELECT COUNT(*) FROM comments WHERE document_id = $1", r["id"]) or 0
            except:
                c = 0
            result.append(doc_dict(r, v, c))
    return sorted(result, key=lambda x: -x["priority_score"])

@app.get("/api/my-uploads")
async def my_uploads(user: dict = Depends(get_user)):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM documents WHERE uploaded_by = $1 ORDER BY created_at DESC", user["id"])
        result = []
        for r in rows:
            try:
                v = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id=$1", r["id"]) or 0
            except:
                v = 0
            try:
                c = await conn.fetchval("SELECT COUNT(*) FROM comments WHERE document_id=$1", r["id"]) or 0
            except:
                c = 0
            result.append(doc_dict(r, v, c))
        return result

@app.get("/api/my-downloads")
async def my_downloads(user: dict = Depends(get_user)):
    # Note: downloads table may not exist in new schema
    if not pool:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT d.*, dl.downloaded_at as dl_at FROM documents d JOIN downloads dl ON d.id=dl.document_id WHERE dl.user_id=$1 ORDER BY dl.downloaded_at DESC", user["id"])
            result = []
            for r in rows:
                try:
                    v = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id=$1", r["id"]) or 0
                except:
                    v = 0
                try:
                    c = await conn.fetchval("SELECT COUNT(*) FROM comments WHERE document_id=$1", r["id"]) or 0
                except:
                    c = 0
                result.append(doc_dict(r, v, c, {"downloaded_at": r["dl_at"].isoformat() if r.get("dl_at") else None}))
            return result
    except Exception:
        # If downloads table doesn't exist, return empty list
        return []

@app.get("/api/my-favorites")
async def my_favorites(user: dict = Depends(get_user)):
    # Note: favorites table may not exist in new schema
    if not pool:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT d.*, f.favorited_at as fav_at FROM documents d JOIN favorites f ON d.id=f.document_id WHERE f.user_id=$1 ORDER BY f.favorited_at DESC", user["id"])
            result = []
            for r in rows:
                try:
                    v = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id=$1", r["id"]) or 0
                except:
                    v = 0
                try:
                    c = await conn.fetchval("SELECT COUNT(*) FROM comments WHERE document_id=$1", r["id"]) or 0
                except:
                    c = 0
                result.append(doc_dict(r, v, c, {"favorited_at": r["fav_at"].isoformat() if r.get("fav_at") else None}))
            return result
    except Exception:
        # If favorites table doesn't exist, return empty list
        return []

@app.post("/api/documents/{doc_id}/download")
async def track_dl(doc_id: str, user: dict = Depends(get_user)):
    # Note: downloads table may not exist in new schema
    if not pool:
        return {"status": "ok"}
    try:
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO downloads (document_id, user_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", uuid.UUID(doc_id), user["id"])
        return {"status": "ok"}
    except Exception:
        # If downloads table doesn't exist, still return ok
        return {"status": "ok"}

@app.get("/api/documents/{doc_id}/file")
async def get_document_file(doc_id: str):
    """Proxy endpoint to get document file from Supabase Storage"""
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT storage_path, content_type FROM documents WHERE id = $1", uid)
        if not row:
            raise HTTPException(404, "Document not found")
        
        file_url = row["storage_path"]
        content_type = row.get("content_type", "application/octet-stream")
        
        # Construct full Supabase URL
        if file_url.startswith("http://") or file_url.startswith("https://"):
            storage_url = file_url
        elif SUPABASE_URL:
            # Extract filename from saved_path if it's a relative path
            filename = file_url.split("/")[-1] if "/" in file_url else file_url
            storage_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"
        else:
            raise HTTPException(503, "Storage not configured")
        
        # Fetch file from Supabase and stream to client
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(storage_url, timeout=30.0, follow_redirects=True)
                if response.status_code != 200:
                    raise HTTPException(502, f"Failed to fetch file from storage: {response.status_code}")
                
                from fastapi.responses import Response
                return Response(
                    content=response.content,
                    media_type=content_type,
                    headers={
                        "Content-Disposition": f'inline; filename="{file_url.split("/")[-1]}"',
                        "Cache-Control": "public, max-age=3600"
                    }
                )
        except httpx.RequestError as e:
            raise HTTPException(502, f"Failed to fetch file: {str(e)}")

@app.post("/api/documents/{doc_id}/favorite")
async def toggle_fav(doc_id: str, user: dict = Depends(get_user)):
    # Note: favorites table may not exist in new schema
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID")
    
    if not pool:
        return {"is_favorited": False}
    
    try:
        async with pool.acquire() as conn:
            # Kiểm tra document tồn tại
            if not await conn.fetchrow("SELECT 1 FROM documents WHERE id=$1", uid):
                raise HTTPException(404, "Document not found")
                
            if await conn.fetchrow("SELECT 1 FROM favorites WHERE document_id=$1 AND user_id=$2", uid, user["id"]):
                await conn.execute("DELETE FROM favorites WHERE document_id=$1 AND user_id=$2", uid, user["id"])
                return {"is_favorited": False}
            await conn.execute("INSERT INTO favorites (document_id, user_id) VALUES ($1,$2)", uid, user["id"])
            return {"is_favorited": True}
    except Exception as e:
        # If favorites table doesn't exist, return False
        return {"is_favorited": False}

# =============================================================================
# COMMENTS & VOTES
# =============================================================================

@app.get("/api/documents/{doc_id}/comments")
async def get_comments(doc_id: str):
    # Note: comments table may not exist in new schema
    if not pool:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM comments WHERE document_id=$1 ORDER BY created_at DESC", uuid.UUID(doc_id))
        return [{"id": str(r["id"]), "author_name": r["author_name"], "text": r["text"], "created_at": r["created_at"].isoformat()} for r in rows]
    except Exception:
        return []

@app.post("/api/documents/{doc_id}/comments")
async def add_comment(doc_id: str, data: CommentCreate, user: dict = Depends(get_user)):
    # Note: comments table may not exist in new schema
    if not pool:
        raise HTTPException(503, "Database not available")
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow("INSERT INTO comments (document_id, author_id, author_name, text) VALUES ($1,$2,$3,$4) RETURNING id, created_at",
                uuid.UUID(doc_id), user["id"], user["fullname"], data.text)
        return {"id": str(r["id"]), "author_name": user["fullname"], "text": data.text, "created_at": r["created_at"].isoformat()}
    except Exception as e:
        raise HTTPException(503, f"Comments not available: {str(e)}")

@app.get("/api/documents/{doc_id}/votes")
async def get_votes(doc_id: str):
    # Note: votes table may not exist in new schema
    if not pool:
        return {"vote_count": 0}
    try:
        async with pool.acquire() as conn:
            c = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id=$1", uuid.UUID(doc_id))
        return {"vote_count": c or 0}
    except Exception:
        return {"vote_count": 0}

@app.get("/api/documents/{doc_id}/votes/check")
async def check_vote(doc_id: str, user: dict = Depends(get_user)):
    # Note: votes table may not exist in new schema
    if not pool:
        return {"has_voted": False}
    try:
        async with pool.acquire() as conn:
            r = await conn.fetchrow("SELECT 1 FROM votes WHERE document_id=$1 AND user_id=$2", uuid.UUID(doc_id), user["id"])
        return {"has_voted": r is not None}
    except Exception:
        return {"has_voted": False}

@app.post("/api/documents/{doc_id}/votes")
async def toggle_vote(doc_id: str, user: dict = Depends(get_user)):
    # Note: votes table may not exist in new schema
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(400, "Invalid document ID")
    
    if not pool:
        return {"action": "unvoted", "vote_count": 0, "has_voted": False}
    
    try:
        async with pool.acquire() as conn:
            if await conn.fetchrow("SELECT 1 FROM votes WHERE document_id=$1 AND user_id=$2", uid, user["id"]):
                await conn.execute("DELETE FROM votes WHERE document_id=$1 AND user_id=$2", uid, user["id"])
                action = "unvoted"
            else:
                await conn.execute("INSERT INTO votes (document_id, user_id) VALUES ($1,$2)", uid, user["id"])
                action = "voted"
            c = await conn.fetchval("SELECT COUNT(*) FROM votes WHERE document_id=$1", uid)
        return {"action": action, "vote_count": c or 0, "has_voted": action == "voted"}
    except Exception:
        return {"action": "unvoted", "vote_count": 0, "has_voted": False}

# =============================================================================
# QUIZ & PDF
# =============================================================================

def pdf_text(path):
    if not PDF_LIB:
        raise HTTPException(503, "No PDF library")
    text = ""
    if PDF_LIB == "pdfplumber":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for p in pdf.pages:
                t = p.extract_text()
                if t: text += t + "\n"
    else:
        import PyPDF2
        with open(path, 'rb') as f:
            for p in PyPDF2.PdfReader(f).pages:
                text += p.extract_text() + "\n"
    if not text.strip():
        raise HTTPException(400, "No text extracted")
    return text

def get_quiz():
    global quiz_gen
    if not quiz_gen and QuizGenerator:
        quiz_gen = QuizGenerator()
    return quiz_gen

def get_sum():
    global summarizer
    if not summarizer and Summarizer:
        summarizer = Summarizer()
    return summarizer

def get_kw():
    global kw_extractor
    if not kw_extractor and KeywordExtractor:
        kw_extractor = KeywordExtractor()
    return kw_extractor

def fmt_quiz(data, src):
    return {"quiz_title": data.get("quiz_title", f"Quiz: {src}"), "source_document": src, "total_questions": data.get("total_questions", 0),
        "questions": [{"id": q.get("id"), "question": q.get("question", ""), "options": q.get("options", {}),
            "correct_answer": q.get("correct_answer", ""), "explanation": q.get("explanation", "")} for q in data.get("questions", [])]}

@app.post("/api/generate-quiz-from-file")
async def quiz_file(file: UploadFile = File(...), num_questions: int = Form(10), user: dict = Depends(get_user)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "PDF only")
    tmp = f"{UPLOAD_DIR}/tmp_{file.filename}"
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        gen = get_quiz()
        if not gen:
            raise HTTPException(503, "Quiz unavailable")
        return fmt_quiz(gen.generate_complete_quiz(pdf_text(tmp), num_questions=num_questions), file.filename)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

@app.post("/api/generate-quiz-from-file-complete")
async def process_pdf(file: UploadFile = File(...), num_questions: int = Form(10),
    include_summary: bool = Form(True), include_keywords: bool = Form(True), user: dict = Depends(get_user)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "PDF only")
    tmp = f"{UPLOAD_DIR}/tmp_{file.filename}"
    try:
        with open(tmp, "wb") as f:
            shutil.copyfileobj(file.file, f)
        text = pdf_text(tmp)
        res = {"document_title": file.filename, "summary": None, "keywords": [], "quiz": None}
        
        if include_summary and (s := get_sum()):
            try: res["summary"] = s.get_summary_text(tmp)
            except: pass
        
        if include_keywords and (k := get_kw()):
            try: res["keywords"] = k.extract_from_text(res["summary"] or text, top_n=10)
            except: pass
        
        if g := get_quiz():
            try: res["quiz"] = fmt_quiz(g.generate_complete_quiz(res["summary"] or text, num_questions=num_questions), file.filename)
            except: pass
        
        return res
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

@app.get("/api/storage-url")
async def storage_url():
    return {"uploads": f"{SUPABASE_URL}/storage/v1/object/public/uploads", "data": f"{SUPABASE_URL}/storage/v1/object/public/data"}

# =============================================================================
# STATIC FILES & PROXY
# =============================================================================

# Proxy for data files from Supabase Storage
@app.get("/data/{filename:path}")
async def serve_data_file(filename: str):
    """Serve data files from Supabase Storage"""
    if not SUPABASE_URL:
        raise HTTPException(503, "Storage not configured")
    
    storage_url = f"{SUPABASE_URL}/storage/v1/object/public/data/{filename}"
    return RedirectResponse(url=storage_url)

# Proxy for uploads from Supabase Storage
@app.get("/uploads/{filename:path}")
async def serve_upload_file(filename: str):
    """Serve uploaded files from Supabase Storage"""
    if not SUPABASE_URL:
        raise HTTPException(503, "Storage not configured")
    
    storage_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{filename}"
    return RedirectResponse(url=storage_url)

# Mount public directory (HTML files only) - must be last
app.mount("/", StaticFiles(directory="public", html=True), name="public")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
