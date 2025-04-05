import logging
from typing import Any, Iterator

from sqlalchemy import Connection, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import config

logger = logging.getLogger(__name__)


def on_connect(dbapi_con, connection_record):
    logger.info("Database connection established")


def on_checkout(dbapi_con, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")


def on_checkin(dbapi_con, connection_record):
    logger.debug("Database connection returned to pool")


class Base(DeclarativeBase):
    pass


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_engine(host, **engine_kwargs)
        self._sessionmaker = sessionmaker(autocommit=False, bind=self._engine)

        event.listen(self._engine, "connect", on_connect)
        event.listen(self._engine.pool, "checkout", on_checkout)
        event.listen(self._engine.pool, "checkin", on_checkin)

    def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    def connect(self) -> Iterator[Connection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise

    def session(self) -> Iterator[Session]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @property
    def engine(self):
        return self._engine


# https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine
sessionmanager = DatabaseSessionManager(
    config.DB_URL,
    dict(
        echo=True,
        pool_size=10,  # number of connections to keep open in the pool
        max_overflow=20,  # maximum number of connections allowed above the pool_size
        pool_recycle=15,  # seconds to wait before releasing a connection back to the pool
        pool_timeout=15,  # seconds to wait before giving up on getting a connection
    ),
)


def get_db():
    return next(sessionmanager.session())
