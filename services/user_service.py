import os
import yaml
import logging
from typing import List, Set
from config.settings import USERS_FILE

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self._allowed_users: Set[str] = set()
        self._load_users()
        
    def _load_users(self):
        """טעינת משתמשים מורשים מקובץ"""
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, 'r', encoding='utf-8') as file:
                    data = yaml.safe_load(file)
                    if data and 'allowed_users' in data:
                        self._allowed_users = set(map(str, data['allowed_users']))
                logger.info(f"נטענו {len(self._allowed_users)} משתמשים מורשים")
            except Exception as e:
                logger.error(f"שגיאה בטעינת משתמשים: {e}")
                
    def _save_users(self):
        """שמירת משתמשים מורשים לקובץ"""
        try:
            os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
            with open(USERS_FILE, 'w', encoding='utf-8') as file:
                yaml.dump({'allowed_users': list(self._allowed_users)}, file, allow_unicode=True)
            logger.info("רשימת המשתמשים נשמרה בהצלחה")
        except Exception as e:
            logger.error(f"שגיאה בשמירת משתמשים: {e}")
            
    def is_user_allowed(self, user_id: int) -> bool:
        """בדיקה אם משתמש מורשה"""
        # ב-Telethon מזהה המשתמש תמיד מגיע כמספר שלם, אך אנו שומרים אותו כמחרוזת בקובץ
        return str(user_id) in self._allowed_users
        
    def add_user(self, user_id: int) -> bool:
        """הוספת משתמש מורשה"""
        # המרת מזהה המשתמש למחרוזת לצורך שמירה, מכיוון ש-Telethon מחזיר מספרים שלמים אך אנו שומרים אותם כמחרוזות
        user_id_str = str(user_id)
        if user_id_str not in self._allowed_users:
            self._allowed_users.add(user_id_str)
            self._save_users()
            logger.info(f"משתמש {user_id} נוסף בהצלחה")
            return True
        return False
        
    def remove_user(self, user_id: int) -> bool:
        """הסרת משתמש מורשה"""
        # המרת מזהה המשתמש למחרוזת לצורך הסרה, מכיוון ש-Telethon מחזיר מספרים שלמים אך אנו שומרים אותם כמחרוזות
        user_id_str = str(user_id)
        if user_id_str in self._allowed_users:
            self._allowed_users.remove(user_id_str)
            self._save_users()
            logger.info(f"משתמש {user_id} הוסר בהצלחה")
            return True
        return False
        
    def add_users(self, user_ids: str) -> tuple[int, List[str]]:
        """הוספת מספר משתמשים בבת אחת"""
        added_count = 0
        invalid_ids = []
        
        # פיצול המחרוזת למזהים
        ids = [id.strip() for id in user_ids.split(',')]
        
        for user_id in ids:
            try:
                # בדיקת תקינות המזהה
                if user_id.isdigit():
                    if self.add_user(int(user_id)):
                        added_count += 1
                else:
                    invalid_ids.append(user_id)
            except ValueError:
                invalid_ids.append(user_id)
                
        return added_count, invalid_ids
        
    def get_allowed_users(self) -> List[str]:
        """קבלת רשימת המשתמשים המורשים"""
        return list(self._allowed_users)
