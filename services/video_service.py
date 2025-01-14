import os
import logging
import asyncio
from collections import defaultdict
from moviepy.editor import VideoFileClip
from config.settings import TARGET_GROUP_ID
from utils.helpers import clean_filename, get_video_caption, wait_for_file_release, wait_and_delete, get_file_name
from utils.rate_limiter import RateLimiter
from services.file_service import check_existing_file, save_file_id, convert_to_mp4, create_thumbnail
from services.queue_service import QueueService
from telethon.tl.custom import Button
from telethon.tl.types import DocumentAttributeVideo

class VideoService:
    def __init__(self, client, download_path):
        self.client = client
        self.download_path = download_path
        self.queue_service = QueueService()
        self.active_downloads = defaultdict(asyncio.Event)
        self.active_uploads = defaultdict(asyncio.Event)  # מעקב אחר העלאות פעילות
        # מגבילי קצב להודעות
        self.progress_limiter = RateLimiter(messages_per_minute=30, limiter_type="progress")
        self.group_limiter = RateLimiter(messages_per_minute=20, limiter_type="group")

    async def cancel_download(self, user_id: int) -> None:
        """ביטול הורדה של משתמש"""
        if user_id in self.active_downloads:
            self.active_downloads[user_id].set()
            logging.info(f"הורדה בוטלה עבור משתמש {user_id}")
        
        await self.queue_service.cancel_user_downloads(user_id)
        
        if len(self.queue_service.upload_queue) > 0:
            next_message = self.queue_service.upload_queue[0]
            asyncio.create_task(self.process_video_message(next_message))

    async def cancel_upload(self, user_id: int) -> None:
        """ביטול העלאה של משתמש"""
        if user_id in self.active_uploads:
            self.active_uploads[user_id].set()
            logging.info(f"המשתמש {user_id} ביטל את ההעלאה")

    def _check_cancellation(self, user_id: int) -> None:
        """בדיקה אם ההורדה בוטלה"""
        if user_id in self.active_downloads and self.active_downloads[user_id].is_set():
            raise asyncio.CancelledError("ההורדה בוטלה על ידי המשתמש")

    def _check_upload_cancellation(self, user_id: int) -> None:
        """בדיקה אם ההעלאה בוטלה"""
        if user_id in self.active_uploads and self.active_uploads[user_id].is_set():
            raise asyncio.CancelledError("ההעלאה בוטלה על ידי המשתמש")

    async def process_video_message(self, message):
        """עיבוד הודעת וידאו חדשה"""
        file = message.media
        original_file_name = get_file_name(message)
        clean_file_name = clean_filename(original_file_name)
        user_id = message.sender_id

        existing_file_id = check_existing_file(clean_file_name)
        if existing_file_id:
            await self._send_existing_video(message, existing_file_id, clean_file_name)
            return

        is_first = len(self.queue_service.user_queue) == 0 or self.queue_service.is_first_user(user_id)
        
        if not is_first:
            position = await self.queue_service.add_to_queue(message)
            queue_message = await message.reply(f"הקובץ התקבל ✅\nמיקומך בתור: {position}")
            self.queue_service.queue_messages[message.id] = queue_message
        else:
            await self.queue_service.add_to_queue(message)
        
        if not self.queue_service.is_first_in_queue(message.id):
            logging.info(f"Message {message.id} waiting in queue")
            return
        
        try:
            download_message = await message.reply("הקובץ התקבל\nאנא המתן...✅")
            await asyncio.sleep(3)
            await download_message.delete()

            file_path = await self._download_video(message, file, clean_file_name)
            if file_path:
                processed_video = await self._process_video(message, file_path, clean_file_name)
                if processed_video:
                    await self._send_processed_video(message, processed_video)
                    await self.queue_service.remove_from_queue(message.id, user_id)
                    
                    if len(self.queue_service.upload_queue) > 0:
                        next_message = self.queue_service.upload_queue[0]
                        asyncio.create_task(self.process_video_message(next_message))

        except Exception as e:
            logging.error(f"שגיאה בעיבוד הוידאו: {e}")
            await message.reply("אירעה שגיאה בעיבוד הוידאו. אנא נסה שוב.")
            await self.queue_service.remove_from_queue(message.id, user_id)
            if len(self.queue_service.upload_queue) > 0:
                next_message = self.queue_service.upload_queue[0]
                asyncio.create_task(self.process_video_message(next_message))

    async def _send_existing_video(self, message, file_id, file_name):
        """שליחת וידאו קיים"""
        caption_without_extension = os.path.splitext(file_name)[0]
        try:
            await self.client.send_file(
                message.chat_id,
                file_id,
                caption=caption_without_extension
            )
            logging.info(f"הקובץ {file_name} כבר קיים ונשלח ישירות מהקבוצה.")
            return True
        except Exception as e:
            logging.error(f"שגיאה בשליחת וידאו קיים: {str(e)}")
            return False

    async def _download_video(self, message, file, clean_file_name):
        """הורדת קובץ הוידאו"""
        try:
            file_path = os.path.join(self.download_path, clean_file_name)
            await self._download_with_progress(message, file_path)
            logging.info(f"הקובץ הורד בהצלחה ל- {file_path}")
            return file_path
        except (TimeoutError, ConnectionError) as e:
            logging.error(f"שגיאת רשת בהורדת הקובץ: {e}")
            await message.reply("אירעה שגיאת רשת בהורדת הקובץ. אנא נסה שוב.")
            await self.queue_service.remove_from_queue(message.id, message.sender_id)
            return None
        except Exception as e:
            logging.error(f"נכשל בהורדת הקובץ: {e}")
            await message.reply("אירעה שגיאה בהורדת הקובץ. אנא נסה שוב.")
            await self.queue_service.remove_from_queue(message.id, message.sender_id)
            return None

    async def _process_video(self, message, file_path, clean_file_name):
        """עיבוד קובץ הוידאו"""
        processing_message = None
        try:
            processing_message = await message.reply("🔄 מעבד את הוידאו...")
            
            base_name, ext = os.path.splitext(clean_file_name)
            original_path = file_path
            
            if ext.lower() != '.mp4':
                await processing_message.edit("🔄 ממיר את הוידאו ל-MP4...")
                mp4_file = os.path.join(self.download_path, f"{base_name}.mp4")
                if not await convert_to_mp4(file_path, mp4_file):
                    await processing_message.edit("❌ שגיאה בהמרת הוידאו")
                    await self.queue_service.remove_from_queue(message.id, message.sender_id)
                    return None
                file_path = mp4_file

            await processing_message.edit("🔄 יוצר תמונה ממוזערת...")
            thumbnail_file = os.path.join(self.download_path, f"{base_name}.jpg")
            try:
                thumbnail_success = await create_thumbnail(file_path, thumbnail_file)
                if not thumbnail_success:
                    logging.warning("נכשל ביצירת תמונה ממוזערת, ממשיך בלעדיה")
                    thumbnail_file = None
            except Exception as e:
                logging.warning(f"שגיאה ביצירת תמונה ממוזערת: {e}")
                thumbnail_file = None
            
            await processing_message.edit("🔄 מחשב את משך הוידאו...")
            video = VideoFileClip(file_path)
            duration = int(video.duration)
            video.close()
            
            await processing_message.edit("✅ העיבוד הושלם!")
            await asyncio.sleep(3)
            await processing_message.delete()

            return {
                'file_path': file_path,
                'thumbnail_path': thumbnail_file,
                'duration': duration,
                'original_path': original_path if original_path != file_path else None
            }
            
        except Exception as e:
            if processing_message:
                await processing_message.edit("❌ שגיאה בעיבוד הוידאו")
                await asyncio.sleep(3)
                await processing_message.delete()
            logging.error(f"שגיאה בעיבוד הוידאו: {e}")
            await self.queue_service.remove_from_queue(message.id, message.sender_id)
            return None

    async def _send_processed_video(self, message, video_data):
        """שליחת הוידאו המעובד"""
        try:
            logging.info("מתחיל שליחת וידאו...")
            caption = get_video_caption(video_data['file_path'])
            
            # 1. שולח למשתמש עם פס התקדמות
            sent_to_user = await self._upload_with_progress(
                message,
                video_data,
                caption
            )
            
            logging.info(f"שולח לקבוצת היעד {TARGET_GROUP_ID}...")
            # 2. שולח לקבוצה
            async with self.group_limiter:
                sent_to_group = await self.client.send_file(
                    TARGET_GROUP_ID,
                    file=video_data['file_path'],
                    thumb=video_data.get('thumbnail_path'),
                    caption=caption,
                    attributes=[
                        DocumentAttributeVideo(
                            duration=video_data['duration'],
                            w=0,  # יתמלא אוטומטית
                            h=0,  # יתמלא אוטומטית
                            supports_streaming=True
                        )
                    ]
                )
            
            # 3. שומר את מזהה הקובץ
            file_name = os.path.basename(video_data['file_path'])
            logging.info(f"שומר file_id עבור {file_name}")
            save_file_id(file_name, sent_to_group.file.id)
            
            logging.info("מנקה קבצים זמניים...")
            await self._cleanup_files(video_data)
            logging.info("תהליך השליחה הושלם בהצלחה")
            
        except Exception as e:
            logging.error(f"שגיאה בשליחת הוידאו: {str(e)}", exc_info=True)
            await message.reply("אירעה שגיאה בשליחת הוידאו. אנא נסה שוב.")
            await self.queue_service.remove_from_queue(message.id, message.sender_id)

    async def _upload_with_progress(self, message, video_data, caption):
        """העלאת קובץ עם פס התקדמות"""
        user_id = message.sender_id
        self.active_uploads[user_id] = asyncio.Event()
        
        cancel_button = [[Button.inline("ביטול ❌", data=f"cancel_upload_{user_id}")]]
        
        progress_message = await message.reply("📤 מתחיל העלאה...", buttons=cancel_button)
        last_percentage = 0
        last_update_time = asyncio.get_event_loop().time()
        uploaded_size = 0

        async def progress_callback(current, total):
            try:
                self._check_upload_cancellation(user_id)  # בדיקת ביטול
                
                nonlocal last_percentage, last_update_time, uploaded_size
                percentage = int(current * 100 / total)
                current_time = asyncio.get_event_loop().time()
                time_diff = current_time - last_update_time
                
                if percentage >= last_percentage + 5 or time_diff >= 3:
                    speed = (current - uploaded_size) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
                    
                    filled = int(percentage / 10)
                    empty = 10 - filled
                    progress_bar = "▰" * filled + "▱" * empty
                    
                    try:
                        async with self.progress_limiter:
                            await progress_message.edit(
                                text=f"📤 מעלה את הקובץ...\n"
                                f"{progress_bar} {percentage}%\n"
                                f"⚡ מהירות: {speed:.1f} MB/s\n"
                                f"📊 גודל: {total / (1024 * 1024):.1f} MB",
                                buttons=cancel_button
                            )
                            last_percentage = percentage
                            last_update_time = current_time
                            uploaded_size = current
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            logging.debug(f"דילוג על עדכון התקדמות: {str(e)}")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logging.error(f"שגיאה בעדכון התקדמות: {str(e)}")

        try:
            # שולח את הקובץ עם פס התקדמות
            sent_message = await self.client.send_file(
                message.chat_id,
                file=video_data['file_path'],
                thumb=video_data.get('thumbnail_path'),
                caption=caption,
                progress_callback=progress_callback,
                attributes=[
                    DocumentAttributeVideo(
                        duration=video_data['duration'],
                        w=0,  # יתמלא אוטומטית
                        h=0,  # יתמלא אוטומטית
                        supports_streaming=True
                    )
                ]
            )
            await progress_message.delete()
            if user_id in self.active_uploads:
                del self.active_uploads[user_id]
            return sent_message

        except asyncio.CancelledError:
            await progress_message.edit("❌ ההעלאה בוטלה!")
            if user_id in self.active_uploads:
                del self.active_uploads[user_id]
            # ניקוי קבצים במקרה של ביטול
            try:
                await self._cleanup_files(video_data)
                logging.info("הקבצים נמחקו בהצלחה אחרי ביטול העלאה")
            except Exception as cleanup_error:
                logging.error(f"שגיאה במחיקת קבצים אחרי ביטול העלאה: {cleanup_error}")
            await asyncio.sleep(3)  # מחכה 3 שניות
            await progress_message.delete()  # מוחק את ההודעה
            raise

        except Exception as e:
            logging.error(f"שגיאה בהעלאת הקובץ: {str(e)}")
            await progress_message.edit("❌ שגיאה בהעלאת הקובץ")
            if user_id in self.active_uploads:
                del self.active_uploads[user_id]
            # ניקוי קבצים במקרה של שגיאה
            try:
                await self._cleanup_files(video_data)
                logging.info("הקבצים נמחקו בהצלחה אחרי שגיאת העלאה")
            except Exception as cleanup_error:
                logging.error(f"שגיאה במחיקת קבצים אחרי שגיאת העלאה: {cleanup_error}")
            await progress_message.delete()
            raise e

    async def _download_with_progress(self, message, file_path):
        """הורדת קובץ עם פס התקדמות"""
        user_id = message.sender_id
        self.active_downloads[user_id] = asyncio.Event()
        
        cancel_button = [[Button.inline("ביטול ❌", data=f"cancel_download_{user_id}")]]
        
        progress_message = await message.reply("📥 הורדה החלה...", buttons=cancel_button)
        last_percentage = 0
        last_update_time = asyncio.get_event_loop().time()
        downloaded_size = 0

        async def progress_callback(current, total):
            try:
                self._check_cancellation(user_id)
                
                nonlocal last_percentage, last_update_time, downloaded_size
                percentage = int(current * 100 / total)
                current_time = asyncio.get_event_loop().time()
                time_diff = current_time - last_update_time
                
                if percentage >= last_percentage + 5 or time_diff >= 3:
                    speed = (current - downloaded_size) / (1024 * 1024 * time_diff) if time_diff > 0 else 0
                    
                    filled = int(percentage / 10)
                    empty = 10 - filled
                    progress_bar = "▰" * filled + "▱" * empty
                    
                    try:
                        async with self.progress_limiter:
                            await progress_message.edit(
                                f"📥 מוריד את הקובץ...\n"
                                f"{progress_bar} {percentage}%\n"
                                f"⚡ מהירות: {speed:.1f} MB/s\n"
                                f"📊 גודל: {total / (1024 * 1024):.1f} MB"
                            )
                            last_percentage = percentage
                            last_update_time = current_time
                            downloaded_size = current
                    except Exception as e:
                        if "MESSAGE_NOT_MODIFIED" not in str(e):
                            logging.debug(f"דילוג על עדכון התקדמות: {str(e)}")
            except asyncio.CancelledError:
                raise

        try:
            await message.download_media(file=file_path, progress_callback=progress_callback)
            await progress_message.edit("✅ ההורדה הושלמה בהצלחה!")
            return True
        except asyncio.CancelledError:
            # כשההורדה מבוטלת - מוחקים את הקובץ החלקי
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"נמחק קובץ חלקי: {file_path}")
                except Exception as e:
                    logging.error(f"שגיאה במחיקת קובץ חלקי: {str(e)}")
            await progress_message.edit("❌ ההורדה בוטלה")
            raise
        except Exception as e:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"נמחק קובץ חלקי בגלל שגיאה: {file_path}")
                except Exception as cleanup_error:
                    logging.error(f"שגיאה במחיקת קובץ חלקי: {str(cleanup_error)}")
            await progress_message.edit("❌ שגיאה בהורדת הקובץ")
            if user_id in self.active_downloads:
                del self.active_downloads[user_id]
            await progress_message.delete()
            raise e
        finally:
            await asyncio.sleep(3)
            await progress_message.delete()
            if user_id in self.active_downloads:
                del self.active_downloads[user_id]

    async def _cleanup_files(self, video_data):
        """ניקוי קבצים זמניים"""
        await wait_for_file_release(video_data['file_path'])
        
        if video_data.get('original_path'):
            await wait_and_delete(video_data['original_path'])
        await wait_and_delete(video_data['file_path'])
        await wait_and_delete(video_data['thumbnail_path'])
        logging.info("קבצים זמניים נמחקו בהצלחה.")
