
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import shutil
import base64, uuid
from datetime import datetime
from guided_editor import GuidedVideoEditor
from video_filters import get_available_presets
import subprocess
from dld_api import fetch_listing_details
from dotenv import load_dotenv 
import requests
import json
import time
import threading
from post_processor import add_combined_overlays, add_agent_property_overlays
from scene_detection import detect_room_transitions_realtime, detect_scene_label, get_room_display_name
from scene_detection import get_room_display_name

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

PROCESSING_RESULTS_FILE = 'processing_results.json'

def load_processing_results():
    if os.path.exists(PROCESSING_RESULTS_FILE):
        try:
            with open(PROCESSING_RESULTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading processing results: {e}")
            return {}
    return {}

def save_processing_results():
    try:
        with open(PROCESSING_RESULTS_FILE, 'w') as f:
            json.dump(app.processing_results, f)
    except Exception as e:
        print(f"Error saving processing results: {e}")

app.processing_results = load_processing_results()

def cleanup_temp_files():
    """Clean up old temporary files to prevent disk space issues"""
    try:
        temp_dir = 'temp'
        if not os.path.exists(temp_dir):
            return
        
        current_time = time.time()
        cleaned_count = 0
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            # Check if file should be cleaned up
            should_clean = False
            
            # Music files
            if filename.startswith('music_') and filename.endswith('.mp3'):
                should_clean = True
            # Video clip files
            elif filename.startswith('simple_clip_') and filename.endswith('.mp4'):
                should_clean = True
            elif filename.startswith('temp_hq_clip_') and filename.endswith('.mp4'):
                should_clean = True
            # Concat files
            elif filename.startswith('temp_concat') and filename.endswith('.txt'):
                should_clean = True
            # Logo files
            elif filename.startswith('agency_logo_') and filename.endswith('.png'):
                should_clean = True
            # QR files
            elif filename.startswith('qr_') and filename.endswith('.png'):
                should_clean = True
            # Processing files
            elif filename.startswith('processing_') and filename.endswith('.mp4'):
                should_clean = True
            elif filename.startswith('filtered_') and filename.endswith('.mp4'):
                should_clean = True
            # Frame files
            elif filename.startswith('temp_frame_') and filename.endswith('.jpg'):
                should_clean = True
            
            # Clean up files older than 2 hours (1 hour for music files)
            file_age = current_time - os.path.getmtime(file_path)
            cleanup_threshold = 3600 if filename.startswith('music_') else 7200  # 1 hour for music, 2 hours for others
            
            if should_clean and file_age > cleanup_threshold:
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    print(f"Cleaned up old temp file: {file_path} (age: {file_age/3600:.1f}h)")
                except OSError as e:
                    print(f"Warning: Could not remove old temp file {file_path}: {e}")
        
        if cleaned_count > 0:
            print(f"Cleaned up {cleaned_count} old temporary files")
            
    except Exception as e:
        print(f"Warning: Error during temp file cleanup: {e}")

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
            result = subprocess.run(remux_cmd, capture_output=True, text=True, timeout=120)  
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

@app.route('/get_filter_presets', methods=['GET'])
def get_filter_presets():
    """Get available video filter presets"""
    try:
        presets = get_available_presets()
        return jsonify({
            'success': True,
            'presets': presets
        })
    except Exception as e:
        print(f"Error getting filter presets: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/start_video_processing', methods=['POST'])
def start_video_processing():
    data = request.json
    video_id = data.get('video_id')
    segments = data.get('segments', [])
    export_mode = data.get('export_mode', 'segments')
    speed_factor = data.get('speed_factor', 3.0)
    quality = data.get('quality', 'standard')
    music_path = data.get('music_path')
    music_volume = data.get('music_volume', 1.0)
    filter_settings = data.get('filter_settings', {'preset': 'none'})
    
    if not segments:
        return jsonify({'error': 'No segments provided'}), 400
    
    print(f"Starting background video processing: video_id={video_id}, mode={export_mode}")
    
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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processing_id = f"proc_{timestamp}"
    
    if not hasattr(app, 'processing_results'):
        app.processing_results = {}
    
    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, f'processing_{timestamp}.mp4')
    
    app.processing_results[processing_id] = {
        'temp_file': temp_filename,
        'video_id': video_id,
        'export_mode': export_mode,
        'speed_factor': speed_factor,
        'quality': quality,
        'segments_count': len(segments),
        'created_at': timestamp,
        'status': 'in_progress'
    }
    save_processing_results()
    
    def process_video():
        try:
            print(f"Background processing thread started for {processing_id}")
            
            editor = GuidedVideoEditor(video_path)
            
            for seg in segments:
                editor.add_segment(
                    seg['start'],
                    seg['end'],
                    seg.get('room')
                )
            
            print(f"Background processing: mode={export_mode}, quality={quality}, speed={speed_factor}x")
            print(f"Filter settings received: {filter_settings}")
            
            if export_mode == 'segments':
                success = editor.create_tour(temp_filename, quality=quality)
            elif export_mode == 'speedup':
                success = editor.create_speedup_tour_simple(temp_filename, speed_factor)
            else:
                success = editor.create_tour(temp_filename, quality=quality)
            
            if not success:
                app.processing_results[processing_id]['status'] = 'failed'
                app.processing_results[processing_id]['error'] = 'Failed to process video segments'
                save_processing_results()
                return
            
            should_apply_filters = (
                filter_settings and (
                    filter_settings.get('preset', 'none') != 'none' or 
                    filter_settings.get('custom', {})  
                )
            )
            
            if should_apply_filters:
                print(f"Applying video filters: {filter_settings}")
                filtered_filename = os.path.join(temp_dir, f'filtered_{timestamp}.mp4')
                
                filter_success = editor.apply_video_filters(temp_filename, filtered_filename, filter_settings)
                if filter_success:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                    os.rename(filtered_filename, temp_filename)
                    print("Video filters applied successfully")
                else:
                    print("Failed to apply video filters - continuing with unfiltered video")
            
            if music_path and os.path.exists(music_path):
                print(f"Adding music overlay: {music_path} (volume: {music_volume})")
                music_success = editor.add_music_overlay(temp_filename, music_path, music_volume)
                if music_success:
                    print("Music overlay added successfully")
                    # Store music path for cleanup later
                    app.processing_results[processing_id]['music_path'] = music_path
                else:
                    print("Failed to add music overlay - continuing without music")
            
            app.processing_results[processing_id]['status'] = 'completed'
            app.processing_results[processing_id]['output_file'] = temp_filename
            print(f"Background processing completed for {processing_id}")
            save_processing_results()
            
        except Exception as e:
            print(f"Background processing error for {processing_id}: {e}")
            app.processing_results[processing_id]['status'] = 'failed'
            app.processing_results[processing_id]['error'] = str(e)
            save_processing_results()
    
    thread = threading.Thread(target=process_video)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'processing_id': processing_id,
        'message': 'Video processing started in background',
        'export_mode': export_mode,
        'segments_count': len(segments)
    })

@app.route('/check_processing_status/<processing_id>', methods=['GET'])
def check_processing_status(processing_id):
    if not hasattr(app, 'processing_results') or processing_id not in app.processing_results:
        return jsonify({'status': 'not_found', 'message': 'Processing ID not found'}), 404
    
    processing_result = app.processing_results[processing_id]
    status = processing_result.get('status', 'in_progress')
    
    if status == 'completed':
        return jsonify({
            'status': 'completed',
            'message': 'Video processing completed',
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count'],
            'created_at': processing_result['created_at']
        })
    elif status == 'failed':
        return jsonify({
            'status': 'failed',
            'message': 'Video processing failed',
            'error': processing_result.get('error', 'Unknown error'),
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count']
        })
    else:
        return jsonify({
            'status': 'in_progress',
            'message': 'Video still processing',
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count']
        })

@app.route('/create_tour', methods=['POST'])
def create_tour():
    data = request.json
    processing_id = data.get('processing_id')
    qr_path = data.get('qr_path')
    agent_name = data.get('agent_name')
    agent_phone = data.get('agent_phone')
    agency_logo_data = data.get('agency_logo_data')
    property_price = data.get('property_price')
    beds = data.get('beds')
    baths = data.get('baths')
    sqft = data.get('sqft')
    
    if not processing_id:
        return jsonify({'error': 'Processing ID required'}), 400
    
    if not hasattr(app, 'processing_results') or processing_id not in app.processing_results:
        return jsonify({'error': 'Processing ID not found or expired'}), 404
    
    processing_result = app.processing_results[processing_id]
    temp_file = processing_result['temp_file']
    
    if not os.path.exists(temp_file):
        return jsonify({'error': 'Processed video file not found'}), 404
    
    print(f"Adding overlays to processed video: {temp_file}")
    print(f"Agent info: {agent_name} | {agent_phone}")
    
    try:
        archive_dir = 'archive'
        os.makedirs(archive_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = os.path.join(archive_dir, f'guided_tour_{timestamp}.mp4')
        
        shutil.copy2(temp_file, output_filename)
        
        logo_path = None
        if agency_logo_data:
            os.makedirs('temp', exist_ok=True)
            logo_path = os.path.join('temp', f"agency_logo_{uuid.uuid4().hex}.png")
            with open(logo_path, 'wb') as lf:
                lf.write(base64.b64decode(agency_logo_data.split(',')[-1]))

        print("Adding agent/property overlays…")
        overlay_success = add_agent_property_overlays(
            output_filename,
            agent_name=agent_name,
            agent_phone=agent_phone,
            logo_path=logo_path,
            beds=beds,
            baths=baths,
            sqft=sqft,
            qr_image_path=qr_path
        )
        
        if not overlay_success:
            print("Failed to add overlays - using video without overlays")
        
        # Clean up all temporary files
        temp_files_to_clean = []
        
        # Add main temp file
        if os.path.exists(temp_file):
            temp_files_to_clean.append(temp_file)
        
        # Add QR file
        if qr_path and os.path.exists(qr_path):
            temp_files_to_clean.append(qr_path)
        
        # Add logo file
        if logo_path and os.path.exists(logo_path):
            temp_files_to_clean.append(logo_path)
        
        # Add music file if it was used in processing
        if processing_result.get('music_path') and os.path.exists(processing_result['music_path']):
            temp_files_to_clean.append(processing_result['music_path'])
        
        # Clean up all temp files
        for temp_file_path in temp_files_to_clean:
            try:
                os.remove(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as e:
                print(f"Warning: Could not remove temporary file {temp_file_path}: {e}")
        
        # Also clean up ALL music files in temp directory after delivery
        try:
            temp_dir = 'temp'
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    if filename.startswith('music_') and filename.endswith('.mp3'):
                        music_file_path = os.path.join(temp_dir, filename)
                        try:
                            os.remove(music_file_path)
                            print(f"Cleaned up music file after delivery: {music_file_path}")
                        except OSError as e:
                            print(f"Warning: Could not remove music file {music_file_path}: {e}")
        except Exception as e:
            print(f"Warning: Error during music cleanup: {e}")
        
        app.processing_results[processing_id]['output_file'] = output_filename
        save_processing_results()
        
        mode_description = f"{processing_result['export_mode']}"
        if processing_result['export_mode'] == 'speedup':
            mode_description += f" ({processing_result['speed_factor']}x speed)"
        
        mode_description += f" + Agent branding"
        if qr_path:
            mode_description += f" + QR Code"
        
        return jsonify({
            'success': True,
            'output_file': output_filename,
            'message': 'Tour created with agent branding!',
            'export_mode': processing_result['export_mode'],
            'speed_factor': processing_result.get('speed_factor'),
            'quality': processing_result.get('quality'),
            'segments_count': processing_result.get('segments_count'),
            'description': mode_description
        })
        
    except Exception as e:
        print(f"Overlay processing error: {e}")
        return jsonify({'error': f'Failed to add overlays: {str(e)}'}), 500

@app.route('/get_tour_result/<processing_id>')
def get_tour_result(processing_id):
    print(f"Getting tour result for processing ID: {processing_id}")
    print(f"Processing results keys: {list(app.processing_results.keys()) if hasattr(app, 'processing_results') else 'No processing_results'}")
    
    if not hasattr(app, 'processing_results') or processing_id not in app.processing_results:
        print(f"Processing ID {processing_id} not found in processing_results")
        return jsonify({'error': 'Tour result not found'}), 404
    
    processing_result = app.processing_results[processing_id]
    print(f"Found processing result: {processing_result}")
    
    output_file = processing_result.get('output_file') or processing_result.get('temp_file')
    
    if output_file and os.path.exists(output_file):
        print(f"Output file found: {output_file}")
        return jsonify({
            'success': True,
            'output_file': output_file,
            'message': 'Tour created successfully!',
            'export_mode': processing_result['export_mode'],
            'speed_factor': processing_result.get('speed_factor'),
            'quality': processing_result.get('quality'),
            'segments_count': processing_result.get('segments_count')
        })
    else:
        print(f"No valid output file found in processing result")
        print(f"Status: {processing_result.get('status')}")
        print(f"Output file path: {output_file}")
        print(f"File exists: {os.path.exists(output_file) if output_file else 'No file path'}")
        return jsonify({'error': 'Tour not yet created'}), 404

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
@app.route('/delivery/<processing_id>')
def delivery_page(processing_id=None):
    return send_file('templates/delivery.html', mimetype='text/html')

@app.route('/export')
def export_page():
    return send_file('templates/export.html', mimetype='text/html')

@app.route('/<path:filename>')
def serve_static(filename):
    return safe_send_file(filename)

@app.route('/ai_segment_detect', methods=['POST'])
def ai_segment_detect():

    data = request.json
    video_id = data.get('video_id')
    detection_interval = data.get('detection_interval', 2.0)   
    
    if video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"AI segment detection for video: {video_path}")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent video for AI segment detection: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    try:
        
        print(f"Starting AI segment detection with interval: {detection_interval}s")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detection_id = f"detect_{timestamp}"
        
        if not hasattr(app, 'detection_sessions'):
            app.detection_sessions = {}
        
        for existing_id, existing_session in list(app.detection_sessions.items()):
            if existing_session.get('status') == 'in_progress' and existing_session.get('video_path') == video_path:
                print(f"Cancelling existing detection session: {existing_id}")
                existing_session['status'] = 'cancelled'
                existing_session['stop_flag'] = True
        
        app.detection_sessions[detection_id] = {
            'video_path': video_path,
            'status': 'in_progress',
            'segments': [],
            'created_at': timestamp,
            'stop_flag': False
        }
        
        def detection_callback(update):
            if detection_id in app.detection_sessions:
                session = app.detection_sessions[detection_id]
                
                if session.get('stop_flag', False):
                    print(f"Detection {detection_id} stopped by flag")
                    return False  
                
                if update['type'] == 'segment_complete':
                    session['segments'] = [s for s in session['segments'] if not (s.get('temporary') and s.get('room') == update['segment']['room'])]
                    session['segments'].append(update['segment'])
                    print(f"Segment detected: {update['segment']['room']} ({update['segment']['start']:.1f}s - {update['segment']['end']:.1f}s)")
                elif update['type'] == 'room_entry':
                    temp_segment = {
                        'start': update['time'],
                        'end': update['time'] + 2.0, 
                        'room': update['room'],
                        'display_name': get_room_display_name(update['room']),
                        'temporary': True  
                    }
                    session['segments'] = [s for s in session['segments'] if not (s.get('temporary') and s.get('room') == update['room'])]
                    session['segments'].append(temp_segment)
                    print(f"Room entry detected: {update['room']} at {update['time']:.1f}s")
                elif update['type'] == 'progress':
                    session['progress'] = update['progress']
            else:
                print(f"Warning: Detection session {detection_id} not found")
                return False   
        
        def run_detection():
            try:
                segments = detect_room_transitions_realtime(video_path, detection_callback, detection_interval)
                
                if detection_id in app.detection_sessions:
                    app.detection_sessions[detection_id]['status'] = 'completed'
                    app.detection_sessions[detection_id]['segments'] = segments
                    print(f"AI detection completed for {detection_id}")
                
            except Exception as e:
                print(f"AI detection error for {detection_id}: {e}")
                if detection_id in app.detection_sessions:
                    app.detection_sessions[detection_id]['status'] = 'failed'
                    app.detection_sessions[detection_id]['error'] = str(e)
        
        thread = threading.Thread(target=run_detection)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'detection_id': detection_id,
            'message': 'AI segment detection started'
        })
        
    except Exception as e:
        print(f"AI segment detection failed: {e}")
        return jsonify({'error': f'AI segment detection failed: {str(e)}'}), 500

@app.route('/check_detection_status/<detection_id>', methods=['GET'])
def check_detection_status(detection_id):
    if not hasattr(app, 'detection_sessions') or detection_id not in app.detection_sessions:
        return jsonify({'status': 'not_found', 'message': 'Detection ID not found'}), 404
    
    session = app.detection_sessions[detection_id]
    status = session.get('status', 'in_progress')
    segments = session.get('segments', [])
    
    if status == 'completed':
        return jsonify({
            'status': 'completed',
            'segments': segments,
            'segments_count': len(segments)
        })
    elif status == 'failed':
        return jsonify({
            'status': 'failed',
            'error': session.get('error', 'Unknown error')
        })
    else:
        return jsonify({
            'status': 'in_progress',
            'progress': session.get('progress', 0),
            'segments': segments,
            'segments_count': len(segments)
        })

@app.route('/auto_detect_room_label', methods=['POST'])
def auto_detect_room_label():

    data = request.json
    video_id = data.get('video_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([video_id, start_time is not None, end_time is not None]):
        return jsonify({'error': 'Missing required parameters: video_id, start_time, end_time'}), 400
    
    if video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"Auto-detecting room label for segment: {start_time}s - {end_time}s")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent video for auto-detection: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    try:
        
        print(f"Auto-detecting room label for segment {start_time}s - {end_time}s")
        room_label = detect_scene_label(video_path, start_time, end_time)
        
        if room_label:
            display_name = get_room_display_name(room_label)
            
            return jsonify({
                'success': True,
                'room_label': room_label,
                'display_name': display_name,
                'message': f'Auto-detected room: {display_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not detect room label for this segment'
            }), 400
        
    except Exception as e:
        print(f"Auto-detection failed: {e}")
        return jsonify({'error': f'Auto-detection failed: {str(e)}'}), 500

@app.route('/stop_ai_detection', methods=['POST'])
def stop_ai_detection():
    """Stop any ongoing AI detection sessions"""
    try:
        if hasattr(app, 'detection_sessions'):
            stopped_count = 0
            for detection_id, session in app.detection_sessions.items():
                if session.get('status') == 'in_progress':
                    print(f"Stopping AI detection session: {detection_id}")
                    session['status'] = 'stopped'
                    session['stop_flag'] = True
                    stopped_count += 1
            
            return jsonify({
                'success': True,
                'message': f'Stopped {stopped_count} active detection sessions'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No active detection sessions found'
            })
    except Exception as e:
        print(f"Error stopping AI detection: {e}")
        return jsonify({'error': f'Failed to stop detection: {str(e)}'}), 500

@app.route('/cleanup_temp_files', methods=['POST'])
def cleanup_temp_files_endpoint():
    """Manually trigger cleanup of temporary files"""
    try:
        cleanup_temp_files()
        return jsonify({
            'success': True,
            'message': 'Temporary files cleanup completed'
        })
    except Exception as e:
        print(f"Error during manual cleanup: {e}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.route('/force_cleanup_temp_files', methods=['POST'])
def force_cleanup_temp_files_endpoint():
    """Force cleanup of ALL temporary files regardless of age"""
    try:
        temp_dir = 'temp'
        if not os.path.exists(temp_dir):
            return jsonify({
                'success': True,
                'message': 'No temp directory found'
            })
        
        cleaned_count = 0
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            # Check if file should be cleaned up
            should_clean = False
            
            # Music files
            if filename.startswith('music_') and filename.endswith('.mp3'):
                should_clean = True
            # Video clip files
            elif filename.startswith('simple_clip_') and filename.endswith('.mp4'):
                should_clean = True
            elif filename.startswith('temp_hq_clip_') and filename.endswith('.mp4'):
                should_clean = True
            # Concat files
            elif filename.startswith('temp_concat') and filename.endswith('.txt'):
                should_clean = True
            # Logo files
            elif filename.startswith('agency_logo_') and filename.endswith('.png'):
                should_clean = True
            # QR files
            elif filename.startswith('qr_') and filename.endswith('.png'):
                should_clean = True
            # Processing files
            elif filename.startswith('processing_') and filename.endswith('.mp4'):
                should_clean = True
            elif filename.startswith('filtered_') and filename.endswith('.mp4'):
                should_clean = True
            # Frame files
            elif filename.startswith('temp_frame_') and filename.endswith('.jpg'):
                should_clean = True
            
            if should_clean:
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    print(f"Force cleaned up temp file: {file_path}")
                except OSError as e:
                    print(f"Warning: Could not remove temp file {file_path}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Force cleanup completed. Removed {cleaned_count} files.'
        })
        
    except Exception as e:
        print(f"Error during force cleanup: {e}")
        return jsonify({'error': f'Force cleanup failed: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)  