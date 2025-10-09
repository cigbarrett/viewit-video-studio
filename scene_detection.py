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
                "- BEDROOM: Limage.png ook for bedroom-specific architectural features like closet spaces, bedroom proportions, "
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

def classify_multiple_images_batch(frame_data_list, unfurnished_mode=False):
    """Classify multiple frames in a single API call"""
    client = get_openai_client()
    if client is None:
        print("OPENAI_API_KEY not found – skipping scene classification")
        return [None] * len(frame_data_list)
    
    try:
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
                "- BEDROOM: Look for bedroom-specific architectural features like closet spaces, bedroom proportions, "
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
                "When uncertain, prefer the more conservative classification based on room size and layout."
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
                "its size, location, and architectural features rather than current furniture."
            )
        
        
        content = [{
            "type": "text",
            "text": (
                f"I'm sending you {len(frame_data_list)} frames from a real estate video tour. "
                "Please analyze each image and classify it into one of these categories: " + 
                ", ".join(categories) + ".\n\n"
                "Respond with ONLY a JSON array of classifications, one for each image in order. "
                "Each element should be exactly one of the category names in lowercase. "
                f"Example format: {str(['bedroom', 'bedroom', 'kitchen', 'bathroom'][:len(frame_data_list)])}\n\n"
                "If you cannot confidently classify an image, use 'uncertain' for that position."
            )
        }]
        
        
        for frame_info in frame_data_list:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_info['base64']}"
                }
            })
        
        
        print(f"Making batch API call to classify {len(frame_data_list)} frames...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=200,  
            temperature=0,
            timeout=90  
        )
        
        
        result_text = response.choices[0].message.content.strip()
        print(f"Batch classification response: {result_text}")
        
        
        import json
        try:
            
            if result_text.startswith('```'):
                
                lines = result_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  
                if lines and lines[-1].startswith('```'):
                    lines = lines[:-1]  
                result_text = '\n'.join(lines).strip()
            
            classifications = json.loads(result_text)
            if not isinstance(classifications, list):
                raise ValueError("Response is not a list")
            
            
            validated = []
            for i, label in enumerate(classifications):
                if isinstance(label, str):
                    label = label.strip().lower()
                    if label in categories or label == 'uncertain':
                        validated.append(label if label != 'uncertain' else None)
                    else:
                        validated.append(None)
                else:
                    validated.append(None)
            
            
            while len(validated) < len(frame_data_list):
                validated.append(None)
            
            return validated[:len(frame_data_list)]
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse batch classification response as JSON: {e}")
            return [None] * len(frame_data_list)
        
    except Exception as exc:
        print(f"Batch classification failed: {exc}")
        return [None] * len(frame_data_list)


def detect_room_transitions_realtime(video_path, callback_function=None, detection_interval=3.0, unfurnished_mode=False):

    print(f"Starting batched room detection for: {video_path} (unfurnished_mode: {unfurnished_mode})")
    
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
    
    print("Step 1: Extracting frames from video...")
    
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % sample_interval == 0:
            current_time = frame_count / fps
            
            
            _, buffer = cv2.imencode('.jpg', frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            sampled_frames.append({
                'time': current_time,
                'base64': frame_b64,
                'frame_number': frame_count
            })
            
            if len(sampled_frames) % 10 == 0:
                print(f"Extracted {len(sampled_frames)} frames ({current_time:.1f}s / {duration:.1f}s)")
                
                if callback_function:
                    extraction_progress = (current_time / duration) * 100
                    callback_function({
                        'type': 'extraction_progress',
                        'frames_extracted': len(sampled_frames),
                        'current_time': current_time,
                        'total_duration': duration,
                        'progress': extraction_progress * 0.1,  # Reserve first 10% for extraction
                        'message': f'Analyzing video content...'
                    })
        
        frame_count += 1
    
    cap.release()
    
    print(f"Step 2: Classifying {len(sampled_frames)} frames in batched API calls...")
    
    
    BATCH_SIZE = 10
    classifications = []
    
    for i in range(0, len(sampled_frames), BATCH_SIZE):
        batch = sampled_frames[i:i+BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(sampled_frames) + BATCH_SIZE - 1) // BATCH_SIZE
        
        if callback_function:
            # Use 10-90% of progress bar for batch processing
            batch_progress = 10 + (i / len(sampled_frames)) * 80
            callback_function({
                'type': 'batch_progress',
                'batch_num': batch_num,
                'total_batches': total_batches,
                'frames_processed': i,
                'total_frames': len(sampled_frames),
                'progress': batch_progress,
                'message': f'AI is identifying rooms...'
            })
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} frames)...")
        batch_results = classify_multiple_images_batch(batch, unfurnished_mode=unfurnished_mode)
        classifications.extend(batch_results)
        
        if callback_function:
            # Use 10-90% of progress bar for batch processing
            batch_progress = 10 + ((i + len(batch)) / len(sampled_frames)) * 80
            callback_function({
                'type': 'batch_complete',
                'batch_num': batch_num,
                'total_batches': total_batches,
                'frames_processed': i + len(batch),
                'total_frames': len(sampled_frames),
                'progress': batch_progress,
                'message': f'Processing room data...'
            })
    
    print(f"Step 3: Building segments from classifications...")
    
    
    segments = []
    current_segment = None
    
    for i, (frame_info, room_label) in enumerate(zip(sampled_frames, classifications)):
        current_time = frame_info['time']
        
        if callback_function:
            # Use 90-100% of progress bar for segment building
            segment_progress = 90 + (i / len(sampled_frames)) * 10
            should_continue = callback_function({
                'type': 'progress',
                'time': current_time,
                'room': room_label,
                'progress': segment_progress
            })
            if should_continue is False:
                print("Detection stopped by callback")
                break
        
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
        else:
            print(f"Time: {current_time:.1f}s, Room: unclassified (skipping)")
    
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
    
    print(f"Batched room detection complete. Found {len(segments)} segments:")
    for seg in segments:
        print(f"  {seg['start']:.1f}s - {seg['end']:.1f}s: {seg['display_name']}")
    
    return segments 