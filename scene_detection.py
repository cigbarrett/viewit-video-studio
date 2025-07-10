import os
import tempfile
import base64
from openai import OpenAI
from video_utils import capture_frame

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_scene_label(video_path, start_time, end_time):
    if client.api_key is None:
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