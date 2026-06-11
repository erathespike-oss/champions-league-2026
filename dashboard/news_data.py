from dataclasses import dataclass
from typing import Optional, List

@dataclass
class NewsItem:
    id: int
    title: str
    date: str
    tag: str
    tag_color: str  # hex color
    image_url: Optional[str] = None

# Placeholder data - user will fill this later
NEWS_LIST: List[NewsItem] = [
    NewsItem(
        id=1,
        title="Винисиус Жуниор - футболист 2024 года - Анчелотти, Ямаль и Мартинес с призами",
        date="18-12-2024",
        tag="По версии FIFA",
        tag_color="#00aaff",
        image_url="/static/dashboard/images/news/id1.jpg"
    ),
    NewsItem(
        id=2,
        title="Все победители Лиги Чемпионов с сезона 1992/93",
        date="15-12-2024",
        tag="От Марселя до Мадрида",
        tag_color="#00aaff",
        image_url="/static/dashboard/images/news/id2.png"
    ),
    NewsItem(
        id=3,
        title="Лучшие игроки из Азии в Лиге чемпионов: Тареми, Сон, Минамино, Шацких",
        date="15-12-2024",
        tag="По версии FIFA",
        tag_color="#00cc66",
        image_url="/static/dashboard/images/news/id3.avif"
    )
]
