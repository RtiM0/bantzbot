import logging
import re
import sqlite3
import time
from datetime import time as t,datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

conn = sqlite3.connect('sqlite.db',check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS USERS (USER_ID integer primary key, JOIN_TIME integer, MESSAGES integer)")

NONCE_REGEX = r'm(?:an(?:chester | )?u|u(?:fc|n))|devils|u(?:nite|t)d|ggmu'
NOT_NONCE_REGEX = r'Peterborough|Chesterfield|Hartlepool|Colchester|Scunthorpe|sheffield|newcastle|Rotherham|(?:Southen|Herefor|Oxfor)d|Carlisle|west ham|Torquay|leeds'
VIDEO_FILE_ID = ""
TOKEN = ""

logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


def start(update, context):
    update.message.reply_text('no')

def tabledisplay_handler(update, context):
    cursor.execute("SELECT * FROM USERS")
    rows = cursor.fetchall()
    msg = "USER_ID\tJOIN_TIME\tMESSAGES\n"
    for row in rows:
        msg = msg + f"{row[0]}\t{str(datetime.fromtimestamp(row[1]))}\t{row[2]}\n"
    update.message.reply_text(msg)
    conn.commit()

def del_inactive(context):
    cursor.execute("SELECT * FROM USERS")
    rows = cursor.fetchall()
    for row in rows:
        if time.time() > row[1]+1800:
            cursor.execute("DELETE FROM USERS WHERE USER_ID=?",(row[0],))
    conn.commit()
    logger.info("Deleted inactive users from table")

def add_group(update, context):
    for member in update.message.new_chat_members:
        logger.info(f'Adding {member.full_name} - {member.id} to db')
        cursor.execute("INSERT OR IGNORE INTO USERS values(?,?,?)",(member.id,int(time.time()),0))
        logger.info(f"New Member {member.full_name} added to db")
    conn.commit()

def is_nonce(text):
    return re.search(NONCE_REGEX,text,re.IGNORECASE) and not re.search(NOT_NONCE_REGEX,text,re.IGNORECASE)

def msg(update, context):
    if update.effective_chat.type=='private':
        if is_nonce(update.message.text):
            update.message.reply_video(VIDEO_FILE_ID)
        else:
            update.message.reply_text("no")
    else:
        cursor.execute("SELECT * FROM USERS")
        rows = cursor.fetchall()
        for row in rows:
            if update.effective_user.id==row[0]:
                cursor.execute('UPDATE USERS SET MESSAGES=MESSAGES+1 WHERE USER_ID=?',(row[0],))
                cursor.execute('SELECT MESSAGES FROM USERS WHERE USER_ID=?',(row[0],))
                nrows = cursor.fetchall()
                msg_count = [nrow for nrow in nrows][0][0]
                logger.info(f"User {update.effective_user.full_name} sent his {msg_count} msg")
                if msg_count <= 5 and is_nonce(update.message.text):
                    logger.info(f"NOT ANOTHER ONE! {update.effective_user.full_name} was a nonce")
                    update.message.reply_video(VIDEO_FILE_ID)
                    cursor.execute('DELETE FROM USERS WHERE USER_ID=?',(row[0],))
                elif msg_count >= 5:
                    cursor.execute('DELETE FROM USERS WHERE USER_ID=?',(row[0],))
                    logger.info(f"User {update.effective_user.full_name} isnt a nonce")
                conn.commit()

def main():
    updater = Updater(TOKEN, use_context=True)

    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_handler(CommandHandler("start", start))
    # dispatcher.add_handler(CommandHandler("some_command", tabledisplay_handler))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, msg))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, add_group))

    job_queue.run_daily(del_inactive,t(0,0,0),name="delete inactive")

    updater.start_polling()
    logger.info("bot start")

    updater.idle()

if __name__ == '__main__':
    main()