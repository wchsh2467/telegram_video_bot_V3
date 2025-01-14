import re
import os
import asyncio
import logging
from config.settings import VIDEO_FORMATS

def clean_filename(filename: str) -> str:
    """ניקוי שם הקובץ מתווים לא חוקיים"""
    return re.sub(r'[<>:"/\\|?*_]', ' ', filename)

def get_video_caption(file_path: str) -> str:
    """יצירת כיתוב לוידאו מתוך שם הקובץ"""
    # הסרת הסיומת מהקובץ ליצירת הכיתוב
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    pixel_format_match = None
    other_format_match = None

    # חיפוש התאמות בפורמטים
    for fmt in VIDEO_FORMATS['PIXEL']:
        if fmt in file_name:
            pixel_format_match = fmt
            file_name = file_name.replace(fmt, '').strip()
            break

    for fmt in VIDEO_FORMATS['OTHER']:
        if fmt in file_name:
            other_format_match = fmt
            file_name = file_name.replace(fmt, '').strip()
            break

    # יצירת מידע על האיכות
    quality_info = ""
    if pixel_format_match or other_format_match:
        quality_info = f"איכות: {other_format_match}, {pixel_format_match}".strip(", ")

    # יצירת הכיתוב הסופי
    caption = f"**{file_name}**"
    if quality_info:
        caption += f"\n**{quality_info}**"
    
    return caption

def get_file_name(message):
    """קבלת שם הקובץ המקורי מהודעת טלגרם
    
    דוגמה:
    אם נשלח קובץ בשם "funny_cat_2024.mp4":
    - הפונקציה תחזיר: "funny_cat_2024.mp4"
    
    אם נשלח קובץ בלי שם:
    - הפונקציה תחזיר: "video.mp4"
    """
    if message.media and hasattr(message.media, 'document'):
        for attr in message.media.document.attributes:
            if hasattr(attr, 'file_name'):
                return attr.file_name
    return "video.mp4"

async def wait_for_file_release(file_path: str) -> None:
    """המתנה עד שהקובץ משתחרר מתהליכים אחרים"""
    while True:
        try:
            os.rename(file_path, file_path)
            break
        except OSError:
            await asyncio.sleep(2)

async def wait_and_delete(file_path: str) -> None:
    """המתנה ומחיקת קובץ עם ניסיונות חוזרים"""
    while True:
        try:
            os.remove(file_path)
            logging.info(f"הקובץ {file_path} נמחק בהצלחה.")
            return
        except OSError:
            logging.warning(f"נכשל במחיקת {file_path}. מנסה שוב בעוד 2 שניות...")
            await asyncio.sleep(2)
