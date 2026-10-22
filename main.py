from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, HttpUrl
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime

# SlowAPI იმპორტი Rate Limiting-ისთვის
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ---------------------------------------------------------
# 0. Limiter კონფიგურაცია (მაგ: 5 მოთხოვნა წუთში ერთ IP-ზე)
# ---------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

# ---------------------------------------------------------
# 1. API Key Security კონფიგურაცია
# ---------------------------------------------------------
API_KEY_NAME = "x-api-key"
VALID_API_KEY = "my-secret-scraper-key-2026"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != VALID_API_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Forbidden: Invalid or missing API Key"
        )
    return api_key

# ---------------------------------------------------------
# 2. მონაცემთა ბაზის კონფიგურაცია (SQLAlchemy)
# ---------------------------------------------------------
DATABASE_URL = "sqlite:///./scraper.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScrapeHistory(Base):
    __tablename__ = "scrape_history"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    links_count = Column(Integer)
    images_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# 3. FastAPI აპლიკაციის ინიციალიზაცია
# ---------------------------------------------------------
app = FastAPI(
    title="AI Web Scraper & Intelligence API",
    description="Asynchronous Web Scraping API with SQLite database, API Key authentication, and Rate Limiting.",
    version="2.1.0"
)

# მივამმაგროთ Rate Limiter ჰენდლერი აპლიკაციას
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class ScrapeRequest(BaseModel):
    url: HttpUrl

# ---------------------------------------------------------
# 4. API ენდფოინთები (Endpoints)
# ---------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Welcome to AI Web Scraper API",
        "status": "active",
        "docs": "/docs"
    }

@app.post("/scrape")
@limiter.limit("5/minute")  # 🛑 ლიმიტი: მაქსიმუმ 5 მოთხოვნა 1 წუთში ერთ IP-ზე
async def scrape_website(
    request: Request, # საჭიროა slowapi-სთვის
    body: ScrapeRequest, 
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    target_url = str(body.url)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(target_url)
            
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch site. HTTP Status: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title Found"
        links = [a.get("href") for a in soup.find_all("a", href=True)]
        images = [img.get("src") for img in soup.find_all("img", src=True)]
        
        paragraphs = [p.text.strip() for p in soup.find_all("p") if p.text.strip()]
        snippet = " ".join(paragraphs[:3])[:300] if paragraphs else "No text found"

        history_entry = ScrapeHistory(
            url=target_url,
            title=title,
            links_count=len(links),
            images_count=len(images)
        )
        db.add(history_entry)
        db.commit()
        db.refresh(history_entry)

        return {
            "status": "success",
            "data": {
                "id": history_entry.id,
                "url": target_url,
                "title": title,
                "snippet": snippet,
                "stats": {
                    "links_count": len(links),
                    "images_count": len(images)
                },
                "scraped_at": history_entry.created_at
            }
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error occurred: {str(e)}")

@app.get("/history")
@limiter.limit("10/minute") # ლიმიტი ისტორიის ენდფოინთისთვისაც
def get_history(
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    history = db.query(ScrapeHistory).order_by(ScrapeHistory.created_at.desc()).all()
    return {"status": "success", "count": len(history), "data": history}
