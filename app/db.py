from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLAlchemy sync engine (simple + robust for deployment)
# If you use Supabase pooler at high scale, you may want to tune pooling.
def make_engine(database_url: str):
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=1800,
    )

def make_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
