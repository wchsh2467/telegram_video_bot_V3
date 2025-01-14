import logging
from telethon import TelegramClient, events
from telethon.tl.types import Message, Document

from services.user_service import UserService
from services.video_service import VideoService

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self, client: TelegramClient, user_service: UserService, video_service: VideoService):
        self.client = client
        self.user_service = user_service
        self.video_service = video_service
        self._register_handlers()
        
    def _register_handlers(self):
        """רישום כל המטפלים בהודעות"""
        
        @self.client.on(events.NewMessage(func=lambda e: e.is_private and (e.media or e.document)))
        async def handle_video(event):
            """טיפול בקבצי וידאו"""
            logger.info(f"התקבלה הודעת וידאו/מסמך מ: {event.sender_id}")
            
            user_id = event.sender_id
            
            # בדיקת הרשאות
            if not self.user_service.is_user_allowed(user_id):
                logger.warning(f"משתמש לא מורשה {user_id} ניסה להשתמש בבוט")
                await event.reply(
                    "**📛 אין לך הרשאה להשתמש בבוט זה**\n"
                    "אנא פנה למנהל המערכת"
                )
                return
                
            # בדיקה שזה אכן קובץ וידאו
            if isinstance(event.media, Document):
                mime_type = event.media.mime_type
                logger.info(f"סוג המסמך: {mime_type}")
                if not (mime_type and mime_type.startswith("video/")):
                    await event.reply("❌ אנא שלח קובץ וידאו בלבד")
                    return
                
            # הוספה לתור העיבוד
            await self.video_service.add_to_queue(event.message)
            logger.info(f"התקבל וידאו חדש ממשתמש {user_id}")
            await event.reply("✅ הקובץ התקבל ומעובד...")
            
        @self.client.on(events.NewMessage(func=lambda e: e.is_private and e.text and not e.text.startswith('/')))
        async def handle_text(event):
            """טיפול בהודעות טקסט"""
            logger.info(f"התקבלה הודעת טקסט מ: {event.sender_id}")
            await event.reply(
                "🎥 אנא שלח קובץ וידאו לניתוח\n\n"
                "לעזרה נוספת, השתמש בפקודה /help"
            )
