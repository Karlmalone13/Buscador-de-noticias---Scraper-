import feedparser
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Topic, News
from urllib.parse import quote


def search_news(query: str, num: int = 20) -> list[dict]:
    query_encoded = quote(query)
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419" #Coletor RSS, buscador

    try:
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:num]:
            source = ""
            if hasattr(entry, "source") and isinstance(entry.source, dict):
                source = entry.source.get("title", "")
            elif hasattr(entry, "tags") and entry.tags:
                source = entry.tags[0].get("term", "")

            # Pega o título sem o nome da fonte (Google News coloca " - Fonte" no final)
            title = entry.get("title", "Sem título")
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                if not source:
                    source = parts[1]

            articles.append({
                "title": title,
                "url": entry.get("link", ""),
                "source": source,
                "snippet": entry.get("summary", ""),
                "published_at": entry.get("published", ""),
            })

        return articles

    except Exception as e:
        print(f"[ERRO] {e}")
        return []


def save_news(db: Session, topic_id: int, articles: list[dict]) -> int:
    saved = 0
    for article in articles:
        url = article.get("url", "")
        if not url:
            continue

        existing = db.query(News).filter(News.url == url).first()
        if existing:
            continue

        news = News(
            topic_id=topic_id,
            title=article.get("title", "Sem título"),
            url=url,
            source=article.get("source", ""),
            snippet=article.get("snippet", ""),
            published_at=article.get("published_at", ""),
            collected_at=datetime.now(),
        )
        db.add(news)
        saved += 1

    db.commit()
    return saved


def collect_all_topics():
    db = SessionLocal()
    try:
        topics = db.query(Topic).filter(Topic.active == True).all()

        if not topics:
            print("[INFO] Nenhum tema cadastrado ainda.")
            return

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Coletando {len(topics)} tema(s)...")

        for topic in topics:
            print(f"  → Buscando: {topic.name}")
            articles = search_news(topic.query)
            count = save_news(db, topic.id, articles)
            print(f"     {count} nova(s) notícia(s) salva(s)")

    finally:
        db.close()


if __name__ == "__main__":
    collect_all_topics()