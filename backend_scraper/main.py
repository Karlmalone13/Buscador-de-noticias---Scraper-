from fastapi import FastAPI, Depends, HTTPException         
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from database import engine, get_db
from models import Base, Topic, News
from collector import collect_all_topics

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="News Monitor API",
    description="Sistema de monitoramento de notícias por tema",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = BackgroundScheduler()
scheduler.add_job(collect_all_topics, "interval", minutes=30, id="collect_news")
scheduler.start()


# ---------- Schemas ----------

class TopicCreate(BaseModel):
    name: str
    query: str


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    query: Optional[str] = None
    active: Optional[bool] = None


class TopicResponse(BaseModel):
    id: int
    name: str
    query: str
    active: bool
    created_at: datetime
    news_count: int = 0

    class Config:
        from_attributes = True


class NewsResponse(BaseModel):
    id: int
    topic_id: int
    topic_name: str
    title: str
    url: str
    source: str
    snippet: str
    published_at: str
    collected_at: datetime

    class Config:
        from_attributes = True


# ---------- Endpoints de Temas ----------

@app.get("/topics", response_model=list[TopicResponse])
def list_topics(db: Session = Depends(get_db)):
    topics = db.query(Topic).order_by(Topic.created_at.desc()).all()
    result = []
    for t in topics:
        count = db.query(News).filter(News.topic_id == t.id).count()
        result.append(TopicResponse(
            id=t.id,
            name=t.name,
            query=t.query,
            active=t.active,
            created_at=t.created_at,
            news_count=count
        ))
    return result


@app.post("/topics", response_model=TopicResponse, status_code=201)
def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    existing = db.query(Topic).filter(Topic.name == topic.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tema já cadastrado")

    new_topic = Topic(name=topic.name, query=topic.query)
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    collect_all_topics()

    return TopicResponse(
        id=new_topic.id,
        name=new_topic.name,
        query=new_topic.query,
        active=new_topic.active,
        created_at=new_topic.created_at,
        news_count=0
    )


@app.patch("/topics/{topic_id}", response_model=TopicResponse)
def update_topic(topic_id: int, data: TopicUpdate, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Tema não encontrado")

    if data.name is not None:
        topic.name = data.name
    if data.query is not None:
        topic.query = data.query
    if data.active is not None:
        topic.active = data.active

    db.commit()
    db.refresh(topic)
    count = db.query(News).filter(News.topic_id == topic.id).count()

    return TopicResponse(
        id=topic.id,
        name=topic.name,
        query=topic.query,
        active=topic.active,
        created_at=topic.created_at,
        news_count=count
    )


@app.delete("/topics/{topic_id}", status_code=204)
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Tema não encontrado")
    db.delete(topic)
    db.commit()


# ---------- Endpoints de Notícias ----------

@app.get("/news", response_model=list[NewsResponse])
def list_news(
    topic_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(News, Topic.name).join(Topic, News.topic_id == Topic.id)

    if topic_id:
        query = query.filter(News.topic_id == topic_id)

    results = query.order_by(News.collected_at.desc()).offset(offset).limit(limit).all()

    return [
        NewsResponse(
            id=n.id,
            topic_id=n.topic_id,
            topic_name=name,
            title=n.title,
            url=n.url,
            source=n.source or "",
            snippet=n.snippet or "",
            published_at=n.published_at or "",
            collected_at=n.collected_at
        )
        for n, name in results
    ]


@app.get("/news/count")
def count_news(db: Session = Depends(get_db)):
    total = db.query(News).count()
    by_topic = (
        db.query(Topic.name, Topic.id)
        .join(News, Topic.id == News.topic_id)
        .group_by(Topic.id)
        .all()
    )
    counts = []
    for name, tid in by_topic:
        c = db.query(News).filter(News.topic_id == tid).count()
        counts.append({"topic": name, "count": c})

    return {"total": total, "by_topic": counts}


# ---------- Coleta manual ----------

@app.post("/collect", status_code=200)
def trigger_collect():
    collect_all_topics()
    return {"message": "Coleta executada com sucesso"}


@app.get("/")
def root():
    return {"status": "ok", "message": "News Monitor API rodando"}
