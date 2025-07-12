import asyncio
import aiosqlite
import datetime
import logging
import os
import common
from pathlib import Path

#from shutdown import shutdown_task

DB_NAME = "messages.db"
TABLE_NAME = "messages"

ROTATE_FILE_PATH = "db/rotate"

STATE_PENDING = "PENDING"
STATE_DONE = "DONE"

log = logging.getLogger(__name__)


class Msg:
    def __init__(self, rec):
        self.msg_id = rec[0]
        self.topic = rec[1]
        self.msg:str = rec[2]
        self.state = rec[3]
        self.created = rec[4]
        self.sent = rec[5]
        self.created_date = datetime.datetime.fromtimestamp(self.created)
        if self.sent:
            self.sent_date = datetime.datetime.fromtimestamp(self.sent)
        else:
            self.sent_date = None

    def __str__(self):
        return "Id: %d, %s, %s, %s, Created: %s, Sent: %s" % \
            (self.msg_id, self.topic, self.state, self.msg, str(self.created_date), str(self.sent_date))


class MsgDb:
    def __init__(self):
        self.db = None

    @classmethod
    def validate_ready(cls):
        if not os.path.isdir("db"):
            log.error("No db directory exists")
            raise Exception("No 'db' directory exists")

        if os.path.exists(ROTATE_FILE_PATH):
            now = datetime.datetime.now()
            backup_file = "db/" + now.strftime('%Y%m%d_%H%M%S') + "_" + DB_NAME
            log.info("Rotating DB to " + backup_file)
            os.rename("db/" + DB_NAME, backup_file)
            os.unlink(ROTATE_FILE_PATH)
            os.spawnl(os.P_NOWAIT, '/bin/gzip', '-f', backup_file)

    # @classmethod
    # async def rotate_initiate(cls):
    #     log.info("Initiating rotation")
    #     Path(ROTATE_FILE_PATH).touch()
    #     await asyncio.create_task(shutdown_task())

    async def connect(self):
        self.db = await aiosqlite.connect("./db/%s" % DB_NAME)
        log.info("MsDb connected")
        #await self.drop_table()
        await self.check_create_table()

    async def close(self):
        log.info("MsDb closing")
        await self.db.close()

    async def list_tables(self):
        sql = "SELECT name FROM sqlite_master WHERE type='table';"
        cursor = await self.db.execute(sql)
        rows = await cursor.fetchall()
        tables = []
        for row in rows:
            tables.append(row[0])
        await cursor.close()
        return tables

    async def check_create_table(self):
        tables = await self.list_tables()
        if TABLE_NAME in tables:
            return
        log.info("CREATE TABLE " + TABLE_NAME)
        sql = """CREATE TABLE IF NOT EXISTS %s (
            id integer PRIMARY KEY AUTOINCREMENT,
            topic text NOT NULL,
            msg text NOT NULL,
            state text,
            created int,
            sent int
        ); """ % TABLE_NAME
        await self.db.execute(sql)
        sql = "CREATE INDEX idx_messages_state ON %s (state);" % TABLE_NAME
        await self.db.execute(sql)

    async def drop_table(self):
        log.info("DROP TABLE " + TABLE_NAME)
        sql = "DROP TABLE {table};".format(table=TABLE_NAME)
        await self.db.execute(sql)

    async def pending_msg_get(self) -> Msg:
        sql = "SELECT id, topic, msg, state, created, sent FROM %s WHERE state = '%s' ORDER BY id ASC LIMIT 1;" \
             % (TABLE_NAME, STATE_PENDING)
        cursor = await self.db.execute(sql)
        row = await cursor.fetchone()
        await cursor.close()
        if not row:
            return None
        #log.info(row)
        msg = Msg(row)
        log.info("Pending msg: %s" % msg.msg_id)
        log.debug("Pending msg: %s" % msg)
        return msg

    async def insert_message(self, topic: str, msg:str) -> int:
        state = STATE_PENDING
        log.debug("Inserting: " + msg)
        sql = "INSERT INTO %s (topic, msg, state, created) VALUES(?, ?, ?, ?);" % TABLE_NAME
        now = int(datetime.datetime.now().timestamp())
        data = (topic, msg, state, now)
        await self.db.execute(sql, data)
        await self.db.commit()
        sql = "SELECT last_insert_rowid()"
        cursor = await self.db.execute(sql)
        row = await cursor.fetchone()
        msg_id = row[0]
        await cursor.close()
        log.debug("Created message: " + str(msg_id))
        return msg_id

    async def delete_message(self, msg:Msg):
        sql = "DELETE FROM %s WHERE id = %d;" % (TABLE_NAME, msg.msg_id)
        await self.db.execute(sql)
        await self.db.commit()
        log.debug("Updated done: %d", msg.msg_id)

    async def update_done(self, msg:Msg):
        now = int(datetime.datetime.now().timestamp())
        sql = "UPDATE %s SET state = '%s', sent= %d WHERE id = %d;" % (TABLE_NAME, STATE_DONE, now, msg.msg_id)
        await self.db.execute(sql)
        await self.db.commit()
        log.debug("Updated done: %d", msg.msg_id)



async def main():
    common.setup_logging()
    log.info("start")
    db = MsgDb()
    await db.connect()
    id = await db.insert_message("Messaage")
    msg = await db.pending_msg_get()
    await db.update_done(msg)
    log.info(msg)
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
