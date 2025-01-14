import logging
from telethon import TelegramClient, events
from telethon.tl.types import Message
from services.user_service import UserService

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, client: TelegramClient, user_service: UserService):
        self.client = client
        self.user_service = user_service
        self._register_handlers()
        
    def _register_handlers(self):
        """רישום כל הפקודות"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_command(event):
            """טיפול בפקודת start"""
            await event.reply(
                "👋 שלום! אני בוט שמנתח קבצי וידאו ומספק מידע טכני עליהם.\n\n"
                "🎥 פשוט שלח לי קובץ וידאו ואני אטפל בו עבורך.\n\n"
                "⚡️ תכונות עיקריות:\n"
                "• המרה אוטומטית ל-MP4\n"
                "• זיהוי איכות הווידאו\n"
                "• שמירת קבצים לשימוש חוזר\n"
                "• תמיכה בכל סוגי הווידאו\n\n"
                "📝 פקודות נוספות:\n"
                "/help - הצגת עזרה מפורטת\n"
                "/about - מידע על הבוט"
            )
            
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_command(event):
            """טיפול בפקודת help"""
            await event.reply(
                "🔍 **מדריך שימוש**\n\n"
                "1️⃣ **שליחת וידאו**\n"
                "• שלח קובץ וידאו כלשהו\n"
                "• הבוט יעבד אותו אוטומטית\n"
                "• תקבל את הווידאו מעובד עם כל המידע\n\n"
                "2️⃣ **פורמטים נתמכים**\n"
                "• MP4, AVI, MKV, MOV, WMV ועוד\n"
                "• המרה אוטומטית ל-MP4\n\n"
                "3️⃣ **איכויות מזוהות**\n"
                "• 144p עד 4K\n"
                "• CAM, DVDRip, WEB-DL ועוד\n\n"
                "❓ לשאלות נוספות, פנה למנהל המערכת"
            )
            
        @self.client.on(events.NewMessage(pattern='/about'))
        async def about_command(event):
            """טיפול בפקודת about"""
            await event.reply(
                "ℹ️ **אודות הבוט**\n\n"
                "🤖 **שם:** Video Info Bot\n"
                "📝 **תיאור:** בוט לניתוח ועיבוד קבצי וידאו\n"
                "🛠 **יכולות:**\n"
                "• ניתוח קבצי וידאו\n"
                "• המרת פורמטים\n"
                "• זיהוי איכות\n"
                "• שמירה לשימוש חוזר\n\n"
                "👨‍💻 **פיתוח:** Python + Telethon\n"
                "📅 **גרסה:** 3.0.0\n"
            )
            
        @self.client.on(events.NewMessage(pattern=r'/(?:adduser|removeuser)\s+\d+', from_users=1681880347))
        async def manage_users(event):
            """טיפול בפקודות ניהול משתמשים"""
            try:
                command = event.pattern_match.string.split()[0][1:]  # הסרת ה-/ מתחילת הפקודה
                user_id = int(event.pattern_match.string.split()[1])
            except (IndexError, ValueError):
                await event.reply("❌ שימוש שגוי. דוגמה: /adduser 123456789")
                return
                
            if command == "adduser":
                if self.user_service.add_user(user_id):
                    await event.reply(f"✅ משתמש {user_id} נוסף בהצלחה")
                else:
                    await event.reply(f"ℹ️ משתמש {user_id} כבר קיים במערכת")
            else:  # removeuser
                if self.user_service.remove_user(user_id):
                    await event.reply(f"✅ משתמש {user_id} הוסר בהצלחה")
                else:
                    await event.reply(f"❌ משתמש {user_id} לא נמצא במערכת")
                    
        @self.client.on(events.NewMessage(pattern='/users', from_users=1681880347))
        async def list_users(event):
            """הצגת רשימת משתמשים מורשים"""
            users = self.user_service.get_allowed_users()
            if users:
                users_text = "\n".join([f"• `{user}`" for user in users])
                await event.reply(
                    f"👥 **משתמשים מורשים:**\n\n{users_text}\n\n"
                    f"סה\"כ: {len(users)} משתמשים"
                )
            else:
                await event.reply("❌ אין משתמשים מורשים במערכת")
