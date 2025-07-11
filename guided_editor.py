import cv2
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import tempfile
import base64
from openai import OpenAI

from video_utils import get_video_info, get_quality_settings, capture_frame
from scene_detection import detect_scene_label, classify_image_scene
from video_processor import extract_clip_simple, extract_clip_hq, combine_clips, combine_clips_hq
from tour_creator import create_tour_simple, create_speedup_tour_simple, create_tour
from post_processor import add_qr_overlay, add_music_overlay, add_agent_watermark, add_combined_overlays

class GuidedVideoEditor:
    
    def __init__(self, video_path):
        self.video_path = Path(video_path)
        self.video_info = get_video_info(self.video_path)
        self.user_segments = []
    
    def add_segment(self, start_time, end_time, label=None):
        if start_time < 0 or end_time > self.video_info['duration']:
            print(f" Invalid time range")
            return False

        if not label or str(label).lower() in {"", "auto", "none"}:
            detected_label = detect_scene_label(self.video_path, start_time, end_time)
            if detected_label:
                label = detected_label
            else:
                label = 'unlabeled'

        segment = {
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,
            'label': label
        }

        self.user_segments.append(segment)
        print(f"Added: {start_time:.1f}s - {end_time:.1f}s ({label})")
        return True

    def create_tour_simple(self, output_path="guided_tour.mp4"):
        return create_tour_simple(self.user_segments, self.video_path, self.video_info, output_path)

    def create_speedup_tour_simple(self, output_path="guided_tour_ffmpeg.mp4", speed_factor=3.0):
        return create_speedup_tour_simple(self.user_segments, self.video_path, self.video_info, output_path, speed_factor)

    def create_tour(self, output_path="guided_tour.mp4", api_key=None, quality='high'):
        return create_tour(self.user_segments, self.video_path, self.video_info, output_path, api_key, quality)

    def get_quality_settings(self, quality='high'):
        return get_quality_settings(quality)

    def extract_clip_simple(self, start, end, output, room_type=None):
        return extract_clip_simple(self.video_path, self.video_info, start, end, output, room_type)

    def extract_clip_hq(self, start, end, output, speed_factor=1.0, quality_settings=None, silent_mode=True, room_type=None):
        return extract_clip_hq(self.video_path, self.video_info, start, end, output, speed_factor, quality_settings, silent_mode, room_type)
    
    def combine_clips(self, clips, output, silent_mode=True):
        return combine_clips(clips, output, silent_mode)

    def combine_clips_hq(self, clips, output, quality_settings):
        return combine_clips_hq(clips, output, quality_settings)

    def add_qr_overlay(self, input_video, qr_image_path, output_path=None, position='bottom_right'):
        return add_qr_overlay(input_video, qr_image_path, output_path, position)

    def add_music_overlay(self, input_video, music_path, volume=0.3, output_path=None):
        return add_music_overlay(input_video, music_path, volume, output_path)
    
    def add_agent_watermark(self, input_video, agent_name, agency_name, output_path=None):
        return add_agent_watermark(input_video, agent_name, agency_name, output_path)

    def add_combined_overlays(self, input_video, agent_name, agency_name, qr_image_path=None, qr_position='top_right', output_path=None):
        return add_combined_overlays(input_video, agent_name, agency_name, qr_image_path, qr_position, output_path)

    def get_video_info(self):
        return self.video_info

    def capture_frame(self, timestamp, output_path):
        return capture_frame(self.video_path, timestamp, output_path)

    def detect_scene_label(self, start_time, end_time):
        return detect_scene_label(self.video_path, start_time, end_time)

    def classify_image_scene(self, image_path):
        return classify_image_scene(image_path)