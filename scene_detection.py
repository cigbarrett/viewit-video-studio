import os
import tempfile
import base64
import cv2
import time
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
        'office': 'Office',
        'dining_room': 'Dining Room',
        'balcony': 'Balcony',
        'unlabeled': 'Unlabeled'
    }
    return label_mapping.get(label, label.replace('_', ' ').title()) if label else 'Unlabeled'

def detect_scene_label(video_path, start_time, end_time, unfurnished_mode=False):
    client = get_openai_client()
    if client is None:
        print("OPENAI_API_KEY not found – skipping automatic scene labelling")
        return None

    mid_time = (start_time + end_time) / 2.0
    os.makedirs('temp', exist_ok=True)
    frame_path = tempfile.mktemp(suffix='.jpg', dir='temp')

    if not capture_frame(video_path, mid_time, frame_path):
        return None

    label = classify_image_scene(frame_path, unfurnished_mode=unfurnished_mode)

    try:
        os.remove(frame_path)
    except OSError:
        pass

    return label

def estimate_room_characteristics(image_path):

    client = get_openai_client()
    if client is None:
        return None
        
    try:
        with open(image_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')

        analysis_prompt = (
            "Analyze this room image and provide characteristics that help identify if it's a bedroom or living room. "
            "Consider:\n"
            "1. Room size (small/medium/large)\n"
            "2. Room proportions (square/rectangular)\n"
            "3. Number and type of doors\n"
            "4. Window characteristics\n"
            "5. Presence of built-in features (closets, alcoves)\n"
            "6. Room location hints (corner room, end of hallway, etc.)\n"
            "7. Whether this appears to be an unfurnished property\n\n"
            "Respond with: 'bedroom' if characteristics suggest bedroom, 'living_room' if characteristics suggest living room, or 'uncertain'."
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a real estate expert analyzing room characteristics."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": analysis_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10,
            temperature=0,
            timeout=30
        )

        result = response.choices[0].message.content.strip().lower()
        return result if result in ['bedroom', 'living_room', 'uncertain'] else 'uncertain'

    except Exception as e:
        print(f"Room characteristics analysis failed: {e}")
        return None

def classify_image_scene(image_path, confidence_threshold=0.7, unfurnished_mode=False):
    client = get_openai_client()
    if client is None:
        print("OPENAI_API_KEY not found – skipping scene classification")
        return None
        
    try:
        with open(image_path, 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')

        categories = [
            "kitchen", "bedroom", "bathroom", "living_room", "closet", 
            "office", "dining_room", "balcony"
        ]


        if unfurnished_mode:
            system_prompt = (
                "You are a computer vision assistant that classifies real-estate scenes. "
                "CRITICAL: This is an UNFURNISHED PROPERTY. Be extremely cautious and conservative in your classification. "
                "Focus entirely on architectural features, room layout, and intended purpose rather than furniture.\n\n"
                "UNFURNISHED PROPERTY CLASSIFICATION GUIDELINES:\n"
                "- BEDROOM: Limage.pngook for bedroom-specific architectural features like closet spaces, bedroom proportions, "
                "bedroom windows, bedroom door locations, or bedroom layout. Even without furniture, if the room has "
                "bedroom characteristics (size, layout, closet), classify as bedroom.\n"
                "- LIVING ROOM: Look for living room architectural characteristics like larger open spaces, "
                "living room proportions, main entry areas, or living room layout. DO NOT classify as living room "
                "just because a bedroom is empty - look for actual living room features.\n"
                "- BATHROOM: Look for bathroom fixtures, plumbing, bathroom tiles, or bathroom layout.\n"
                "- KITCHEN: Look for kitchen cabinets, appliances, kitchen layout, or kitchen fixtures.\n"
                "- CLOSET: Small storage spaces, walk-in closets, or utility closets.\n"
                "- OFFICE: Study areas, home office layouts, or workspace characteristics.\n"
                "- DINING ROOM: Dining area layouts, dining room proportions, or dining room features.\n"
                "- BALCONY: Outdoor spaces, balconies, terraces, or exterior areas.\n\n"
                "When uncertain, prefer the more conservative classification based on room size and layout. "
                "Respond with exactly one of the following lowercase labels and nothing else: " + ", ".join(categories) + "."
            )
        else:
            system_prompt = (
                "You are a computer vision assistant that classifies real-estate scenes. "
                "IMPORTANT: Be very cautious when classifying unfurnished or partially furnished properties. "
                "Look for architectural features and room characteristics rather than just furniture.\n\n"
                "Key classification guidelines:\n"
                "- BEDROOM: Look for bedroom-specific features like closet spaces, bedroom proportions, "
                "bedroom windows, or bedroom door locations. Even without a bed, if the room has bedroom "
                "characteristics (size, layout, closet), classify as bedroom.\n"
                "- LIVING ROOM: Look for living room characteristics like larger open spaces, "
                "living room proportions, main entry areas, or living room architectural features. "
                "Don't classify as living room just because a bedroom is empty.\n"
                "- BATHROOM: Look for bathroom fixtures, plumbing, bathroom tiles, or bathroom layout.\n"
                "- KITCHEN: Look for kitchen cabinets, appliances, kitchen layout, or kitchen fixtures.\n"
                "- CLOSET: Small storage spaces, walk-in closets, or utility closets.\n"
                "- OFFICE: Study areas, home office layouts, or workspace characteristics.\n"
                "- DINING ROOM: Dining area layouts, dining room proportions, or dining room features.\n"
                "- BALCONY: Outdoor spaces, balconies, terraces, or exterior areas.\n\n"
                "When in doubt about an unfurnished room, consider the room's intended purpose based on "
                "its size, location, and architectural features rather than current furniture.\n\n"
                "Respond with exactly one of the following lowercase labels and nothing else: " + ", ".join(categories) + "."
            )

        user_prompt = (
            "Analyze this real estate image carefully. Consider the room's architectural features, "
            "size, layout, and intended purpose. If this appears to be an unfurnished or partially "
            "furnished property, focus on the room's characteristics rather than missing furniture. "
            "Which scene type best describes this image?"
        )

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
            max_tokens=10,
            temperature=0,
            timeout=30
        )

        label = response.choices[0].message.content.strip().lower()

        if label not in categories:
            print(f"AI couldn't confidently classify scene (got '{label}'), skipping label")
            return None

        if label in ['bedroom', 'living_room']:
            if unfurnished_mode:
                verification_prompt = (
                    "This is a follow-up analysis for an UNFURNISHED PROPERTY room classified as '" + label + "'. "
                    "Please verify this classification by considering:\n"
                    "1. Room size and proportions (bedrooms are typically smaller than living rooms)\n"
                    "2. Location in the property (bedrooms are usually in private areas)\n"
                    "3. Architectural features (closets, windows, door placement)\n"
                    "4. Room layout and intended purpose\n\n"
                    "For unfurnished properties, be extra conservative. If uncertain, prefer bedroom for smaller rooms. "
                    "Respond with 'bedroom', 'living_room', or 'uncertain'."
                )
            else:
                verification_prompt = (
                    "This is a follow-up analysis for a room classified as '" + label + "'. "
                    "Please verify this classification by considering:\n"
                    "1. Room size and proportions (bedrooms are typically smaller than living rooms)\n"
                    "2. Location in the property (bedrooms are usually in private areas)\n"
                    "3. Architectural features (closets, windows, door placement)\n"
                    "4. Whether this appears to be an unfurnished property\n\n"
                    "If this is an unfurnished property and you're uncertain, consider the room's intended purpose. "
                    "Respond with 'bedroom', 'living_room', or 'uncertain'."
                )
            
            try:
                verification_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a real estate expert verifying room classifications."},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": verification_prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{img_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=10,
                    temperature=0,
                    timeout=30
                )
                
                verification_label = verification_response.choices[0].message.content.strip().lower()
                
                if verification_label == 'uncertain':
                    print(f"AI uncertain about {label} classification, using room characteristics analysis")
                    characteristics = estimate_room_characteristics(image_path)
                    if characteristics and characteristics in ['bedroom', 'living_room']:
                        if characteristics != label:
                            print(f"Room characteristics analysis changed classification from {label} to {characteristics}")
                            return characteristics
                        else:
                            print(f"Room characteristics analysis confirmed {label} classification")
                            return label
                    else:
                        print(f"Room characteristics analysis inconclusive, keeping original {label} classification")
                        return label
                elif verification_label in ['bedroom', 'living_room']:
                    if verification_label != label:
                        print(f"Verification changed classification from {label} to {verification_label}")
                        return verification_label
                    else:
                        print(f"Verification confirmed {label} classification")
                        return label
                        
            except Exception as e:
                print(f"Verification failed, using original classification: {e}")
                return label

        print(f"Detected scene label: {label}")
        return label

    except Exception as exc:
        print(f"OpenAI scene classification failed: {exc}")
        time.sleep(1)
        return None

def detect_room_transitions_realtime(video_path, callback_function=None, detection_interval=3.0, unfurnished_mode=False):

    print(f"Starting simple room detection for: {video_path} (unfurnished_mode: {unfurnished_mode})")
    
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
            
            if int(current_time) % 30 == 0:
                print(f"AI Detection Progress: {current_time:.1f}s / {duration:.1f}s ({current_time/duration*100:.1f}%)")
            
            # Use temp directory for frame files
            os.makedirs('temp', exist_ok=True)
            temp_frame_path = os.path.join('temp', f"temp_frame_{frame_count}_{int(time.time()*1000)}.jpg")
            cv2.imwrite(temp_frame_path, frame)
            
            try:
                time.sleep(0.5)  
                
                room_label = classify_image_scene(temp_frame_path, unfurnished_mode=unfurnished_mode)
                
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
                            should_continue = callback_function({
                                'type': 'room_entry',
                                'room': room_label,
                                'time': current_time,
                                'progress': (current_time / duration) * 100
                            })
                            if should_continue is False:
                                print("Detection stopped by callback")
                                cap.release()
                                return segments
                        
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
                                should_continue = callback_function({
                                    'type': 'segment_complete',
                                    'segment': segment,
                                    'progress': (current_time / duration) * 100
                                })
                                if should_continue is False:
                                    print("Detection stopped by callback")
                                    cap.release()
                                    return segments
                        
                        current_segment = {
                            'start': current_time,
                            'room': room_label,
                            'frames': [{'time': current_time, 'room': room_label}]
                        }
                        print(f"Starting new segment: {room_label} at {current_time:.1f}s")
                        
                        if callback_function:
                            should_continue = callback_function({
                                'type': 'room_entry',
                                'room': room_label,
                                'time': current_time,
                                'progress': (current_time / duration) * 100
                            })
                            if should_continue is False:
                                print("Detection stopped by callback")
                                cap.release()
                                return segments
                    
                    if callback_function:
                        should_continue = callback_function({
                            'type': 'progress',
                            'time': current_time,
                            'room': room_label,
                            'progress': (current_time / duration) * 100
                        })
                        if should_continue is False:
                            print("Detection stopped by callback")
                            cap.release()
                            return segments
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