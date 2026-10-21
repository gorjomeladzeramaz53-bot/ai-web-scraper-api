from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import re

app = FastAPI(
    title="AI Text Summarizer & Analytics API",
    description="ტექსტის ანალიზისა და შეჯამების API პორტფოლიოსთვის",
    version="1.0.0"
)

class TextRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "კეთილი იყოს თქვენი მობრძანება AI Text Summarizer API-ში!",
        "docs_url": "/docs"
    }

@app.post("/analyze")
def analyze_text(data: TextRequest):
    content = data.text.strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="გთხოვთ, შეიყვანოთ ტექსტი!")
    
    # სიტყვების და წინადადებების დათვლა
    words = re.findall(r'\w+', content)
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    word_count = len(words)
    sentence_count = len(sentences)
    
    # წაკითხვის სავარაუდო დრო (საშუალოდ 200 სიტყვა წუთში)
    reading_time_minutes = round(word_count / 200, 2)
    
    # მარტივი შეჯამება (პირველი 2 წინადადება)
    summary = " ".join(sentences[:2]) if sentences else content[:100]
    
    # ყველაზე ხშირი სიტყვების პოვნა (საკვანძო სიტყვები)
    word_freq = {}
    for word in words:
        w = word.lower()
        if len(w) > 3:  # მხოლოდ 3 ასოზე მეტი სიგრძის სიტყვები
            word_freq[w] = word_freq.get(w, 0) + 1
            
    top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:5]
    
    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "estimated_reading_time_minutes": reading_time_minutes,
        "summary": summary,
        "top_keywords": top_keywords
    }