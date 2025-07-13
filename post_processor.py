import os
import subprocess

def add_qr_overlay(input_video, qr_image_path, output_path=None, position='bottom_right'):
    input_video = str(input_video)
    qr_image_path = str(qr_image_path)

    if not os.path.exists(input_video):
        print(f"Video not found for QR overlay: {input_video}")
        return False
    if not os.path.exists(qr_image_path):
        print(f"QR image not found: {qr_image_path}")
        return False

    pos_map = {
        'top_left': ('50', '50'),
        'top_right': ('W-w-30', '30'),  
        'bottom_left': ('50', 'H-h-50'),
        'bottom_right': ('W-w-50', 'H-h-50'),
    }
    x_expr, y_expr = pos_map.get(position, ('W-w-30', '30'))  

    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_qr{ext}"

    cmd = [
        'ffmpeg', '-i', input_video,
        '-i', qr_image_path,
        '-filter_complex', f"[1:v]scale=120:120[qr];[0:v][qr]overlay={x_expr}:{y_expr}",
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'copy',
        '-threads', '4',
        '-movflags', '+faststart',
        '-y', output_path
    ]
    print(f"Overlaying QR code → {output_path}")
    print(f"DEBUG: QR overlay FFmpeg command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(f"DEBUG: QR overlay return code: {result.returncode}")
        if result.returncode != 0:
            print(f"QR overlay failed: {result.stderr[-300:]}")
            print("Trying fallback method with reduced quality...")
            return _qr_overlay_fallback(input_video, qr_image_path, output_path, x_expr, y_expr, replace_in_place)
        else:
            print("QR overlay FFmpeg command completed successfully")
    except subprocess.TimeoutExpired:
        print("QR overlay timed out, trying fallback method with reduced quality...")
        return _qr_overlay_fallback(input_video, qr_image_path, output_path, x_expr, y_expr, replace_in_place)

    if not os.path.exists(output_path):
        print("QR overlay failed: output file was not created")
        return False
        
    output_size = os.path.getsize(output_path)
    if output_size < 1000:
        print(f"QR overlay failed: output file too small ({output_size} bytes)")
        return False
        
    print(f"QR overlay output file size: {output_size / (1024 * 1024):.1f}MB")

    if replace_in_place:
        try:
            os.replace(output_path, input_video)
            print("In-place QR overlay complete")
            return True
        except OSError as exc:
            print(f" Could not replace original video: {exc}")
            return False

    print("QR overlay complete")
    return True

def add_combined_overlays(input_video, agent_name, agency_name, agent_phone=None, qr_image_path=None, qr_position='top_right', output_path=None):

    input_video = str(input_video)
    print(f"DEBUG: Combined overlays function called with: '{agent_name}' @ '{agency_name}' | {agent_phone}, QR: {qr_image_path}")
    print(f"DEBUG: Input video: {input_video}")
    
    if not os.path.exists(input_video):
        print(f"Video not found for combined overlays: {input_video}")
        return False
    
    if not agent_name or not agency_name:
        print(f"Agent name and agency name are required (got: '{agent_name}', '{agency_name}')")
        return False
    
    if qr_image_path and not os.path.exists(qr_image_path):
        print(f"QR image not found: {qr_image_path}")
        return False
    
    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_combined{ext}"
    
    print(f"DEBUG: Output path: {output_path}")
    print(f"DEBUG: Replace in place: {replace_in_place}")
    
    try:
        agent_display = agent_name.replace('_', ' ').title()
        agency_display = agency_name.replace('_', ' ').title()
        
        print(f"DEBUG: Display names: '{agent_display}' @ '{agency_display}' | {agent_phone}")
        
        if qr_image_path:
            pos_map = {
                'top_left': ('50', '50'),
                'top_right': ('W-w-30', '30'),  
                'bottom_left': ('50', 'H-h-50'),
                'bottom_right': ('W-w-50', 'H-h-50'),
            }
            x_expr, y_expr = pos_map.get(qr_position, ('W-w-30', '30'))
            
            text_overlays = [
                f"drawtext=text='{agent_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
                f"fontsize=72:fontcolor=white:shadowcolor=black:shadowx=4:shadowy=2:"
                f"x=50:y=150",
                f"drawtext=text='{agency_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
                f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2:"
                f"x=50:y=230"
            ]
            
            if agent_phone:
                text_overlays.append(
                    f"drawtext=text='{agent_phone}':fontfile=/Windows/Fonts/arialbd.ttf:"
                    f"fontsize=42:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2:"
                    f"x=50:y=300"
                )
            
            text_overlay = ",".join(text_overlays)
            
            filter_complex = (
                f"[1:v]scale=180:180[qr];"
                f"[0:v]{text_overlay}[txt];"
                f"[txt][qr]overlay={x_expr}:{y_expr}"
            )
            
            cmd = [
                'ffmpeg', 
                '-i', input_video,
                '-i', qr_image_path,
                '-filter_complex', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-threads', '2',  
                '-tune', 'fastdecode',  
                '-x264-params', 'ref=1:subme=1:me=hex:trellis=0',  
                '-bufsize', '20M',  
                '-movflags', '+faststart',
                '-c:a', 'copy',  
                '-y', output_path
            ]
            print(f"Memory-optimized combined overlays (agent + QR): '{agent_name}' @ '{agency_name}' | {agent_phone} + QR → {output_path}")
            
        else:
            text_overlays = [
                f"drawtext=text='{agent_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
                f"fontsize=72:fontcolor=white:shadowcolor=black:shadowx=4:shadowy=2:"
                f"x=50:y=150",
                f"drawtext=text='{agency_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
                f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2:"
                f"x=50:y=230"
            ]
            
            if agent_phone:
                text_overlays.append(
                    f"drawtext=text='{agent_phone}':fontfile=/Windows/Fonts/arialbd.ttf:"
                    f"fontsize=42:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2:"
                    f"x=50:y=300"
                )
            
            text_overlay = ",".join(text_overlays)
            
            cmd = [
                'ffmpeg', 
                '-i', input_video,
                '-vf', text_overlay,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '23',
                '-threads', '2',  
                '-tune', 'fastdecode',  
                '-x264-params', 'ref=1:subme=1:me=hex:trellis=0',  
                '-bufsize', '15M',  
                '-movflags', '+faststart',
                '-c:a', 'copy',  
                '-y', output_path
            ]
            print(f"Memory-optimized agent watermark: '{agent_name}' @ '{agency_name}' | {agent_phone} → {output_path}")
        
        print(f"DEBUG: Memory-optimized combined FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print(f"DEBUG: Combined FFmpeg return code: {result.returncode}")
        if result.stdout:
            print(f"DEBUG: Combined FFmpeg stdout: {result.stdout[-200:]}")
        if result.stderr:
            print(f"DEBUG: Combined FFmpeg stderr: {result.stderr[-300:]}")
        
        if result.returncode != 0:
            print(f"Combined overlays failed, trying fallback...")
            print(f"Error was: {result.stderr[-300:]}")
            
            simple_text_overlays = [
                f"drawtext=text='{agent_display}':x=30:y=100:fontsize=64:fontcolor=white:shadowcolor=black:shadowx=4:shadowy=2",
                f"drawtext=text='{agency_display}':x=30:y=180:fontsize=40:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2"
            ]
            
            if agent_phone:
                simple_text_overlays.append(
                    f"drawtext=text='{agent_phone}':x=30:y=240:fontsize=36:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2"
                )
            
            simple_text_overlay = ",".join(simple_text_overlays)
            
            if qr_image_path:
                simple_filter = (
                    f"[1:v]scale=160:160[qr];"
                    f"[0:v]{simple_text_overlay}[txt];"
                    f"[txt][qr]overlay={x_expr}:{y_expr}"
                )
                
                simple_cmd = [
                    'ffmpeg', 
                    '-i', input_video,
                    '-i', qr_image_path,
                    '-filter_complex', simple_filter,
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '30',
                    '-threads', '2',  
                    '-tune', 'fastdecode',  
                    '-x264-params', 'ref=1:subme=1:me=hex:trellis=0',  
                    '-bufsize', '10M',  
                    '-movflags', '+faststart',
                    '-c:a', 'copy', 
                    '-y', output_path
                ]
            else:
                simple_cmd = [
                    'ffmpeg', 
                    '-i', input_video,
                    '-vf', simple_text_overlay,
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '30',
                    '-threads', '2',  
                    '-tune', 'fastdecode',  
                    '-x264-params', 'ref=1:subme=1:me=hex:trellis=0',  
                    '-bufsize', '8M',   
                    '-movflags', '+faststart',
                    '-c:a', 'copy',  
                    '-y', output_path
                ]
            
            print(f"Trying memory-optimized fallback: {' '.join(simple_cmd)}")
            simple_result = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=180)
            
            if simple_result.returncode != 0:
                print(f"Memory-optimized fallback also failed: {simple_result.stderr[-300:]}")
                return False
            else:
                print("Memory-optimized fallback succeeded!")
        else:
            print("Memory-optimized combined overlays succeeded!")
        
    except subprocess.TimeoutExpired:
        print("Combined overlays timed out")
        return False
    except Exception as e:
        print(f"Combined overlays error: {e}")
        return False
    
    if not os.path.exists(output_path):
        print("Combined overlays failed: output file was not created")
        return False
        
    output_size = os.path.getsize(output_path)
    input_size = os.path.getsize(input_video)
    
    if output_size < 1000:
        print(f"Combined overlays failed: output file too small ({output_size} bytes)")
        return False
        
    print(f"DEBUG: File sizes - Input: {input_size}, Output: {output_size}")
    
    if output_size < (input_size * 0.8):
        print(f"Warning: Output file significantly smaller than input ({output_size} vs {input_size})")
    else:
        print(f"File size check passed")
    
    if replace_in_place:
        try:
            print(f"DEBUG: Replacing original file: {output_path} → {input_video}")
            print(f"DEBUG: Combined overlays file size: {os.path.getsize(output_path)}")
            os.replace(output_path, input_video)
            print(f"In-place combined overlays complete")
            print(f"DEBUG: Final file size: {os.path.getsize(input_video)}")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            return False
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Combined overlays complete: {output_path} ({file_size:.1f}MB)")
    return True

def _qr_overlay_fallback(input_video, qr_image_path, output_path, x_expr, y_expr, replace_in_place):
    print("Using QR overlay fallback method with lower quality")
    
    cmd = [
        'ffmpeg', '-i', input_video,
        '-i', qr_image_path,
        '-filter_complex', f"[1:v]scale=100:100[qr];[0:v][qr]overlay={x_expr}:{y_expr}",
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '30',
        '-c:a', 'copy',
        '-threads', '4',
        '-movflags', '+faststart',
        '-y', output_path
    ]
    
    print(f"DEBUG: QR fallback FFmpeg command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"QR fallback failed: {result.stderr[-200:]}")
            return False
    except subprocess.TimeoutExpired:
        print("QR fallback also timed out")
        return False
        
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        print("QR fallback failed: invalid output file")
        return False
        
    if replace_in_place:
        try:
            os.replace(output_path, input_video)
            print("In-place QR fallback overlay complete")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            return False
            
    print("QR fallback overlay complete")
    return True

def add_music_overlay(input_video, music_path, volume=0.3, output_path=None):
    input_video = str(input_video)
    music_path = str(music_path)
    
    if not os.path.exists(input_video):
        print(f"Video not found for music overlay: {input_video}")
        return False
    if not os.path.exists(music_path):
        print(f"Music file not found: {music_path}")
        return False
    
    volume = max(0.0, min(1.0, float(volume)))
    
    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_music{ext}"
    
    try:
        probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', input_video]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        
        if probe_result.returncode == 0:
            actual_video_duration = float(probe_result.stdout.strip())
        else:
            print(f"Warning: Could not get video duration")
            actual_video_duration = 60
        
        print("Adding music as primary audio track (looping to match processed video duration)")
        cmd = [
            'ffmpeg', 
            '-i', input_video,
            '-stream_loop', '-1',
            '-i', music_path,
            '-c:v', 'copy',
            '-map', '0:v',
            '-map', '1:a',
            '-filter:a', f'volume={volume}',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-t', str(actual_video_duration),
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        print(f"Adding music overlay: volume={volume:.2f}, looping music to {actual_video_duration:.1f}s → {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode != 0:
            print(f"Music overlay failed: {result.stderr[-300:]}")
            return False
        
    except subprocess.TimeoutExpired:
        print("Music overlay timed out")
        return False
    except Exception as e:
        print(f"Music overlay error: {e}")
        return False
    
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        print("Music overlay failed: output file is invalid")
        return False
    
    if replace_in_place:
        try:
            os.replace(output_path, input_video)
            print("In-place music overlay complete")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            return False
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Music overlay complete: {output_path} ({file_size:.1f}MB)")
    return True 

def add_agent_watermark(input_video, agent_name, agency_name, agent_phone=None, output_path=None):
    input_video = str(input_video)
    print(f"DEBUG: Watermark function called with: '{agent_name}' @ '{agency_name}' | {agent_phone}")
    print(f"DEBUG: Input video: {input_video}")
    
    if not os.path.exists(input_video):
        print(f"Video not found for agent watermark: {input_video}")
        return False
    
    if not agent_name or not agency_name:
        print(f"Agent name and agency name are required for watermark (got: '{agent_name}', '{agency_name}')")
        return False
    
    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_agent{ext}"
    
    print(f"DEBUG: Output path: {output_path}")
    print(f"DEBUG: Replace in place: {replace_in_place}")
    
    agent_clean = agent_name.replace("'", "\\'").replace(":", "\\:")
    agency_clean = agency_name.replace("'", "\\'").replace(":", "\\:")
    phone_clean = agent_phone.replace("'", "\\'").replace(":", "\\:") if agent_phone else None
    print(f"DEBUG: Cleaned names: '{agent_clean}' @ '{agency_clean}' | {phone_clean}")
    
    try:
        agent_display = agent_name.replace('_', ' ').title()
        agency_display = agency_name.replace('_', ' ').title()
        
        print(f"DEBUG: Display names: '{agent_display}' @ '{agency_display}' | {agent_phone}")
        
        text_overlays = [
            f"drawtext=text='{agent_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
            f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1:"
            f"x=50:y=150",
            f"drawtext=text='{agency_display}':fontfile=/Windows/Fonts/arialbd.ttf:"
            f"fontsize=32:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1:"
            f"x=50:y=200"
        ]
        
        if agent_phone:
            text_overlays.append(
                f"drawtext=text='{agent_phone}':fontfile=/Windows/Fonts/arialbd.ttf:"
                f"fontsize=28:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1:"
                f"x=50:y=240"
            )
        
        text_overlay = ",".join(text_overlays)
        
        print(f"DEBUG: Using watermark overlay: {text_overlay}")
        
        cmd = [
            'ffmpeg', 
            '-i', input_video,
            '-vf', text_overlay,
            '-c:a', 'copy',  
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        print(f"Adding agent watermark: '{agent_name}' @ '{agency_name}' | {agent_phone} → {output_path}")
        print(f"DEBUG: FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        print(f"DEBUG: FFmpeg return code: {result.returncode}")
        if result.stdout:
            print(f"DEBUG: FFmpeg stdout: {result.stdout[-200:]}")
        if result.stderr:
            print(f"DEBUG: FFmpeg stderr: {result.stderr[-300:]}")
        
        if result.returncode != 0:
            print(f"Agent watermark failed with font, trying without font...")
            print(f"Error was: {result.stderr[-300:]}")
            
            simple_text_overlays = [
                f"drawtext=text='{agent_display}':x=30:y=100:fontsize=32:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1",
                f"drawtext=text='{agency_display}':x=30:y=140:fontsize=24:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1"
            ]
            
            if agent_phone:
                simple_text_overlays.append(
                    f"drawtext=text='{agent_phone}':x=30:y=175:fontsize=20:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=1"
                )
            
            simple_filter = ",".join(simple_text_overlays)
            
            simple_cmd = [
                'ffmpeg', 
                '-i', input_video,
                '-vf', simple_filter,
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-movflags', '+faststart',
                '-y', output_path
            ]
            
            print(f"Trying simple watermark: {' '.join(simple_cmd)}")
            simple_result = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=180)
            
            if simple_result.returncode != 0:
                print(f"Simple watermark also failed: {simple_result.stderr[-300:]}")
                return False
            else:
                print("Simple watermark succeeded!")
        else:
            print("Complex watermark succeeded!")
        
    except subprocess.TimeoutExpired:
        print("Agent watermark timed out")
        return False
    except Exception as e:
        print(f"Agent watermark error: {e}")
        return False
    
    if not os.path.exists(output_path):
        print("Agent watermark failed: output file was not created")
        return False
        
    output_size = os.path.getsize(output_path)
    input_size = os.path.getsize(input_video)
    
    if output_size < 1000:
        print(f"Agent watermark failed: output file too small ({output_size} bytes)")
        return False
        
    print(f"DEBUG: File sizes - Input: {input_size}, Output: {output_size}")
    
    if output_size < (input_size * 0.8):
        print(f"Warning: Output file significantly smaller than input ({output_size} vs {input_size})")
    else:
        print(f"File size check passed")
    
    if replace_in_place:
        try:
            print(f"DEBUG: Replacing original file: {output_path} → {input_video}")
            print(f"DEBUG: Watermarked file size: {os.path.getsize(output_path)}")
            os.replace(output_path, input_video)
            print(f"In-place agent watermark complete")
            print(f"DEBUG: Final file size: {os.path.getsize(input_video)}")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            return False
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Agent watermark complete: {output_path} ({file_size:.1f}MB)")
    return True 