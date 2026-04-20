from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine, select

DATABASE_URL = "sqlite:///./xdr.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    
    # Create default admin user if it doesn't exist
    with Session(engine) as session:
        from src.models import User
        from src.security import hash_password
        
        admin = session.exec(select(User).where(User.username == "admin")).first()
        if not admin:
            admin_user = User(
                username="admin",
                email="admin@xdr.local",
                full_name="Administrator",
                hashed_password=hash_password("password123"),
                is_active=True,
                role="admin",
            )
            session.add(admin_user)
            session.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
