import os
import tempfile
import subprocess
from pathlib import Path
from video_utils import get_quality_settings
from video_processor import extract_clip_simple, extract_clip_hq, combine_clips, combine_clips_hq

def create_tour_simple(user_segments, video_path, video_info, output_path="guided_tour.mp4"):
    if not user_segments:
        print("No segments selected!")
        return False

    print(f"Creating SIMPLE segments-only tour from {len(user_segments)} segments...")
    
    sorted_segments = sorted(user_segments, key=lambda x: x['start_time'])
    
    temp_clips = []
    for i, segment in enumerate(sorted_segments):
        clip_path = f"temp/simple_clip_{i}.mp4"
        
        success = extract_clip_simple(
            video_path, video_info, segment['start_time'], segment['end_time'], 
            clip_path, room_type=segment.get('label')
        )
        
        if success:
            temp_clips.append(clip_path)
            print(f"Simple Clip {i+1}: {segment['start_time']:.1f}s-{segment['end_time']:.1f}s ({segment.get('label', 'room')})")
        else:
            print(f"Failed to extract simple clip {i+1}")
            return False
    
    if temp_clips:
        success = combine_clips(temp_clips, output_path, silent_mode=True)
    else:
        print("No clips to combine")
        success = False
    
    for clip in temp_clips:
        if os.path.exists(clip):
            os.unlink(clip)
    
    if success:
        print(f"SIMPLE segments-only tour created: {output_path}")
    
    return success

def create_speedup_tour_simple(user_segments, video_path, video_info, output_path="guided_tour_ffmpeg.mp4", speed_factor=3.0):
    if not user_segments:
        print("No segments selected!")
        return False

    with tempfile.TemporaryDirectory() as temp_dir:
        timeline = []
        current_time = 0.0
        sorted_segments = sorted(user_segments, key=lambda x: x['start_time'])

        for segment in sorted_segments:
            if current_time < segment['start_time']:
                timeline.append({
                    'type': 'gap',
                    'start': current_time,
                    'end': segment['start_time'],
                    'speed': speed_factor
                })
            timeline.append({
                'type': 'segment',
                'start': segment['start_time'],
                'end': segment['end_time'],
                'speed': 1.0,
                'label': segment.get('label')
            })
            current_time = segment['end_time']

        if current_time < video_info['duration']:
            timeline.append({
                'type': 'gap',
                'start': current_time,
                'end': video_info['duration'],
                'speed': speed_factor
            })

        part_paths = []
        for i, part in enumerate(timeline):
            temp_path = Path(temp_dir) / f"part_{i}.mp4"
            duration = part['end'] - part['start']
            
            base_cmd = [
                'ffmpeg', '-ss', str(part['start']), '-t', str(duration),
                '-i', str(video_path),
                '-vf'
            ]
            
            if part['speed'] > 1.0:
                filter_str = f"setpts=PTS/{part['speed']},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
                print(f"Speedup gap: {part['start']:.1f}s to {part['end']:.1f}s at {part['speed']}x (9:16)")
            else:
                filters = ["scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"]
                if part.get('label'):
                    display_text = part['label'].replace('_', ' ').upper()
                    text_overlay = (
                        f"drawtext=text='{display_text}':fontfile=/Windows/Fonts/arialbd.ttf:"
                        f"fontsize=65:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1:"
                        f"x=(w-text_w)/2:y=h-text_h-250"
                    )
                    filters.append(text_overlay)
                filter_str = ",".join(filters)
                print(f"Normal segment: {part['start']:.1f}s to {part['end']:.1f}s (9:16) with label {part.get('label')}")

            cmd = base_cmd + [filter_str, '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-y', str(temp_path)]
            
            timeout_duration = max(60, int(duration * (2 if part['speed'] > 1.0 else 3)))
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration)
            except subprocess.TimeoutExpired:
                print(f"Simple FFmpeg timeout after {timeout_duration}s for part {i+1}. Clip may be too long or heavy to process in one pass.")
                return False

            if result.returncode != 0:
                print(f"Simple FFmpeg error: {result.stderr[-300:]}")
                return False
                
            part_paths.append(temp_path)
            print(f"Part {i+1} created: {temp_path.name}")

        concat_list = Path(temp_dir) / "parts.txt"
        with open(concat_list, 'w') as f:
            for path in part_paths:
                f.write(f"file '{path.resolve()}'\n")

        combine_cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy', '-y', output_path
        ]
        print(f"Combining {len(part_paths)} parts...")
        result = subprocess.run(combine_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"SIMPLE speedup tour created: {output_path}")
            return True
        else:
            print(f"Simple combine failed: {result.stderr[-300:]}")
            return False

def create_tour(user_segments, video_path, video_info, output_path="guided_tour.mp4", api_key=None, quality='high'):
    if not user_segments:
        print("No segments selected!")
        return False
    
    quality_settings = get_quality_settings(quality)
    print(f"Creating {quality} quality tour from {len(user_segments)} segments...")
    
    enhanced = []
    for segment in user_segments:
        enhanced.append({
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'duration': segment['end_time'] - segment['start_time'],
            'scene_type': segment.get('label', 'room'),
            'label': segment['label']
        })
    
    enhanced.sort(key=lambda x: x['start_time'])
    
    temp_clips = []
    for i, segment in enumerate(enhanced):
        clip_path = f"temp/temp_hq_clip_{i}.mp4"
        
        success = extract_clip_hq(
            video_path, video_info, segment['start_time'], segment['end_time'], clip_path,
            speed_factor=1.0, quality_settings=quality_settings, 
            silent_mode=True, room_type=segment['label']
        )
        
        if success:
            temp_clips.append(clip_path)
            print(f"HQ Clip {i+1}: {segment['scene_type']} ({segment['duration']:.1f}s)")
        else:
            print(f"Failed to extract HQ clip {i+1}")
    
    if temp_clips:
        success = combine_clips_hq(temp_clips, output_path, quality_settings)
    else:
        print("No clips to combine")
        success = False
    
    for clip in temp_clips:
        if os.path.exists(clip):
            os.unlink(clip)
    
    return success 