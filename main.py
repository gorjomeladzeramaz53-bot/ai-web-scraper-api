from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
DATABASE_URL = "sqlite:///./scraper.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ScrapedDataModel(Base):
    __tablename__ = "scraped_data"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    title = Column(String)
    text_snippet = Column(Text)
    links_count = Column(Integer)
    images_count = Column(Integer)
    scraped_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Web Scraper & Intelligence API", version="1.0.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ScrapeRequest(BaseModel):
    url: HttpUrl

@app.get("/")
def home():
    return {"message": "AI Web Scraper & Intelligence API is running!"}

@app.post("/scrape")
async def scrape_website(payload: ScrapeRequest, db: Session = Depends(get_db)):
    target_url = str(payload.url)
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(target_url)
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch URL. Status code: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
        
        text_content = " ".join([p.get_text() for p in soup.find_all("p")])
        snippet = text_content[:500] if text_content else "No text found"

        links_count = len(soup.find_all("a"))
        images_count = len(soup.find_all("img"))

        db_item = ScrapedDataModel(
            url=target_url,
            title=title,
            text_snippet=snippet,
            links_count=links_count,
            images_count=images_count
        )
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        return {
            "status": "success",
            "url": target_url,
            "title": title,
            "links_count": links_count,
            "images_count": images_count,
            "snippet": snippet
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    items = db.query(ScrapedDataModel).order_by(ScrapedDataModel.scraped_at.desc()).limit(10).all()
    return items
