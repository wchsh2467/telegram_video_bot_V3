import logging
from collections import defaultdict

class QueueService:
    def __init__(self):
        self.upload_queue = []  # תור הקבצים
        self.user_queue = []    # תור המשתמשים
        self.queue_messages = {}  # שמירת הודעות התור לפי message_id

    async def add_to_queue(self, message, queue_message=None):
        """הוספת הודעה לתור"""
        user_id = message.sender_id
        
        # הוספת המשתמש לתור המשתמשים אם הוא לא נמצא בו
        if user_id not in self.user_queue:
            self.user_queue.append(user_id)
            position = len(self.user_queue)
            logging.info(f"Added user {user_id} to queue. Position: {position}")
        
        # הוספת ההודעה לתור הקבצים
        self.upload_queue.append(message)
        logging.info(f"Added message {message.id} to queue for user {user_id}")
        
        # שמירת הודעת התור אם יש
        if queue_message:
            self.queue_messages[message.id] = queue_message
        
        return len(self.user_queue)

    def is_first_user(self, user_id):
        """בדיקה אם המשתמש ראשון בתור"""
        return len(self.user_queue) > 0 and self.user_queue[0] == user_id

    def is_first_in_queue(self, message_id):
        """בדיקה אם ההודעה ראשונה בתור הקבצים"""
        return len(self.upload_queue) > 0 and self.upload_queue[0].id == message_id

    def get_user_position(self, user_id):
        """קבלת מיקום המשתמש בתור"""
        try:
            return self.user_queue.index(user_id) + 1
        except ValueError:
            return None

    async def remove_from_queue(self, message_id, user_id):
        """הסרת הודעה מהתור"""
        # מחיקת הודעת התור אם קיימת
        if message_id in self.queue_messages:
            try:
                await self.queue_messages[message_id].delete()
                del self.queue_messages[message_id]
                logging.info(f"Deleted queue message for message {message_id}")
            except Exception as e:
                logging.warning(f"Failed to delete queue message: {e}")
        
        # הסרת ההודעה מתור הקבצים
        self.upload_queue = [msg for msg in self.upload_queue if msg.id != message_id]
        
        # בדיקה אם למשתמש יש עוד קבצים בתור
        user_has_more_files = any(msg.sender_id == user_id for msg in self.upload_queue)
        if not user_has_more_files and user_id in self.user_queue:
            self.user_queue.remove(user_id)
            logging.info(f"Removed user {user_id} from queue - no more files")
        
        logging.info(f"Removed message {message_id} from queue")

    async def cancel_user_downloads(self, user_id):
        """ביטול כל ההורדות של משתמש מסוים"""
        messages_to_remove = []
        for msg in self.upload_queue:
            if msg.sender_id == user_id:
                if msg.id in self.queue_messages:
                    try:
                        await self.queue_messages[msg.id].delete()
                        del self.queue_messages[msg.id]
                    except Exception as e:
                        logging.warning(f"Failed to delete queue message: {e}")
                messages_to_remove.append(msg)
        
        for msg in messages_to_remove:
            self.upload_queue.remove(msg)
        
        if user_id in self.user_queue:
            self.user_queue.remove(user_id)
            logging.info(f"Removed user {user_id} and all their files from queue")
