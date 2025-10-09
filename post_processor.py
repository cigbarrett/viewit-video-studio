import os
import subprocess

def _validate_video_file(video_path, timeout=10):
    
    try:
        
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            return duration > 0
        else:
            print(f"FFprobe validation failed for {video_path}: {result.stderr}")
            return False
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError) as e:
        print(f"Video validation error for {video_path}: {e}")
        return False


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
        print(f"Creating music overlay: {input_video} → {output_path}")
    
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
            # Remove original file first
            if os.path.exists(input_video):
                os.remove(input_video)
                print(f"Removed original video: {input_video}")
            
            # Move music overlay to original location
            os.rename(output_path, input_video)
            print("In-place music overlay complete")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            # Try to restore original if replacement failed
            if os.path.exists(output_path) and not os.path.exists(input_video):
                try:
                    os.rename(output_path, input_video)
                    print("Restored original video after failed replacement")
                except:
                    pass
            return False
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Music overlay complete: {output_path} ({file_size:.1f}MB)")
    return True 

 

def add_agent_property_overlays(input_video, agent_name, agent_phone=None, logo_path=None, beds=None, baths=None, sqft=None, price=None, qr_image_path=None, output_path=None):
    input_video = str(input_video)
    print(f"Property overlay params: beds={beds}, baths={baths}, sqft={sqft}, logo_path={logo_path}")
    
    if not os.path.exists(input_video):
        print(f"Video not found for property overlays: {input_video}")
        return False
    
    if not _validate_video_file(input_video):
        print(f"Video file is corrupted or incomplete: {input_video}")
        return False

    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_prop{ext}"

    
    has_overlays = any([
        agent_name, agent_phone, beds, baths, sqft, 
        (logo_path and os.path.exists(logo_path)),
        (qr_image_path and os.path.exists(qr_image_path))
    ])
    
    if not has_overlays:
        print('No overlays provided; leaving video unchanged')
        if replace_in_place:
            return True
        else:
            
            import shutil
            shutil.copy2(input_video, output_path)
            return True

    
    inputs = ['-i', input_video]
    filter_parts = []
    filter_parts.append('[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[scaled]')
    chain_tag = 'scaled'
    idx = 1

    
    if logo_path and os.path.exists(logo_path):
        inputs += ['-i', logo_path]
        filter_parts.append(f'[{idx}:v]scale=800:-1,format=rgba,colorchannelmixer=aa=0.3[logo]')  
        filter_parts.append(f'[{chain_tag}][logo]overlay=(W-w)/2:(H-h)/2[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1

    
    
    
    vertical_offset = 0
    base_y = 1100  
    
    
    bed_icon_path = 'static/1.png'
    if beds and os.path.exists(bed_icon_path):
        y_pos = base_y + vertical_offset
        print(f"Adding bed icon: {bed_icon_path} at y={y_pos}")
        inputs += ['-i', bed_icon_path]
        filter_parts.append(f'[{idx}:v]scale=80:80[bed]')
        filter_parts.append(f'[{chain_tag}][bed]overlay=50:{y_pos}[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1
        vertical_offset += 120

    
    bath_icon_path = 'static/2.png'
    if baths and os.path.exists(bath_icon_path):
        y_pos = base_y + vertical_offset
        print(f"Adding bath icon: {bath_icon_path} at y={y_pos}")
        inputs += ['-i', bath_icon_path]
        filter_parts.append(f'[{idx}:v]scale=80:80[bath]')
        filter_parts.append(f'[{chain_tag}][bath]overlay=50:{y_pos}[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1
        vertical_offset += 120

    
    sqft_icon_path = 'static/3.png'
    if sqft and os.path.exists(sqft_icon_path):
        y_pos = base_y + vertical_offset
        print(f"Adding sqft icon: {sqft_icon_path} at y={y_pos}")
        inputs += ['-i', sqft_icon_path]
        filter_parts.append(f'[{idx}:v]scale=80:80[sqft]')
        filter_parts.append(f'[{chain_tag}][sqft]overlay=50:{y_pos}[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1
        vertical_offset += 120

    
    if qr_image_path and os.path.exists(qr_image_path):
        try:
            qr_size = os.path.getsize(qr_image_path)
            if qr_size > 100:  
                inputs += ['-i', qr_image_path]
                filter_parts.append(f'[{idx}:v]scale=150:150[qr]')
                filter_parts.append(f'[{chain_tag}][qr]overlay=W-w-50:50[o{idx}]')
                chain_tag = f'o{idx}'
                idx += 1
                print(f"QR code added: {qr_image_path} ({qr_size} bytes)")
            else:
                print(f"QR file too small, skipping: {qr_image_path} ({qr_size} bytes)")
        except OSError as e:
            print(f"QR file error, skipping: {qr_image_path} - {e}")

    def escape_text(text):
        if not text:
            return ""
        text = str(text)
        text = text.replace('\\', '\\\\')  
        text = text.replace(':', '\\:')    
        text = text.replace("'", "\\'")    
        text = text.replace('"', '\\"')    
        text = text.replace('[', '\\[')    
        text = text.replace(']', '\\]')
        text = text.replace('=', '\\=')    
        text = text.replace(';', '\\;')    
        text = text.replace(',', '\\,')    
        return text
    
    
    text_overlays = []
    if agent_name:
        safe_agent = escape_text(agent_name)
        text_overlays.append(
            f"drawtext=text='{safe_agent}':fontfile=fonts/Poppins.ttf:fontsize=40:fontcolor=white:shadowcolor=black@0.8:shadowx=3:shadowy=3:x=76:y=200")
    if agent_phone:
        safe_phone = escape_text(agent_phone)
        text_overlays.append(
            f"drawtext=text='{safe_phone}':fontfile=fonts/Poppins.ttf:fontsize=40:fontcolor=white:shadowcolor=black@0.8:shadowx=3:shadowy=3:x=76:y=280")
    
    text_vertical_offset = 0
    text_base_y = 1100  
    
    
    if beds:
        safe_beds = escape_text(beds)
        y_pos = text_base_y + text_vertical_offset + 30
        print(f"Adding beds text: '{safe_beds}' at y={y_pos}")
        text_overlays.append(
            f"drawtext=text='{safe_beds}':fontfile=fonts/Poppins.ttf:fontsize=40:fontcolor=white:shadowcolor=black@0.8:shadowx=4:shadowy=4:x=140:y={y_pos}")
        text_vertical_offset += 120
    
    
    if baths:
        safe_baths = escape_text(baths)
        y_pos = text_base_y + text_vertical_offset + 30
        print(f"Adding baths text: '{safe_baths}' at y={y_pos}")
        text_overlays.append(
            f"drawtext=text='{safe_baths}':fontfile=fonts/Poppins.ttf:fontsize=40:fontcolor=white:shadowcolor=black@0.8:shadowx=4:shadowy=4:x=140:y={y_pos}")
        text_vertical_offset += 120
    
    
    if sqft:
        safe_sqft = escape_text(f"{sqft} sq.ft.")
        y_pos = text_base_y + text_vertical_offset + 30
        print(f"Adding sqft text: '{safe_sqft}' at y={y_pos}")
        text_overlays.append(
            f"drawtext=text='{safe_sqft}':fontfile=fonts/Poppins.ttf:fontsize=40:fontcolor=white:shadowcolor=black@0.8:shadowx=4:shadowy=4:x=140:y={y_pos}")

    
    if text_overlays:
        draw_chain = ','.join(text_overlays)
        filter_parts.append(f'[{chain_tag}]{draw_chain}[outv]')
        final_map = '[outv]'
    else:
        final_map = f'[{chain_tag}]'

    filter_complex = ';'.join(filter_parts)

    
    cmd = ['ffmpeg'] + inputs + [
        '-filter_complex', filter_complex,
        '-map', final_map,
        '-map', '0:a?',
        '-c:v', 'libx264',
        '-preset', 'veryfast',  
        '-crf', '20',  
        '-threads', '2',
        '-tune', 'fastdecode',
        '-x264-params', 'ref=1:subme=1:me=hex:trellis=0',  
        '-maxrate', '15M',  
        '-bufsize', '15M',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', output_path
    ]

    print('Running optimized agent/property overlay:')
    print(' '.join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print('Overlay failed:', result.stderr[-300:])
            return False
    except subprocess.TimeoutExpired:
        print('Overlay timed out')
        return False

    if replace_in_place:
        try:
            os.replace(output_path, input_video)
            return True
        except OSError as exc:
            print('Could not replace original video:', exc)
            return False

    return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
