
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
from datetime import datetime
from guided_editor import GuidedVideoEditor
import subprocess
from dld_api import fetch_listing_details
from dotenv import load_dotenv 
import requests
import json
import time

load_dotenv() 

app = Flask(__name__)
CORS(app)  

import json

def load_uploaded_videos():
    try:
        with open('uploaded_videos.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_uploaded_videos():
    with open('uploaded_videos.json', 'w') as f:
        json.dump(uploaded_videos, f)

uploaded_videos = load_uploaded_videos()

def safe_send_file(filename):
    if not os.path.isfile(filename):
        return "File not found", 404
    try:
        return send_file(
            filename,
            mimetype={
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.mp4': 'video/mp4'
            }.get(os.path.splitext(filename)[1].lower(), 'application/octet-stream')
        )
    except Exception as e:
        print(f"Error serving file {filename}: {e}")
        return "Error serving file", 500

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    
    video = request.files['video']
    
    upload_dir = 'uploads'
    os.makedirs(upload_dir, exist_ok=True)
    
    original_video_path = os.path.join(upload_dir, video.filename)
    video.save(original_video_path)
    video_path = original_video_path
    video_id = video.filename

    if video_id.lower().endswith('.mov'):
        print(f"Detected .MOV file. Attempting to remux to MP4 for compatibility...")
        new_video_path = os.path.splitext(original_video_path)[0] + '.mp4'
        
        remux_cmd = [
            'ffmpeg', '-i', original_video_path,
            '-c', 'copy',           
            '-movflags', '+faststart',
            '-y', new_video_path
        ]
        
        try:
            result = subprocess.run(remux_cmd, capture_output=True, text=True, timeout=120) # Increased timeout
            if result.returncode == 0:
                print(f"Successfully remuxed to {new_video_path}")
                video_path = new_video_path  
                video_id = os.path.basename(new_video_path) 
                
                try:
                    os.remove(original_video_path)
                    print(f"Removed original .MOV file: {original_video_path}")
                except OSError as e:
                    print(f"Could not remove original .MOV file: {e}")
            else:
                print(f"FFmpeg remux failed. Using original file. Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"Remux command timed out. Using original file.")
        except Exception as e:
            print(f"An error occurred during remux. Using original file. Error: {e}")

    editor = GuidedVideoEditor(video_path)
    if not editor.video_info:
        return jsonify({'error': 'Invalid video'}), 400
    
    uploaded_videos[video_id] = video_path
    save_uploaded_videos() 
    
    print(f"Video uploaded: {video.filename} → {video_path}")
    print(f"Stored videos: {list(uploaded_videos.keys())}")
    
    return jsonify({
        'duration': editor.video_info['duration'],
        'width': editor.video_info['width'],
        'height': editor.video_info['height'],
        'video_id': video_id, 
        'video_path': video_path
    })

@app.route('/verify_listing', methods=['POST'])
def verify_listing():

    data = request.json or {}
    trade_license = data.get('trade_license_number')
    listing_number = data.get('listing_number')
    # auth_token = data.get('auth_token')
    # username = data.get('username')
    # password = data.get('password')


    auth_token = os.getenv('DLD_BEARER_TOKEN')
    username = os.getenv('DLD_USERNAME')
    password = os.getenv('DLD_PASSWORD')

    if not trade_license or not listing_number or (not auth_token and not (username and password)):
        return jsonify({'error': 'Missing credentials. Supply auth_token OR username/password via request or .env'}), 400

    try:
        listing_data, qr_path = fetch_listing_details(
            trade_license,
            listing_number,
            auth_token=auth_token,
            username=username,
            password=password,
        )
        return jsonify({
            'success': True,
            'listing': listing_data.get('data', {}).get('result', [{}])[0],
            'qr_path': qr_path
        })
    except Exception as exc:
        print(f"DLD verification failed: {exc}")
        return jsonify({'success': False, 'error': str(exc)}), 400

@app.route('/search_music', methods=['POST'])
def search_music():
    data = request.json or {}
    query = data.get('query', 'background music')
    page_size = min(data.get('page_size', 15), 150)  
    
    api_key = os.getenv('FREESOUND_API_KEY')
    if not api_key:
        return jsonify({'error': 'Freesound API key not configured'}), 500
    
    try:
        params = {
            'query': query,
            'token': api_key,
            'page_size': page_size,
            'filter': 'duration:[30.0 TO 300.0] AND tag:music', 
            'fields': 'id,name,description,tags,duration,previews,username,license',
            'sort': 'score' 
        }
        
        response = requests.get('https://freesound.org/apiv2/search/text/', params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"Freesound API error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Music search failed'}), 400
        
        search_results = response.json()
        
        music_tracks = []
        for result in search_results.get('results', []):
            track = {
                'id': result['id'],
                'name': result['name'],
                'description': result.get('description', ''),
                'tags': result.get('tags', []),
                'duration': result.get('duration', 0),
                'username': result.get('username', 'Unknown'),
                'license': result.get('license', 'Unknown'),
                'preview_mp3': result.get('previews', {}).get('preview-hq-mp3', ''),
                'preview_ogg': result.get('previews', {}).get('preview-hq-ogg', ''),
            }
            music_tracks.append(track)
        
        return jsonify({
            'success': True,
            'count': search_results.get('count', 0),
            'results': music_tracks
        })
        
    except requests.exceptions.RequestException as e:
        print(f"Freesound API request failed: {e}")
        return jsonify({'error': 'Music search service unavailable'}), 503
    except Exception as e:
        print(f"Music search error: {e}")
        return jsonify({'error': 'Music search failed'}), 500

@app.route('/download_music', methods=['POST'])
def download_music():
    data = request.json
    preview_url = data.get('preview_url')
    
    if not preview_url:
        return jsonify({'error': 'No preview URL provided'}), 400
    
    try:
        # Create music path
        music_filename = f"music_{int(time.time())}.mp3"
        music_path = os.path.join('temp', music_filename)
        os.makedirs('temp', exist_ok=True)
        
        print(f"Downloading music: {preview_url}")
        response = requests.get(preview_url, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to download music file'}), 400
        
        with open(music_path, 'wb') as f:
            f.write(response.content)
        
        if not os.path.exists(music_path) or os.path.getsize(music_path) < 1000:
            return jsonify({'error': 'Downloaded music file is invalid'}), 400
        
        print(f"Music downloaded: {music_path} ({os.path.getsize(music_path)} bytes)")
        
        return jsonify({
            'success': True,
            'music_path': music_path,
            'cached': False
        })
        
    except requests.exceptions.RequestException as e:
        print(f"Music download failed: {e}")
        return jsonify({'error': 'Music download failed'}), 503
    except Exception as e:
        print(f"Music download error: {e}")
        return jsonify({'error': 'Music download failed'}), 500

@app.route('/detect_segment_label', methods=['POST'])
def detect_segment_label():

    data = request.json
    video_id = data.get('video_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([video_id is not None, start_time is not None, end_time is not None]):
        return jsonify({'error': 'Missing required parameters: video_id, start_time, end_time'}), 400
    
    try:
        start_time = float(start_time)
        end_time = float(end_time)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid time values - must be numbers'}), 400
    
    if start_time >= end_time:
        return jsonify({'error': 'End time must be after start time'}), 400
    
    if video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"Detecting label for segment: {start_time:.1f}s-{end_time:.1f}s in {video_path}")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent video for detection: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    try:
        from scene_detection import detect_scene_label
        
        print(f"Starting real-time label detection for {start_time:.1f}s-{end_time:.1f}s...")
        detected_label = detect_scene_label(video_path, start_time, end_time)
        
        if detected_label:
            print(f"Label detected: '{detected_label}' for segment {start_time:.1f}s-{end_time:.1f}s")
            
            label_mapping = {
                'kitchen': 'Kitchen',
                'bedroom': 'Bedroom', 
                'bathroom': 'Bathroom',
                'living_room': 'Living Room',
                'closet': 'Closet',
                'exterior': 'Exterior',
                'office': 'Office',
                'common_area': 'Common Area',
                'dining_room': 'Dining Room',
                'balcony': 'Balcony',
                'unlabeled': 'Unlabeled'
            }
            
            display_name = label_mapping.get(detected_label, detected_label.replace('_', ' ').title())
            
            return jsonify({
                'success': True,
                'detected_label': detected_label,
                'display_name': display_name,
                'confidence': 'high',  
                'processing_time': f"{end_time - start_time:.1f}s segment processed"
            })
        else:
            print(f"❌ No label detected for segment {start_time:.1f}s-{end_time:.1f}s")
            return jsonify({
                'success': True,
                'detected_label': 'unlabeled',
                'display_name': 'Unlabeled',
                'confidence': 'low',
                'processing_time': f"{end_time - start_time:.1f}s segment processed"
            })
            
    except Exception as e:
        print(f"❌ Label detection failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Label detection failed: {str(e)}',
            'fallback_label': 'unlabeled',
            'fallback_display': 'Unlabeled'
        }), 500

@app.route('/create_tour', methods=['POST'])
def create_tour():
    data = request.json
    video_id = data.get('video_id')
    segments = data.get('segments', [])
    export_mode = data.get('export_mode', 'segments')
    speed_factor = data.get('speed_factor', 3.0)
    quality = data.get('quality', 'standard')
    qr_path = data.get('qr_path')  
    music_path = data.get('music_path')  
    music_volume = data.get('music_volume', 1.0)  
    agent_name = data.get('agent_name') 
    agency_name = data.get('agency_name') 
    
    if not segments:
        return jsonify({'error': 'No segments provided'}), 400
    
    print(f"video_id={video_id}, available_videos={list(uploaded_videos.keys())}")
    
    if video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"Using uploaded video: {video_path}")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent uploaded video: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    editor = GuidedVideoEditor(video_path)
    
    for seg in segments:
        editor.add_segment(
            seg['start'],
            seg['end'],
            seg.get('room')  
        )
    
    archive_dir = 'archive'
    os.makedirs(archive_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(archive_dir, f'guided_tour_{timestamp}.mp4')
    
    print(f"Creating tour: mode={export_mode}, quality={quality}, speed={speed_factor}x, segments={len(segments)}")
    print(f"Output will be saved to: {output_filename}")
    if agent_name and agency_name:
        print(f"Agent branding: {agent_name} @ {agency_name}")
    
    if export_mode == 'segments':
        success = editor.create_tour_simple(output_filename)
        mode_description = f"Segments only (fast processing)"

    elif export_mode == 'speedup':
        print(f"SPEEDUP MODE: Creating {quality} quality tour with {speed_factor}x speed")
        success = editor.create_speedup_tour_simple(output_filename, speed_factor)
        mode_description = f"Speedup {speed_factor}x ({quality} quality)"
        print(f"SPEEDUP RESULT: success={success}")

    # elif export_mode == 'trim':
    #     success = editor.create_tour_simple(output_filename)
    #     mode_description = f"Trimmed & enhanced (fast processing)"
    else:
        print(f"Unknown export mode: {export_mode}, using default")
        success = editor.create_tour(output_filename, quality=quality)
        mode_description = f"Default processing ({quality} quality)"
    
    if success and music_path and os.path.exists(music_path):
        print(f"Adding music overlay: {music_path} (volume: {music_volume})")
        music_success = editor.add_music_overlay(output_filename, music_path, music_volume)
        if music_success:
            print("Music overlay added successfully")
            mode_description += f" + Music"
        else:
            print("Failed to add music overlay - continuing without music")
    elif music_path:
        print(f"Music file not found: {music_path}")
    
    if success and (agent_name and agency_name):
        print(f"Adding combined overlays: '{agent_name}' @ '{agency_name}'")
        print(f"Video file exists: {os.path.exists(output_filename)}")
        print(f"Video file size: {os.path.getsize(output_filename) if os.path.exists(output_filename) else 'N/A'}")
        
        if qr_path and os.path.exists(qr_path):
            print(f"QR file exists: {os.path.exists(qr_path)}")
            print(f"QR file size: {os.path.getsize(qr_path) if os.path.exists(qr_path) else 'N/A'}")
            
            combined_success = editor.add_combined_overlays(
                output_filename, 
                agent_name, 
                agency_name, 
                qr_image_path=qr_path, 
                qr_position='top_right'
            )
            
            if combined_success:
                print("Combined overlays (agent + QR) added successfully")
                mode_description += f" + Agent branding + QR Code"
            else:
                print("Failed to add combined overlays - continuing without overlays")
        else:
            watermark_success = editor.add_combined_overlays(
                output_filename, 
                agent_name, 
                agency_name
            )
            
            if watermark_success:
                print("Agent watermark added successfully")
                mode_description += f" + Agent branding"
            else:
                print("Failed to add agent watermark - continuing without watermark")
    else:
        print(f"Overlays skipped - success: {success}, agent_name: '{agent_name}', agency_name: '{agency_name}'")
    
    if success:
        files_to_cleanup = []
        
        if music_path and os.path.exists(music_path):
            files_to_cleanup.append(music_path)
        
        if qr_path and os.path.exists(qr_path):
            files_to_cleanup.append(qr_path)
        
        for file_path in files_to_cleanup:
            try:
                os.remove(file_path)
                print(f"Cleaned up temporary file: {file_path}")
            except OSError as e:
                print(f"Warning: Could not remove temporary file {file_path}: {e}")
    
    if success:
        return jsonify({
            'success': True,
            'output_file': output_filename,
            'message': f'Tour created!',
            'export_mode': export_mode,
            'speed_factor': speed_factor,
            'quality': quality
        })
    else:
        return jsonify({'error': 'Failed to create tour'}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    if filename.startswith('archive/'):
        file_path = filename
    else:
        archive_path = os.path.join('archive', filename)
        if os.path.exists(archive_path):
            file_path = archive_path
        else:
            file_path = filename
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/')
def index():
    return send_file('templates/upload.html', mimetype='text/html')

@app.route('/edit')
def edit_page():
    return send_file('templates/edit.html', mimetype='text/html')

@app.route('/delivery')
def delivery_page():
    return send_file('templates/delivery.html', mimetype='text/html')

@app.route('/export')
def export_page():
    return send_file('templates/export.html', mimetype='text/html')

@app.route('/<path:filename>')
def serve_static(filename):
    return safe_send_file(filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)  