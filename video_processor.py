import os
import subprocess
from video_utils import get_quality_settings

def extract_clip_simple(video_path, video_info, start, end, output, room_type=None):
    try:
        width = video_info.get('width', 1920)
        height = video_info.get('height', 1080)
        fps = video_info.get('fps', 30)
        
        filters = []

        filters.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
        if width > 1080 or height > 1920:
            print(f"Resizing from {width}x{height} to 1080x1920 for standardised output")

        if room_type:
            display_text = room_type.replace('_', ' ').upper()
            fontsize = max(width // 25, 90)
            text_overlay = (
                f"drawtext=text='{display_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"fontsize={fontsize * 1.5}:fontcolor=black:"
                f"x=(w-text_w)/2:y=h-text_h-275"
            )
            filters.append(text_overlay)

        filter_arg = []
        if filters:
            filter_arg = ['-vf', ','.join(filters)]
        
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-ss', str(start), '-t', str(end - start),
            '-c:v', 'libx264',
            '-an',  
            '-preset', 'veryfast',
            '-crf', '23',
            '-r', str(fps),  
            '-g', str(fps),  
            '-keyint_min', str(fps),  
            '-sc_threshold', '0',  
            '-maxrate', '5M',
            '-bufsize', '5M',   
            '-avoid_negative_ts', 'make_zero',
            '-threads', '2',
            '-tune', 'fastdecode',  
            '-x264-params', 'ref=2:subme=2:me=hex:trellis=0'  
        ] + filter_arg + ['-y', output]
        
        print(f"Memory-optimized clip: {start:.1f}s-{end:.1f}s → {output}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return True
        else:
            print(f"Normal clip failed: {result.stderr[-500:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"Normal clip timeout: {output}")
        return False
    except Exception as e:
        print(f"Normal clip error: {e}")
        return False

def extract_clip_hq(video_path, video_info, start, end, output, speed_factor=1.0, quality_settings=None, silent_mode=True, room_type=None):
    if quality_settings is None:
        quality_settings = get_quality_settings('high')
        
    try:
        duration = end - start
        width = video_info.get('width', 1920)
        height = video_info.get('height', 1080)
        
        if speed_factor != 1.0:
            return extract_speedup_clip_fast(video_path, video_info, start, end, output, speed_factor, room_type)
        
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-ss', str(start), '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', quality_settings['preset'],
            '-crf', quality_settings['crf'],
            '-movflags', '+faststart',
            '-avoid_negative_ts', 'make_zero',
            '-threads', quality_settings.get('threads', '2')
        ]
        
        if quality_settings.get('memory_optimized', False):
            cmd.extend([
                '-tune', 'fastdecode',
                '-x264-params', 'ref=2:subme=2:me=hex:trellis=0:8x8dct=0'
            ])
        
        if quality_settings['maxrate'] != 'unlimited':
            cmd.extend(['-maxrate', quality_settings['maxrate']])
            cmd.extend(['-bufsize', quality_settings['bufsize']])
        
        if room_type:
            display_text = room_type.replace('_', ' ').upper()
            fontsize = max(width // 25, 48)
            text_filter = (
                f"drawtext=text='{display_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"fontsize={fontsize * 1.5}:fontcolor=black:"
                f"x=(w-text_w)/2:y=h-text_h-275"
            )
            cmd.extend(['-vf', text_filter])
        
        if silent_mode:
            cmd.extend(['-an'])
        else:
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])  
        
        cmd.extend(['-y', output])
        
        print(f"Memory-optimized HQ clip: {start:.1f}s-{end:.1f}s (bufsize: {quality_settings['bufsize']})")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=quality_settings['timeout'])
        
        if result.returncode == 0:
            file_size = os.path.getsize(output) / (1024 * 1024)  
            print(f"HQ Clip created: {output} ({file_size:.1f}MB)")
            return True
        else:
            print(f"HQ Extraction failed: {result.stderr[-300:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"HQ Extraction timeout (may need to reduce quality setting)")
        return False
    except Exception as e:
        print(f"HQ Extraction error: {e}")
        return False

def extract_speedup_clip_fast(video_path, video_info, start, end, output, speed_factor=1.0, room_type=None):
    try:
        duration = end - start
        width = video_info.get('width', 1920)
        height = video_info.get('height', 1080)
        fps = video_info.get('fps', 30)
        
        filters = [f"setpts=PTS/{speed_factor}"]
        
        filters.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
        if width > 1080 or height > 1920:
            print(f"Resizing from {width}x{height} to 1080x1920 for standardised output")
        
        if room_type:
            display_text = room_type.replace('_', ' ').upper()
            fontsize = max(36, width // 40)  
            text_overlay = (
                f"drawtext=text='{display_text}':fontcolor=black:"
                f"fontsize={fontsize * 1.5}:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"x=(w-text_w)/2:y=h-text_h-275"
            )
            filters.append(text_overlay)
        
        video_filter = ",".join(filters)
        
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-ss', str(start), '-t', str(duration),
            '-filter:v', video_filter,
            '-an',  
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',  
            '-r', str(fps),  
            '-g', str(fps),  
            '-keyint_min', str(fps),  
            '-sc_threshold', '0',  
            '-maxrate', '6M',  
            '-bufsize', '6M',  
            '-threads', '2',  
            '-tune', 'fastdecode',  
            '-x264-params', 'ref=2:subme=2:me=hex:trellis=0',  
            '-movflags', '+faststart',
            '-y', output
        ]
        
        base_timeout = min(90, int(duration * 2.5))
        if width > 2560:
            timeout_duration = base_timeout * 2
        else:
            timeout_duration = base_timeout
        
        print(f"Memory-optimized speedup processing: {timeout_duration}s timeout")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_duration)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output) / (1024 * 1024)
            print(f"Fast speedup clip: {output} ({file_size:.1f}MB)")
            return True
        else:
            print(f"Fast speedup failed: {result.stderr[-200:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"Fast speedup timeout")
        return False
    except Exception as e:
        print(f"Fast speedup error: {e}")
        return False



def combine_clips(clips, output, silent_mode=True, project_temp_dir=None):
    try:
        for clip in clips:
            if not os.path.exists(clip):
                print(f"Missing clip: {clip}")
                return False
        
        
        temp_dir = project_temp_dir or 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        concat_file = os.path.join(temp_dir, 'temp_concat.txt')
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{os.path.abspath(clip)}'\n")
        
        
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', 
            '-i', concat_file,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-r', '30',  
            '-g', '30',  
            '-keyint_min', '30',  
            '-sc_threshold', '0',  
            '-movflags', '+faststart',
            '-y', output
        ]
        
        if silent_mode:
            cmd.extend(['-an'])
            print(f"Combining {len(clips)} clips into silent video → {output}")
        else:
            cmd.extend(['-c:a', 'aac']) 
            print(f"Combining {len(clips)} clips → {output}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  
        
        if os.path.exists(concat_file):
            os.unlink(concat_file)
        
        if result.returncode == 0:
            print(f"Tour created: {output}")
            return True
        else:
            print(f"FFmpeg combine error: {result.stderr}")
            return False
        
    except subprocess.TimeoutExpired:
        print(f"FFmpeg timeout during combine")
        return False
    except Exception as e:
        print(f"Combine error: {e}")
    
    return False

def combine_clips_hq(clips, output, quality_settings, project_temp_dir=None):
    try:
        if not clips:
            print("No clips to combine")
            return False
        
        valid_clips = []
        for clip in clips:
            if os.path.exists(clip) and os.path.getsize(clip) > 1000:
                valid_clips.append(clip)
            else:
                print(f"Skipping invalid clip: {clip}")
        
        if not valid_clips:
            print("No valid clips to combine")
            return False
        
        
        temp_dir = project_temp_dir or 'temp'
        os.makedirs(temp_dir, exist_ok=True)
        
        concat_file = os.path.join(temp_dir, 'temp_concat_hq.txt')
        with open(concat_file, 'w', encoding='utf-8') as f:
            for clip in valid_clips:
                f.write(f"file '{os.path.abspath(clip).replace(os.sep, '/')}'\n")
        
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', concat_file,
            '-c:v', 'libx264',
            '-preset', quality_settings['preset'],
            '-crf', '23',
            '-threads', quality_settings.get('threads', '2'),  
            '-movflags', '+faststart',
            '-avoid_negative_ts', 'make_zero',
            '-an',  
            '-y', output
        ]
        
        if quality_settings.get('memory_optimized', False):
            cmd.extend([
                '-tune', 'fastdecode',
                '-x264-params', 'ref=2:subme=2:me=hex:trellis=0:8x8dct=0'
            ])
        
        if quality_settings['maxrate'] != 'unlimited':
            cmd.extend(['-maxrate', quality_settings['maxrate']])
            cmd.extend(['-bufsize', quality_settings['bufsize']])
        
        print(f"Memory-optimized HQ combining {len(valid_clips)} clips with {quality_settings['preset']} preset (bufsize: {quality_settings['bufsize']})...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=quality_settings['timeout'])
        
        if os.path.exists(concat_file):
            os.remove(concat_file)

        if result.returncode == 0:
            file_size = os.path.getsize(output) / (1024 * 1024)
            print(f"Memory-optimized HQ tour created: {output} ({file_size:.1f}MB)")
            return True
        else:
            print(f"HQ combine failed: {result.stderr[-500:]}")
            return False

    except subprocess.TimeoutExpired:
        print(f"HQ combine timeout")
        return False
    except Exception as e:
        print(f"HQ combine error: {e}")
        return False

 