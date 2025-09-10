import os
import tempfile
import subprocess
from pathlib import Path
from video_utils import get_quality_settings
from video_processor import extract_clip_simple, extract_clip_hq, combine_clips, combine_clips_hq

def number_duplicate_segments(segments):

    if not segments:
        return {}
    
    room_groups = {}
    for i, segment in enumerate(segments):
        room_type = segment.get('label', 'unlabeled')
        if room_type not in room_groups:
            room_groups[room_type] = []
        room_groups[room_type].append(i)
    
    display_names = {}
    for room_type, indices in room_groups.items():
        if len(indices) > 1:
            sorted_indices = sorted(indices, key=lambda i: segments[i]['start_time'])
            for j, segment_index in enumerate(sorted_indices, 1):
                display_names[segment_index] = f"{room_type.replace('_', ' ').upper()} {j}"
        else:
            display_names[indices[0]] = room_type.replace('_', ' ').upper()
    
    return display_names

def create_tour_simple(user_segments, video_path, video_info, output_path="guided_tour.mp4", project_temp_dir=None):
    if not user_segments:
        print("No segments selected!")
        return False

    print(f"Creating SIMPLE segments-only tour from {len(user_segments)} segments...")
    
    display_names = number_duplicate_segments(user_segments)
    
    sorted_segments = sorted(user_segments, key=lambda x: x['start_time'])
    
    
    temp_dir = project_temp_dir or 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_clips = []
    for i, segment in enumerate(sorted_segments):
        clip_path = os.path.join(temp_dir, f"simple_clip_{i}.mp4")
        
        display_name = display_names.get(i, segment.get('label'))
        
        success = extract_clip_simple(
            video_path, video_info, segment['start_time'], segment['end_time'], 
            clip_path, room_type=display_name
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

def create_speedup_tour_simple(user_segments, video_path, video_info, output_path="guided_tour_ffmpeg.mp4", speed_factor=3.0, project_temp_dir=None):
    if not user_segments:
        print("No segments selected!")
        return False

    display_names = number_duplicate_segments(user_segments)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        timeline = []
        current_time = 0.0
        sorted_segments = sorted(user_segments, key=lambda x: x['start_time'])

        for i, segment in enumerate(sorted_segments):
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
                'label': segment.get('label'),
                'display_name': display_names.get(i, segment.get('label', 'unlabeled').replace('_', ' ').upper())
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
                filters = [
                    "setpts=PTS*1",  
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
                ]
                if part.get('display_name'):
                    display_text = part['display_name']
                    text_overlay = (
                        f"drawtext=text='{display_text}':fontfile=Inter:"
                        f"fontsize=65:fontcolor=black:"
                        f"x=(w-text_w)/2:y=h-text_h-250"
                    )
                    filters.append(text_overlay)
                filter_str = ",".join(filters)
                print(f"Normal segment: {part['start']:.1f}s to {part['end']:.1f}s (9:16) with label {part.get('display_name', part.get('label'))}")

            cmd = base_cmd + [
                filter_str, 
                '-an', 
                '-c:v', 'libx264', 
                '-preset', 'veryfast', 
                '-crf', '23',  
                '-r', '30',    
                '-g', '30',    
                '-keyint_min', '30',  
                '-sc_threshold', '0',  
                '-y', str(temp_path)
            ]
            
            
            from video_processor import _get_concurrent_resource_settings, _release_ffmpeg_process
            resource_settings = _get_concurrent_resource_settings()
            
            base_timeout = max(60, int(duration * (2 if part['speed'] > 1.0 else 3)))
            timeout_duration = int(base_timeout * resource_settings['timeout_multiplier'])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration)
            except subprocess.TimeoutExpired:
                print(f"Simple FFmpeg timeout after {timeout_duration}s for part {i+1} (concurrent load). Clip may be too long or heavy to process in one pass.")
                _release_ffmpeg_process()
                return False

            if result.returncode != 0:
                print(f"Simple FFmpeg error: {result.stderr[-300:]}")
                _release_ffmpeg_process()
                return False
                
            part_paths.append(temp_path)
            print(f"Part {i+1} created: {temp_path.name}")
            _release_ffmpeg_process()

        
        import uuid
        concat_list = Path(temp_dir) / f"parts_{uuid.uuid4().hex[:8]}.txt"
        with open(concat_list, 'w') as f:
            for path in part_paths:
                f.write(f"file '{path.resolve()}'\n")

        
        from video_processor import _get_concurrent_resource_settings, _release_ffmpeg_process
        resource_settings = _get_concurrent_resource_settings()
        
        combine_cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', str(concat_list),
            '-c:v', 'libx264',
            '-preset', resource_settings['preset'],
            '-crf', '23',
            '-r', '30',  
            '-g', '30',  
            '-movflags', '+faststart',
            '-threads', resource_settings['threads'],
            '-y', output_path
        ]
        
        
        base_timeout = 90 if len(part_paths) > 5 else 60
        timeout_duration = int(base_timeout * resource_settings['timeout_multiplier'])
        
        print(f"Concurrent speedup combining {len(part_paths)} parts: {resource_settings['threads']} threads, {resource_settings['preset']} preset, {timeout_duration}s timeout")
        try:
            result = subprocess.run(combine_cmd, capture_output=True, text=True, timeout=timeout_duration)
        except subprocess.TimeoutExpired:
            print(f"Simple speedup combine timeout (concurrent load)")
            
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    print(f"Removed partial speedup output file: {output_path}")
                except OSError as e:
                    print(f"Could not remove partial speedup file: {e}")
            _release_ffmpeg_process()
            return False
        finally:
            
            if os.path.exists(concat_list):
                try:
                    os.remove(concat_list)
                except OSError as e:
                    print(f"Could not remove concat file: {e}")

        if result.returncode == 0:
            print(f"SIMPLE speedup tour created: {output_path}")
            _release_ffmpeg_process()
            return True
        else:
            print(f"Simple combine failed: {result.stderr[-300:]}")
            
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    print(f"Removed failed speedup output file: {output_path}")
                except OSError as e:
                    print(f"Could not remove failed speedup file: {e}")
            _release_ffmpeg_process()
            return False

def create_tour(user_segments, video_path, video_info, output_path="guided_tour.mp4", api_key=None, quality='professional', project_temp_dir=None):
    if not user_segments:
        print("No segments selected!")
        return False
    
    quality_settings = get_quality_settings(quality)
    print(f"Creating {quality} quality tour from {len(user_segments)} segments...")
    
    display_names = number_duplicate_segments(user_segments)
    
    enhanced = []
    for segment in user_segments:
        enhanced.append({
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'duration': segment['end_time'] - segment['start_time'],
            'scene_type': segment.get('label', 'room'),
            'label': segment['label'],
            'speed_factor': segment.get('speed_factor', 1.0)   
            
        })
    
    enhanced.sort(key=lambda x: x['start_time'])
    
    
    temp_dir = project_temp_dir or 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_clips = []
    for i, segment in enumerate(enhanced):
        clip_path = os.path.join(temp_dir, f"temp_hq_clip_{i}.mp4")
        
        display_name = display_names.get(i, segment['label'])
        
        success = extract_clip_hq(
            video_path, video_info, segment['start_time'], segment['end_time'], clip_path,
            speed_factor=segment['speed_factor'], quality_settings=quality_settings, 
            silent_mode=True, room_type=display_name
        )
        
        if success:
            temp_clips.append(clip_path)
            speed_text = f" ({segment['speed_factor']}x)" if segment['speed_factor'] != 1.0 else ""
            print(f"HQ Clip {i+1}: {segment['scene_type']}{speed_text} ({segment['duration']:.1f}s)")
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