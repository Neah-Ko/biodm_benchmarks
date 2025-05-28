from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Project, ProjectCreateSchema


async def read(s: AsyncSession, id: int):
    return await s.query(Project).filter(Project.id == id).first()


async def read_all(s: AsyncSession, short_name: str):
    stmt = select(Project)
    if short_name:
        stmt = stmt.where(Project.short_name.ilike(short_name.replace('*', '%')))
    return (await s.execute(stmt)).scalars().unique().all()


async def create(s: AsyncSession, project: ProjectCreateSchema):
    db_item = Project(**project.model_dump())
    s.add(db_item)
    await s.commit()
    await s.refresh(db_item)
    return db_item


# async def create_blog(blog: BlogCreate):
#     # Simulate saving to DB
#     return {"id": 1, "title": blog.title, "content": blog.content, "created_at": datetime.now()}

# async def update_blog(blog_id: int, blog: BlogUpdate):
#     # Simulate updating DB
#     return {"id": blog_id, "title": blog.title or "Unchanged", "content": blog.content or "Unchanged", "created_at": datetime.now()}
