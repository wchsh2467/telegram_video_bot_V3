import asyncio
import time
import logging
from typing import List


class RateLimiter:
    """מנהל השהיות להודעות טלגרם
    
    מגבלות טלגרם:
    - צ'אט פרטי: הודעה 1 בשנייה (60 בדקה)
    - קבוצה: 20 הודעות בדקה
    - שידור המוני: 30 הודעות בשנייה (עם תשלום)
    
    דוגמאות לשימוש:
    ```python
    # יצירת מגביל לצ'אט פרטי
    private_limiter = RateLimiter(messages_per_minute=60, limiter_type="private")
    
    # שימוש במגביל
    async with private_limiter:
        await message.edit("עדכון סטטוס")
    
    # יצירת מגביל לקבוצה
    group_limiter = RateLimiter(messages_per_minute=20, limiter_type="group")
    
    # שימוש במגביל
    async with group_limiter:
        await bot.send_message(group_id, "הודעה לקבוצה")
    ```
    """
    
    def __init__(self, messages_per_minute: int, limiter_type: str = "private"):
        """אתחול מגביל הקצב
        
        Args:
            messages_per_minute (int): כמות ההודעות המקסימלית בדקה
            limiter_type (str): סוג המגביל ("private" או "group")
        """
        self.messages_per_minute = messages_per_minute
        self.min_interval = 60.0 / messages_per_minute
        self.limiter_type = limiter_type
        self.lock = asyncio.Lock()
        self.message_times: List[float] = []
        
        logging.info(
            f"נוצר מגביל קצב חדש: "
            f"סוג={limiter_type}, "
            f"הודעות בדקה={messages_per_minute}, "
            f"אינטרוול מינימלי={self.min_interval:.2f} שניות"
        )
    
    def _clean_old_messages(self, current_time: float) -> None:
        """ניקוי הודעות ישנות (מעל דקה)"""
        self.message_times = [t for t in self.message_times if current_time - t < 60]
    
    async def __aenter__(self):
        """כניסה להקשר של המגביל"""
        async with self.lock:
            current_time = time.time()
            
            # ניקוי הודעות ישנות
            self._clean_old_messages(current_time)
            
            # בדיקה אם הגענו למגבלת ההודעות בדקה
            if len(self.message_times) >= self.messages_per_minute:
                wait_time = self.message_times[0] + 60 - current_time
                if wait_time > 0:
                    logging.debug(
                        f"[{self.limiter_type}] ממתין {wait_time:.2f} שניות "
                        f"(הגענו למגבלת {self.messages_per_minute} הודעות בדקה)"
                    )
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
                    self._clean_old_messages(current_time)
            
            # בדיקת אינטרוול מינימלי בין הודעות
            if self.message_times:
                elapsed = current_time - self.message_times[-1]
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    logging.debug(
                        f"[{self.limiter_type}] ממתין {wait_time:.2f} שניות "
                        f"(אינטרוול מינימלי)"
                    )
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
            
            # הוספת זמן ההודעה הנוכחית
            self.message_times.append(current_time)
            logging.debug(
                f"[{self.limiter_type}] נשלחה הודעה "
                f"(סה״כ {len(self.message_times)} הודעות בדקה האחרונה)"
            )
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """יציאה מהקשר של המגביל"""
        pass
