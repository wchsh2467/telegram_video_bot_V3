import os
import logging
import subprocess
from moviepy.editor import VideoFileClip

logger = logging.getLogger(__name__)

def convert_to_mp4(input_file: str, output_file: str) -> bool:
    """המרת קובץ וידאו לפורמט MP4"""
    try:
        command = [
            'ffmpeg', '-i', input_file,
            '-c:v', 'libx264',  # קודק וידאו
            '-c:a', 'aac',      # קודק אודיו
            '-movflags', '+faststart',  # אופטימיזציה להזרמה
            '-y',  # דריסת קובץ קיים
            output_file
        ]
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"שגיאה בהמרת הקובץ: {stderr.decode()}")
            return False
            
        logger.info(f"הקובץ הומר בהצלחה ל-{output_file}")
        return True
        
    except Exception as e:
        logger.error(f"שגיאה בהמרת הקובץ: {e}")
        return False

def create_thumbnail(input_file: str, output_file: str, time_offset: float = 1.0) -> bool:
    """יצירת תמונה ממוזערת מהווידאו"""
    try:
        command = [
            'ffmpeg', '-i', input_file,
            '-ss', str(time_offset),
            '-vframes', '1',
            '-vf', 'scale=320:-1',  # גודל קבוע לרוחב, גובה יחסי
            '-y',
            output_file
        ]
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        _, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"שגיאה ביצירת תמונה ממוזערת: {stderr.decode()}")
            return False
            
        logger.info(f"נוצרה תמונה ממוזערת: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"שגיאה ביצירת תמונה ממוזערת: {e}")
        return False

def get_video_info(file_path: str) -> dict:
    """קבלת מידע על קובץ הווידאו"""
    try:
        with VideoFileClip(file_path) as clip:
            info = {
                'duration': int(clip.duration),
                'width': int(clip.size[0]),
                'height': int(clip.size[1]),
                'fps': float(clip.fps),
                'audio': clip.audio is not None
            }
        return info
    except Exception as e:
        logger.error(f"שגיאה בקבלת מידע על הווידאו: {e}")
        return {}
