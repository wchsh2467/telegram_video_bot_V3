import os
import logging
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo, Message
from telethon.tl.custom import Button
from config.settings import API_ID, API_HASH, BOT_TOKEN, DOWNLOAD_PATH, TARGET_GROUP_ID, ADMIN_USER_ID
from services.video_service import VideoService
from services.user_service import UserService

# הגדרת הלוגר
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# יצירת אובייקט הבוט
client = TelegramClient('video_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# יצירת שירותים
video_service = VideoService(client, DOWNLOAD_PATH)
user_service = UserService()

@client.on(events.NewMessage(func=lambda e: e.media))
async def handle_video(event):
    """טיפול בהודעות וידאו"""
    message = event.message
    
    # בדיקת הרשאות המשתמש
    user_id_str = str(message.sender_id)
    if not user_service.is_user_allowed(user_id_str):
        await message.reply("אין לך הרשאה להשתמש בבוט זה. 🚫")
        return

    # בדיקה אם זו הודעת וידאו או מסמך
    if message.document:
        # בדיקת סיומת הקובץ
        file_name = message.file.name if message.file.name else ""
        if not file_name.lower().endswith(('.mkv', '.avi', '.mov', '.mp4', '.m4v', '.flv', '.webm', '.ts', '.mts', '.wmv', '.vob', '.dat', '.rm', '.rmvb', '.divx', '.Mpg', '.mpg')):
            await message.reply("הקובץ אינו בפורמט וידאו נתמך. 🚫")
            return

    # עיבוד הוידאו
    await video_service.process_video_message(message)

@client.on(events.NewMessage(pattern='/update', func=lambda e: e.is_private))
async def update_users(event):
    """עדכון רשימת המשתמשים המורשים"""
    message = event.message
    sender_id = message.sender_id  # כבר מספר, אין צורך בהמרה
    
    if sender_id != ADMIN_USER_ID:  # עכשיו משווים מספר למספר
        await message.reply("אין לך הרשאה לעדכן את רשימת המשתמשים. 🚫")
        return

    try:
        # קבלת רשימת המשתמשים החדשה
        new_users = message.text.split()[1:]
        if not new_users:
            await message.reply("אנא ציין רשימת מזהי משתמשים לעדכון.")
            return

        # עדכון רשימת המשתמשים
        added_count, invalid_ids = user_service.add_users(','.join(new_users))
        
        # יצירת הודעת תשובה
        response = f"נוספו {added_count} משתמשים בהצלחה."
        if invalid_ids:
            response += f"\nמזהים לא תקינים: {', '.join(invalid_ids)}"
        
        await message.reply(response)

    except Exception as e:
        logging.error(f"שגיאה בעדכון רשימת המשתמשים: {e}")
        await message.reply("אירעה שגיאה בעדכון רשימת המשתמשים.")

@client.on(events.NewMessage(pattern='/remove', func=lambda e: e.is_private))
async def remove_user(event):
    """הסרת משתמש מרשימת המורשים"""
    message = event.message
    sender_id = message.sender_id
    
    if sender_id != ADMIN_USER_ID:
        await message.reply("אין לך הרשאה להסיר משתמשים מהרשימה. 🚫")
        return

    try:
        # קבלת מזהה המשתמש להסרה
        args = message.text.split()
        if len(args) != 2:
            await message.reply("אנא ציין מזהה משתמש להסרה.\nלדוגמה: `/remove 123456789`")
            return
            
        user_id_to_remove = args[1]
        if not user_id_to_remove.isdigit():
            await message.reply("מזהה המשתמש חייב להיות מספר.")
            return
            
        # הסרת המשתמש
        if user_service.remove_user(int(user_id_to_remove)):
            await message.reply(f"משתמש {user_id_to_remove} הוסר בהצלחה מרשימת המורשים. ✅")
        else:
            await message.reply(f"משתמש {user_id_to_remove} לא נמצא ברשימת המורשים. ❌")

    except Exception as e:
        logging.error(f"שגיאה בהסרת משתמש: {e}")
        await message.reply("אירעה שגיאה בהסרת המשתמש.")

@client.on(events.CallbackQuery(pattern=r'^cancel_download_'))
async def handle_cancel_download(event):
    """טיפול בלחיצה על כפתור ביטול הורדה"""
    try:
        # חילוץ מזהה המשתמש מה-callback_data
        user_id = int(event.data.decode().split('_')[-1])
        
        # וידוא שהמשתמש מבטל את ההורדה שלו
        if event.sender_id != user_id:
            await event.answer("אינך יכול לבטל הורדות של משתמשים אחרים", alert=True)
            return
        
        await video_service.cancel_download(user_id)
        await event.answer("ההורדה מבוטלת...", alert=True)
    
    except Exception as e:
        logging.error(f"שגיאה בביטול ההורדה: {e}")
        await event.answer("אירעה שגיאה בביטול ההורדה", alert=True)

@client.on(events.CallbackQuery(pattern=r"cancel_upload_(\d+)"))
async def cancel_upload_handler(event):
    """טיפול בביטול העלאה"""
    user_id = int(event.pattern_match.group(1))
    if event.sender_id == user_id:
        await video_service.cancel_upload(user_id)
        await event.answer("ההעלאה בוטלה!")
    else:
        await event.answer("אתה לא יכול לבטל העלאה של משתמש אחר!")

if __name__ == "__main__":
    logging.info("מתחיל את הבוט")
    client.run_until_disconnected()
