import os
import tempfile
import base64
import cv2
import numpy as np
from openai import OpenAI
from video_utils import capture_frame, get_video_info

_client = None

def get_openai_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _client = OpenAI(api_key=api_key)
        else:
            _client = None
    return _client

def get_room_display_name(label):
    label_mapping = {
        'kitchen': 'Kitchen',
        'bedroom': 'Bedroom', 
        'bathroom': 'Bathroom',
        'living_room': 'Living Room',
        'closet': 'Closet',
        'exterior': 'Exterior',
        'office': 'Office',
        'common_area': 'Common Area',
        'dining_room': 'Dining Room',
        'balcony': 'Balcony',
        'unlabeled': 'Unlabeled'
    }
    return label_mapping.get(label, label.replace('_', ' ').title()) if label else 'Unlabeled'

def detect_scene_label(video_path, start_time, end_time):
    client = get_openai_client()
    if client is None:
        print("OPENAI_API_KEY not found – skipping automatic scene labelling")
        return None

    mid_time = (start_time + end_time) / 2.0
    os.makedirs('temp', exist_ok=True)
    frame_path = tempfile.mktemp(suffix='.jpg', dir='temp')

    if not capture_frame(video_path, mid_time, frame_path):
        return None

    label = classify_image_scene(frame_path)

    try:
        os.remove(frame_path)
    except OSError:
        pass

    return label

def classify_image_scene(image_path):
    client = get_openai_client()
    if client is None:
        print("OPENAI_API_KEY not found – skipping scene classification")
        return None
        
    try:
        with open(image_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')

        categories = [
            "kitchen", "bedroom", "bathroom", "living_room", "closet", 
            "exterior", "office", "common_area", "dining_room", "balcony"
        ]

        system_prompt = (
            "You are a computer vision assistant that classifies real-estate "
            "scenes. Respond with exactly one of the following lowercase labels "
            "and nothing else: " + ", ".join(categories) + "."
        )

        user_prompt = "Which scene type best describes this image?"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=5,
            temperature=0
        )

        label = response.choices[0].message.content.strip().lower()

        if label not in categories:
            print(f"AI couldn't confidently classify scene (got '{label}'), skipping label")
            return None

        print(f"Detected scene label: {label}")
        return label

    except Exception as exc:
        print(f"OpenAI scene classification failed: {exc}")
        return None 

def detect_room_transitions_realtime(video_path, callback_function=None, detection_interval=2.0):

    print(f"Starting simple room detection for: {video_path}")
    
    video_info = get_video_info(video_path)
    if not video_info:
        print("Failed to get video info")
        return []
    
    duration = video_info['duration']
    fps = video_info['fps']
    
    sample_interval = max(1, int(fps * detection_interval))
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("Failed to open video for room detection")
        return []
    
    frame_count = 0
    sampled_frames = []
    
    print("Sampling frames for room detection...")
    
    segments = []
    current_segment = None
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % sample_interval == 0:
            current_time = frame_count / fps
            
            temp_frame_path = f"temp_frame_{frame_count}.jpg"
            cv2.imwrite(temp_frame_path, frame)
            
            try:
                room_label = classify_image_scene(temp_frame_path)
                
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)
                
                if room_label is not None:
                    print(f"Time: {current_time:.1f}s, Room: {room_label}")
                    
                    if current_segment is None:
                        current_segment = {
                            'start': current_time,
                            'room': room_label,
                            'frames': [{'time': current_time, 'room': room_label}]
                        }
                        print(f"Starting new segment: {room_label} at {current_time:.1f}s")
                        
                        if callback_function:
                            callback_function({
                                'type': 'room_entry',
                                'room': room_label,
                                'time': current_time,
                                'progress': (current_time / duration) * 100
                            })
                        
                    elif room_label == current_segment['room']:
                        current_segment['frames'].append({'time': current_time, 'room': room_label})
                        print(f"Extending segment: {room_label} at {current_time:.1f}s")
                        
                    else:
                        if len(current_segment['frames']) >= 2:  
                            segment = {
                                'start': current_segment['start'],
                                'end': current_segment['frames'][-1]['time'],
                                'room': current_segment['room'],
                                'display_name': get_room_display_name(current_segment['room'])
                            }
                            segments.append(segment)
                            print(f"Segment complete: {current_segment['room']} ({segment['start']:.1f}s - {segment['end']:.1f}s)")
                            
                            if callback_function:
                                callback_function({
                                    'type': 'segment_complete',
                                    'segment': segment,
                                    'progress': (current_time / duration) * 100
                                })
                        
                        current_segment = {
                            'start': current_time,
                            'room': room_label,
                            'frames': [{'time': current_time, 'room': room_label}]
                        }
                        print(f"Starting new segment: {room_label} at {current_time:.1f}s")
                        
                        if callback_function:
                            callback_function({
                                'type': 'room_entry',
                                'room': room_label,
                                'time': current_time,
                                'progress': (current_time / duration) * 100
                            })
                    
                    if callback_function:
                        callback_function({
                            'type': 'progress',
                            'time': current_time,
                            'room': room_label,
                            'progress': (current_time / duration) * 100
                        })
                else:
                    print(f"Time: {current_time:.1f}s, Room: unclassified (skipping)")
                
            except Exception as e:
                print(f"Error analyzing frame at {current_time:.1f}s: {e}")
                if os.path.exists(temp_frame_path):
                    os.remove(temp_frame_path)
        
        frame_count += 1
    
    cap.release()
    
    if current_segment and len(current_segment['frames']) >= 2:
        segment = {
            'start': current_segment['start'],
            'end': current_segment['frames'][-1]['time'],
            'room': current_segment['room'],
            'display_name': get_room_display_name(current_segment['room'])
        }
        segments.append(segment)
        print(f"Final segment: {current_segment['room']} ({segment['start']:.1f}s - {segment['end']:.1f}s)")
        
        if callback_function:
            callback_function({
                'type': 'segment_complete',
                'segment': segment,
                'progress': 100
            })
    
    segments = [s for s in segments if s['end'] - s['start'] >= 2.0]
    
    print(f"Simple room detection complete. Found {len(segments)} segments:")
    for seg in segments:
        print(f"  {seg['start']:.1f}s - {seg['end']:.1f}s: {seg['display_name']}")
    
    return segments 