from sqlalchemy.orm import Query
from typing import TypeVar, List, Tuple

T = TypeVar("T")

def paginate(query: Query, page: int, page_size: int) -> Tuple[List[T], int, int]:
    """
    Generic pagination helper for SQLAlchemy queries.
    Returns: (items, total_count, total_pages)
    """
    total = query.count()
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    if page < 1:
        page = 1
        
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    return items, total, total_pages
