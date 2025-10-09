import os
import tempfile
import subprocess
from pathlib import Path
from video_utils import get_quality_settings
from video_processor import extract_clip_simple, extract_clip_hq, combine_clips, combine_clips_hq, extract_clips_parallel

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

    print(f"Creating OPTIMIZED SIMPLE tour from {len(user_segments)} segments...")
    
    display_names = number_duplicate_segments(user_segments)
    
    sorted_segments = sorted(user_segments, key=lambda x: x['start_time'])
    
    
    for i, segment in enumerate(sorted_segments):
        segment['display_name'] = display_names.get(i, segment.get('label'))
    
    temp_dir = project_temp_dir or 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    
    if len(sorted_segments) > 1:
        print("Using parallel clip extraction for better performance...")
        temp_clips = extract_clips_parallel(video_path, video_info, sorted_segments, temp_dir, max_workers=2)
    else:
        
        temp_clips = []
        for i, segment in enumerate(sorted_segments):
            clip_path = os.path.join(temp_dir, f"simple_clip_{i}.mp4")
            
            success = extract_clip_simple(
                video_path, video_info, segment['start_time'], segment['end_time'], 
                clip_path, room_type=segment['display_name']
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
        print(f"OPTIMIZED SIMPLE tour created: {output_path}")
    
    return success

def create_speedup_tour_simple(user_segments, video_path, video_info, output_path="guided_tour_ffmpeg.mp4", speed_factor=3.0, project_temp_dir=None):
    if not user_segments:
        print("No segments selected!")
        return False

    display_names = number_duplicate_segments(user_segments)
    
    
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

    
    temp_dir = project_temp_dir or 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    import uuid
    concat_file = os.path.join(temp_dir, f'speedup_concat_{uuid.uuid4().hex[:8]}.txt')
    
    
    part_paths = []
    for i, part in enumerate(timeline):
        start_time = part['start']
        end_time = part['end']
        duration = end_time - start_time
        
        part_filename = f"part_{i}.mp4"
        part_path = os.path.join(temp_dir, part_filename)
        part_paths.append(part_path)
        
        base_cmd = [
            'ffmpeg', '-ss', str(start_time), '-t', str(duration),
            '-i', str(video_path),
            '-vf'
        ]
        
        if part['speed'] > 1.0:
            filter_str = f"setpts=PTS/{part['speed']},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            print(f"Speedup gap: {start_time:.1f}s to {end_time:.1f}s at {part['speed']}x (9:16)")
        else:
            filters = [
                "setpts=PTS*1",  
                "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            ]
            if part.get('display_name'):
                display_text = part['display_name']
                text_overlay = (
                    f"drawtext=text='{display_text}':fontfile=fonts/Poppins.ttf:"
                    f"fontsize=70:fontcolor=white:shadowcolor=black@0.8:shadowx=4:shadowy=4:"
                    f"x=(w-text_w)/2:y=h-text_h-200"
                )
                filters.append(text_overlay)
            filter_str = ",".join(filters)
            print(f"Normal segment: {start_time:.1f}s to {end_time:.1f}s (9:16) with label {part.get('display_name', part.get('label'))}")

        cmd = base_cmd + [
            filter_str, 
            '-an', 
            '-c:v', 'libx264', 
            '-preset', 'veryfast',  
            '-crf', '20',  
            '-r', '30',    
            '-g', '30',    
            '-keyint_min', '30',  
            '-sc_threshold', '0',  
            '-maxrate', '15M',  
            '-bufsize', '15M',
            '-y', part_path
        ]
        
        from video_processor import _get_concurrent_resource_settings, _release_ffmpeg_process
        resource_settings = _get_concurrent_resource_settings()
        
        base_timeout = max(30, int(duration * 1.5))  
        timeout_duration = int(base_timeout * resource_settings['timeout_multiplier'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration)
        except subprocess.TimeoutExpired:
            print(f"Part {i+1} timeout after {timeout_duration}s")
            _release_ffmpeg_process()
            return False

        if result.returncode != 0:
            print(f"Part {i+1} failed: {result.stderr[-300:]}")
            _release_ffmpeg_process()
            return False
            
        print(f"Part {i+1} created: {part_filename}")
        _release_ffmpeg_process()

    
    with open(concat_file, 'w') as f:
        for part_path in part_paths:
            f.write(f"file '{os.path.abspath(part_path)}'\n")

    
    from video_processor import _get_concurrent_resource_settings, _release_ffmpeg_process
    resource_settings = _get_concurrent_resource_settings()
    
    combine_cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c:v', 'libx264',
        '-preset', 'veryfast',  
        '-crf', '20',  
        '-r', '30',  
        '-g', '30',  
        '-maxrate', '15M',  
        '-bufsize', '15M',
        '-movflags', '+faststart',
        '-threads', resource_settings['threads'],
        '-y', output_path
    ]
    
    base_timeout = 120 if len(timeline) > 10 else 90  
    timeout_duration = int(base_timeout * resource_settings['timeout_multiplier'])
    
    print(f"FAST combining {len(timeline)} parts: {resource_settings['threads']} threads, {timeout_duration}s timeout")
    
    try:
        result = subprocess.run(combine_cmd, capture_output=True, text=True, timeout=timeout_duration)
    except subprocess.TimeoutExpired:
        print(f"Combine timeout after {timeout_duration}s")
        _release_ffmpeg_process()
        return False
    finally:
        
        if os.path.exists(concat_file):
            os.remove(concat_file)
        for part_path in part_paths:
            if os.path.exists(part_path):
                os.remove(part_path)

    if result.returncode == 0:
        print(f"FAST speedup tour created: {output_path}")
        _release_ffmpeg_process()
        return True
    else:
        print(f"Combine failed: {result.stderr[-300:]}")
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