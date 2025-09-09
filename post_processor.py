import os
import subprocess
import os, subprocess

def add_combined_overlays(input_video, agent_name, agency_name, agent_phone=None, qr_image_path=None, qr_position='top_right', output_path=None):

    input_video = str(input_video)
    print(f"Combined overlays function called with: '{agent_name}' @ '{agency_name}' | {agent_phone}, QR: {qr_image_path}")
    print(f"Input video: {input_video}")
    
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
    
    print(f"Output path: {output_path}")
    print(f"Replace in place: {replace_in_place}")
    
    try:
        agent_display = agent_name.replace('_', ' ').title()
        agency_display = agency_name.replace('_', ' ').title()
        
        print(f"Display names: '{agent_display}' @ '{agency_display}' | {agent_phone}")
        
        if qr_image_path:
            pos_map = {
                'top_left': ('50', '50'),
                'top_right': ('W-w-30', '30'),  
                'bottom_left': ('50', 'H-h-50'),
                'bottom_right': ('W-w-50', 'H-h-50'),
            }
            x_expr, y_expr = pos_map.get(qr_position, ('W-w-30', '30'))
            
            text_overlays = [
                f"drawtext=text='{agent_display}':"
                f"fontfile=Inter:fontsize=64:"
                f"fontcolor=white:shadowcolor=black@0.7:shadowx=2:shadowy=2:"
                f"x=50:y=H*0.75",

                f"drawtext=text='{agency_display}':"
                f"fontfile=Inter:fontsize=44:"
                f"fontcolor=white:shadowcolor=black@0.5:shadowx=2:shadowy=2:"
                f"x=50:y=H*0.75+70"
            ]

            
            if agent_phone:
                text_overlays.append(
                    f"drawtext=text='{agent_phone}':fontfile=Inter:"
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
                f"drawtext=text='{agent_display}':fontfile=Inter:"
                f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=1:shadowy=0:"
                f"x=50:y=150",
                f"drawtext=text='{agency_display}':fontfile=Inter:"
                f"fontsize=48:fontcolor=white:shadowcolor=black:shadowx=1:shadowy=0:"
                f"x=50:y=230"
            ]
            
            if agent_phone:
                text_overlays.append(
                    f"drawtext=text='{agent_phone}':fontfile=Inter:"
                    f"fontsize=42:fontcolor=white:shadowcolor=black:shadowx=1:shadowy=0:"
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
        
        print(f"Memory-optimized combined FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print(f"Combined FFmpeg return code: {result.returncode}")
        if result.stdout:
            print(f"Combined FFmpeg stdout: {result.stdout[-200:]}")
        if result.stderr:
            print(f"Combined FFmpeg stderr: {result.stderr[-300:]}")
        
        if result.returncode != 0:
            print(f"Combined overlays failed, trying fallback...")
            print(f"Error was: {result.stderr[-300:]}")
            
            simple_text_overlays = [
                f"drawtext=text='{agent_display}':fontfile=Inter:x=30:y=300:fontsize=64:fontcolor=white:shadowcolor=black:shadowx=4:shadowy=2",
                f"drawtext=text='{agency_display}':fontfile=Inter:x=30:y=260:fontsize=40:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2"
            ]
            
            if agent_phone:
                simple_text_overlays.append(
                    f"drawtext=text='{agent_phone}':fontfile=Inter:x=30:y=240:fontsize=36:fontcolor=white:shadowcolor=black:shadowx=3:shadowy=2"
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
        
    print(f"File sizes - Input: {input_size}, Output: {output_size}")
    
    if output_size < (input_size * 0.8):
        print(f"Warning: Output file significantly smaller than input ({output_size} vs {input_size})")
    else:
        print(f"File size check passed")
    
    if replace_in_place:
        try:
            print(f"Replacing original file: {output_path} → {input_video}")
            print(f"Combined overlays file size: {os.path.getsize(output_path)}")
            os.replace(output_path, input_video)
            print(f"In-place combined overlays complete")
            print(f"Final file size: {os.path.getsize(input_video)}")
            return True
        except OSError as exc:
            print(f"Could not replace original video: {exc}")
            return False
    
    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Combined overlays complete: {output_path} ({file_size:.1f}MB)")
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

 

def add_agent_property_overlays(input_video, agent_name, agent_phone=None, logo_path=None, beds=None, baths=None, sqft=None, price=None, qr_image_path=None, output_path=None):


    input_video = str(input_video)
    print(f"Property overlay params: beds={beds}, baths={baths}, sqft={sqft}, logo_path={logo_path}")
    
    if not os.path.exists(input_video):
        print(f"Video not found for property overlays: {input_video}")
        return False

    replace_in_place = output_path is None
    if replace_in_place:
        base, ext = os.path.splitext(input_video)
        output_path = f"{base}_prop{ext}"

    inputs = ['-i', input_video]
    filter_parts = []
    chain_tag = '0:v'
    idx = 1

    if logo_path and os.path.exists(logo_path):
        inputs += ['-i', logo_path]
        filter_parts.append(f'[{idx}:v]scale=400:-1,format=rgba,colorchannelmixer=aa=0.3[logo]')
        filter_parts.append(f'[{chain_tag}][logo]overlay=(W-w)/2:(H-h)/2[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1

    bed_icon_path = 'static/bed.PNG'
    bath_icon_path = 'static/bath.PNG'

    if beds and os.path.exists(bed_icon_path):
        print(f"Adding bed icon: {bed_icon_path}")
        inputs += ['-i', bed_icon_path]
        filter_parts.append(f'[{idx}:v]scale=70:70[bed]')
        filter_parts.append(f'[{chain_tag}][bed]overlay=W/4+20:H-220[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1

    if baths and os.path.exists(bath_icon_path):
        print(f"Adding bath icon: {bath_icon_path}")
        inputs += ['-i', bath_icon_path]
        filter_parts.append(f'[{idx}:v]scale=65:65[bath]')
        filter_parts.append(f'[{chain_tag}][bath]overlay=W/2+20:H-220[o{idx}]')
        chain_tag = f'o{idx}'
        idx += 1

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
            f"drawtext=text='{safe_agent}':fontfile=Inter:fontsize=48:fontcolor=black:x=50:y=150")
    if agent_phone:
        safe_phone = escape_text(agent_phone)
        text_overlays.append(
            f"drawtext=text='{safe_phone}':fontfile=Inter:fontsize=40:fontcolor=black:x=50:y=200")
    if beds:
        safe_beds = escape_text(beds)
        text_overlays.append(
            f"drawtext=text='{safe_beds}':fontfile=Inter:fontsize=56:fontcolor=black:x=W/4-tw/2:y=H-200")
    if baths:
        safe_baths = escape_text(baths)
        text_overlays.append(
            f"drawtext=text='{safe_baths}':fontfile=Inter:fontsize=56:fontcolor=black:x=W/2-tw/2:y=H-200")
    if sqft:
        safe_sqft = escape_text(f"{sqft} sq.ft.")
        text_overlays.append(
            f"drawtext=text='{safe_sqft}':fontfile=Inter:fontsize=56:fontcolor=black:x=3*W/4-tw/2:y=H-200")

    no_icons_or_qr = len(filter_parts) == 0
    no_text = len(text_overlays) == 0
    if no_icons_or_qr and no_text:
        print('No overlays provided; leaving video unchanged')
        return True

    final_map = None
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
        '-crf', '23',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', output_path
    ]

    print('Running agent/property overlay:')
    print(' '.join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
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
