from __future__ import annotations
from typing import Callable, cast
import asyncio
import asyncpg  # type: ignore


from sqlalchemy import text

from src.database.postgres import PostgresDatabase


class KeepAlive:

    def __init__(self) -> None:
        self.keep_alive = True

    def stop(self) -> None:
        self.keep_alive = False


def get_db_url(db: PostgresDatabase) -> str:
    password = cast(str, db.engine.url.password)
    url = str(db.engine.url)
    url = url.replace(
        "***", password
    )  # __repr__ hides the password, hide_password=False seems to not work
    url = url.replace("+psycopg2", "")
    return url


async def listen_to_notifications(
    db: PostgresDatabase,
    handler: Callable[[str, str, str, str], None],
    keep_alive: KeepAlive = KeepAlive(),
) -> None:
    url = get_db_url(db)

    conn = await asyncpg.connect(url)
    await conn.add_listener("event_insert", handler)
    try:
        while keep_alive.keep_alive:
            await asyncio.sleep(1)
    finally:
        await conn.close()


def add_notification_function(db: PostgresDatabase) -> None:
    with db.transaction(parent=None) as sub_con:
        sql = text(
            f"""
CREATE FUNCTION notify_event_insert() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('event_insert', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER event_insert_trigger
AFTER INSERT ON events
FOR EACH ROW
EXECUTE FUNCTION notify_event_insert();"""
        )
        sub_con.execute(sql)
