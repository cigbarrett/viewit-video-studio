import cv2
import os
from pathlib import Path

def get_video_info(video_path):
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        return {
            'duration': duration,
            'fps': fps,
            'width': width,
            'height': height
        }
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None

def get_quality_settings(quality='high'):
    settings = {
        'draft': {
            'crf': '23',
            'preset': 'veryfast',
            'maxrate': '20M',
            'bufsize': '40M',
            'timeout': 60,
            'target_resolution': '1080:1920'
        },
        'standard': {
            'crf': '20',
            'preset': 'fast',
            'maxrate': '35M',
            'bufsize': '70M',
            'timeout': 180,
            'target_resolution': '1080:1920'
        },
        'high': {
            'crf': '17',
            'preset': 'medium',
            'maxrate': '70M',
            'bufsize': '140M',
            'timeout': 600,
            'target_resolution': '1080:1920'
        },
        'professional': {
            'crf': '14',
            'preset': 'slow',
            'maxrate': '150M',
            'bufsize': '300M',
            'timeout': 1200,
            'target_resolution': '1080:1920'
        }
    }
    return settings.get(quality, settings['high'])

def capture_frame(video_path, timestamp, output_path):
    try:
        cap = cv2.VideoCapture(str(video_path))
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print("Failed to capture frame for scene detection")
            return False
        cv2.imwrite(output_path, frame)
        return True
    except Exception as exc:
        print(f"Frame capture error: {exc}")
        return False 