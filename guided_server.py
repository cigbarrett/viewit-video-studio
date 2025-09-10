
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

load_dotenv() 



app = Flask(__name__)
CORS(app)  

import json


def load_projects():
    try:
        with open('projects.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_projects():
    try:
        with open('projects.json', 'w') as f:
            json.dump(app.projects, f)
    except Exception as e:
        print(f"Error saving projects: {e}")


def load_uploaded_videos():
    try:
        with open('uploaded_videos.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_uploaded_videos():
    
    save_projects()


app.projects = load_projects()
if not hasattr(app, 'projects'):
    app.projects = {}


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
    
    save_projects()


legacy_processing_results = load_processing_results()
for proc_id, proc_data in legacy_processing_results.items():
    if proc_id not in app.projects:
        project_id = proc_data.get('video_id', proc_id)
        video_path = proc_data.get('video_path', uploaded_videos.get(project_id, ''))
        app.projects[proc_id] = {
            'project_id': proc_id,
            'video_id': project_id,
            'video_path': video_path,
            'processing_results': {proc_id: proc_data},
            'detection_sessions': {},
            'created_at': proc_data.get('created_at', datetime.now().strftime("%Y%m%d_%H%M%S")),
            'status': 'active'
        }


app.processing_results = {}
app.detection_sessions = {}

def _cleanup_temp_files(force=False, age_threshold=None):

    result = {
        'cleaned_count': 0,
        'errors': []
    }
    
    try:
        temp_dir = 'temp'
        if not os.path.exists(temp_dir):
            return result
        
        current_time = time.time()
        
        temp_file_patterns = [
            {'prefix': 'music_', 'suffix': '.mp3', 'default_threshold': 3600},
            {'prefix': 'simple_clip_', 'suffix': '.mp4', 'default_threshold': 7200},
            {'prefix': 'temp_hq_clip_', 'suffix': '.mp4', 'default_threshold': 7200},
            {'prefix': 'temp_concat', 'suffix': '.txt', 'default_threshold': 7200},
            {'prefix': 'agency_logo_', 'suffix': '.png', 'default_threshold': 7200},
            {'prefix': 'qr_', 'suffix': '.png', 'default_threshold': 7200},
            {'prefix': 'processing_', 'suffix': '.mp4', 'default_threshold': 7200},
            {'prefix': 'filtered_', 'suffix': '.mp4', 'default_threshold': 7200},
            {'prefix': 'temp_frame_', 'suffix': '.jpg', 'default_threshold': 7200},
        ]
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            should_clean = False
            cleanup_threshold = 7200  
            
            for pattern in temp_file_patterns:
                if filename.startswith(pattern['prefix']) and filename.endswith(pattern['suffix']):
                    should_clean = True
                    cleanup_threshold = pattern['default_threshold']
                    break
            
            if not should_clean:
                continue
                
            if age_threshold is not None:
                cleanup_threshold = age_threshold
                
            file_age = current_time - os.path.getmtime(file_path)
            if force or file_age > cleanup_threshold:
                try:
                    os.remove(file_path)
                    result['cleaned_count'] += 1
                    age_str = f" (age: {file_age/3600:.1f}h)" if not force else ""
                    print(f"Cleaned up temp file: {file_path}{age_str}")
                except OSError as e:
                    error_msg = f"Could not remove temp file {file_path}: {e}"
                    result['errors'].append(error_msg)
                    print(f"Warning: {error_msg}")
        
        if result['cleaned_count'] > 0:
            print(f"Cleaned up {result['cleaned_count']} temporary files")
            
    except Exception as e:
        error_msg = f"Error during temp file cleanup: {e}"
        result['errors'].append(error_msg)
        print(f"Warning: {error_msg}")
        
    return result

def cleanup_temp_files():
    _cleanup_temp_files(force=False)

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
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_id = f"proj_{timestamp}_{uuid.uuid4().hex[:8]}"
    
    
    upload_dir = os.path.join('uploads', project_id)
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
    
    app.projects[project_id] = {
        'project_id': project_id,
        'video_id': video_id,
        'video_path': video_path,
        'processing_results': {},
        'detection_sessions': {},
        'created_at': timestamp,
        'status': 'active',
        'video_info': editor.video_info
    }
    
    
    uploaded_videos[video_id] = video_path
    save_projects()
    
    print(f"Video uploaded to project {project_id}: {video.filename} → {video_path}")
    print(f"Active projects: {len(app.projects)}")
    
    processing_id = f"proc_{project_id}_{timestamp}"
    
    app.projects[project_id]['processing_results'][processing_id] = {
        'video_id': video_id,
        'video_path': video_path,
        'created_at': timestamp,
        'status': 'uploaded',
        'project_id': project_id
    }
    save_projects()
    
    response_data = {
        'duration': editor.video_info['duration'],
        'width': editor.video_info['width'],
        'height': editor.video_info['height'],
        'video_id': video_id, 
        'video_path': video_path,
        'processing_id': processing_id,
        'project_id': project_id,
        'edit_url': f'/edit/{processing_id}'  
    }
    
    return jsonify(response_data)

@app.route('/verify_listing', methods=['POST'])
def verify_listing():

    data = request.json or {}
    trade_license = data.get('trade_license_number')
    listing_number = data.get('listing_number')
    
    
    


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
    existing_processing_id = data.get('processing_id') 
    project_id = data.get('project_id')
    
    if not segments:
        return jsonify({'error': 'No segments provided'}), 400
    
    print(f"Starting background video processing: project_id={project_id}, video_id={video_id}, mode={export_mode}")
    
    
    video_path = None
    if project_id and project_id in app.projects:
        video_path = app.projects[project_id]['video_path']
        print(f"Using project video: {video_path}")
    elif video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"Using legacy uploaded video: {video_path}")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent uploaded video: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processing_id = existing_processing_id or f"proc_{project_id or 'legacy'}_{timestamp}_{uuid.uuid4().hex[:6]}"
    
    
    temp_dir = os.path.join('temp', project_id or 'legacy')
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, f'processing_{timestamp}.mp4')
    print(f"Created project-specific temp directory: {temp_dir}")
    
    
    processing_result = {
        'temp_file': temp_filename,
        'video_id': video_id,
        'project_id': project_id,
        'export_mode': export_mode,
        'speed_factor': speed_factor,
        'quality': quality,
        'segments_count': len(segments),
        'created_at': timestamp,
        'status': 'in_progress'
    }
    
    if project_id and project_id in app.projects:
        app.projects[project_id]['processing_results'][processing_id] = processing_result
    else:
        
        if not hasattr(app, 'processing_results'):
            app.processing_results = {}
        app.processing_results[processing_id] = processing_result
    
    save_projects()
    
    def process_video():
        try:
            print(f"Background processing thread started for {processing_id}")
            
            
            def should_stop():
                if project_id and project_id in app.projects:
                    proc_result = app.projects[project_id]['processing_results'].get(processing_id, {})
                    return proc_result.get('stop_flag', False) or proc_result.get('status') == 'cancelled'
                else:
                    proc_result = app.processing_results.get(processing_id, {})
                    return proc_result.get('stop_flag', False) or proc_result.get('status') == 'cancelled'
            
            
            if should_stop():
                print(f"Processing {processing_id} was stopped before starting")
                return
            
            editor = GuidedVideoEditor(video_path, temp_dir)
            
            for seg in segments:
                
                if should_stop():
                    print(f"Processing {processing_id} stopped during segment addition")
                    return
                    
                editor.add_segment(
                    seg['start'],
                    seg['end'],
                    seg.get('room')
                )
            
            
            if should_stop():
                print(f"Processing {processing_id} stopped before main processing")
                return
            
            print(f"Background processing: mode={export_mode}, quality={quality}, speed={speed_factor}x")
            print(f"Filter settings received: {filter_settings}")
            
            
            if should_stop():
                print(f"Processing {processing_id} stopped before video creation")
                return
            
            if export_mode == 'segments':
                success = editor.create_tour(temp_filename, quality=quality)
            elif export_mode == 'speedup':
                success = editor.create_speedup_tour_simple(temp_filename, speed_factor)
            else:
                success = editor.create_tour(temp_filename, quality=quality)
            
            
            if should_stop():
                print(f"Processing {processing_id} stopped after video creation")
                
                if os.path.exists(temp_filename):
                    try:
                        os.remove(temp_filename)
                        print(f"Cleaned up partial output file: {temp_filename}")
                    except Exception as e:
                        print(f"Error cleaning up partial file: {e}")
                return
            
            if not success:
                
                if project_id and project_id in app.projects:
                    app.projects[project_id]['processing_results'][processing_id]['status'] = 'failed'
                    app.projects[project_id]['processing_results'][processing_id]['error'] = 'Failed to process video segments'
                else:
                    app.processing_results[processing_id]['status'] = 'failed'
                    app.processing_results[processing_id]['error'] = 'Failed to process video segments'
                save_projects()
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
                    
                    if project_id and project_id in app.projects:
                        app.projects[project_id]['processing_results'][processing_id]['music_path'] = music_path
                    else:
                        app.processing_results[processing_id]['music_path'] = music_path
                else:
                    print("Failed to add music overlay - continuing without music")
            
            
            if project_id and project_id in app.projects:
                app.projects[project_id]['processing_results'][processing_id]['status'] = 'completed'
                app.projects[project_id]['processing_results'][processing_id]['output_file'] = temp_filename
            else:
                app.processing_results[processing_id]['status'] = 'completed'
                app.processing_results[processing_id]['output_file'] = temp_filename
                
            print(f"Background processing completed for {processing_id}")
            save_projects()
            
        except Exception as e:
            print(f"Background processing error for {processing_id}: {e}")
            
            if project_id and project_id in app.projects:
                app.projects[project_id]['processing_results'][processing_id]['status'] = 'failed'
                app.projects[project_id]['processing_results'][processing_id]['error'] = str(e)
            else:
                app.processing_results[processing_id]['status'] = 'failed'
                app.processing_results[processing_id]['error'] = str(e)
            save_projects()
    
    thread = threading.Thread(target=process_video)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'processing_id': processing_id,
        'project_id': project_id,
        'message': 'Video processing started in background',
        'export_mode': export_mode,
        'segments_count': len(segments)
    })

@app.route('/stop_video_processing', methods=['POST'])
def stop_video_processing():
    
    data = request.json or {}
    processing_id = data.get('processing_id')
    
    if not processing_id:
        return jsonify({'error': 'Processing ID required'}), 400
    
    print(f"Stopping background video processing: {processing_id}")
    
    
    stopped = False
    for project_id, project in app.projects.items():
        if processing_id in project.get('processing_results', {}):
            proc_result = project['processing_results'][processing_id]
            if proc_result.get('status') == 'in_progress':
                proc_result['status'] = 'cancelled'
                proc_result['stop_flag'] = True
                stopped = True
                print(f"Stopped processing {processing_id} in project {project_id}")
                break
    
    
    if not stopped and processing_id in app.processing_results:
        proc_result = app.processing_results[processing_id]
        if proc_result.get('status') == 'in_progress':
            proc_result['status'] = 'cancelled'
            proc_result['stop_flag'] = True
            stopped = True
            print(f"Stopped legacy processing {processing_id}")
    
    if stopped:
        save_projects()
        return jsonify({'success': True, 'message': f'Processing {processing_id} stopped'})
    else:
        return jsonify({'success': False, 'message': f'Processing {processing_id} not found or not running'})

@app.route('/check_processing_status/<processing_id>', methods=['GET'])
def check_processing_status(processing_id):
    
    processing_result = None
    
    
    for project_id, project_data in app.projects.items():
        if processing_id in project_data.get('processing_results', {}):
            processing_result = project_data['processing_results'][processing_id]
            break
    
    
    if not processing_result and hasattr(app, 'processing_results') and processing_id in app.processing_results:
        processing_result = app.processing_results[processing_id]
    
    if not processing_result:
        return jsonify({'status': 'not_found', 'message': 'Processing ID not found'}), 404
    
    status = processing_result.get('status', 'in_progress')
    
    if status == 'completed':
        return jsonify({
            'status': 'completed',
            'message': 'Video processing completed',
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count'],
            'created_at': processing_result['created_at'],
            'project_id': processing_result.get('project_id')
        })
    elif status == 'failed':
        return jsonify({
            'status': 'failed',
            'message': 'Video processing failed',
            'error': processing_result.get('error', 'Unknown error'),
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count'],
            'project_id': processing_result.get('project_id')
        })
    else:
        return jsonify({
            'status': 'in_progress',
            'message': 'Video still processing',
            'export_mode': processing_result['export_mode'],
            'segments_count': processing_result['segments_count'],
            'project_id': processing_result.get('project_id')
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
    
    
    processing_result = None
    project_id = None
    
    
    for pid, project_data in app.projects.items():
        if processing_id in project_data.get('processing_results', {}):
            processing_result = project_data['processing_results'][processing_id]
            project_id = pid
            break
    
    
    if not processing_result and hasattr(app, 'processing_results') and processing_id in app.processing_results:
        processing_result = app.processing_results[processing_id]
    
    if not processing_result:
        return jsonify({'error': 'Processing ID not found or expired'}), 404
    
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
        
        
        import time
        max_wait = 30  
        wait_count = 0
        
        while wait_count < max_wait:
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1000:
                
                try:
                    shutil.copy2(temp_file, output_filename)
                    
                    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 1000:
                        break
                except (OSError, shutil.Error) as e:
                    print(f"Copy attempt {wait_count + 1} failed: {e}")
            else:
                print(f"Waiting for temp file to be ready... (attempt {wait_count + 1})")
            
            wait_count += 1
            time.sleep(1)
        
        if wait_count >= max_wait:
            print(f"Failed to copy temp file after {max_wait} seconds")
            return jsonify({'error': 'Video file not ready for processing'}), 500
        
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
        
        
        time.sleep(2)
        
        temp_files_to_clean = []
        
        if os.path.exists(temp_file):
            temp_files_to_clean.append(temp_file)
        
        if qr_path and os.path.exists(qr_path):
            temp_files_to_clean.append(qr_path)
        
        if logo_path and os.path.exists(logo_path):
            temp_files_to_clean.append(logo_path)
        
        if processing_result.get('music_path') and os.path.exists(processing_result['music_path']):
            temp_files_to_clean.append(processing_result['music_path'])
        
        for temp_file_path in temp_files_to_clean:
            try:
                os.remove(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")
            except OSError as e:
                print(f"Warning: Could not remove temporary file {temp_file_path}: {e}")
        
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
        
        
        if project_id and project_id in app.projects:
            app.projects[project_id]['processing_results'][processing_id]['output_file'] = output_filename
        else:
            app.processing_results[processing_id]['output_file'] = output_filename
        save_projects()
        
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
    
    
    processing_result = None
    
    
    for project_id, project_data in app.projects.items():
        if processing_id in project_data.get('processing_results', {}):
            processing_result = project_data['processing_results'][processing_id]
            print(f"Found processing result in project {project_id}: {processing_result}")
            break
    
    
    if not processing_result and hasattr(app, 'processing_results') and processing_id in app.processing_results:
        processing_result = app.processing_results[processing_id]
        print(f"Found processing result in legacy storage: {processing_result}")
    
    if not processing_result:
        print(f"Processing ID {processing_id} not found")
        return jsonify({'error': 'Tour result not found'}), 404
    
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
            'segments_count': processing_result.get('segments_count'),
            'project_id': processing_result.get('project_id')
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
@app.route('/edit/<processing_id>')
def edit_page(processing_id=None):
    return send_file('templates/edit.html', mimetype='text/html')

@app.route('/get_video_data/<processing_id>', methods=['GET'])
def get_video_data(processing_id):
    
    processing_result = None
    project_id = None
    
    
    for pid, project_data in app.projects.items():
        if processing_id in project_data.get('processing_results', {}):
            processing_result = project_data['processing_results'][processing_id]
            project_id = pid
            break
    
    
    if not processing_result and hasattr(app, 'processing_results') and processing_id in app.processing_results:
        processing_result = app.processing_results[processing_id]
    
    if not processing_result:
        return jsonify({
            'success': False,
            'error': 'Processing ID not found'
        }), 404
    
    
    video_path = None
    if project_id and project_id in app.projects:
        video_path = app.projects[project_id]['video_path']
        video_info = app.projects[project_id].get('video_info')
    else:
        video_id = processing_result.get('video_id')
        if video_id and video_id in uploaded_videos:
            video_path = uploaded_videos[video_id]
        else:
            return jsonify({
                'success': False,
                'error': 'Video not found'
            }), 404
        video_info = None
    
    if not os.path.exists(video_path):
        return jsonify({
            'success': False,
            'error': 'Video file not found on server'
        }), 404
    
    try:
        
        if video_info:
            video_data = {
                'duration': video_info['duration'],
                'width': video_info['width'],
                'height': video_info['height'],
                'video_id': processing_result.get('video_id'),
                'video_path': video_path,
                'processing_id': processing_id,
                'project_id': project_id
            }
        else:
            editor = GuidedVideoEditor(video_path)
            if not editor.video_info:
                return jsonify({
                    'success': False,
                    'error': 'Invalid video file'
                }), 400
            
            video_data = {
                'duration': editor.video_info['duration'],
                'width': editor.video_info['width'],
                'height': editor.video_info['height'],
                'video_id': processing_result.get('video_id'),
                'video_path': video_path,
                'processing_id': processing_id,
                'project_id': project_id
            }
        
        return jsonify({
            'success': True,
            'video_data': video_data
        })
    except Exception as e:
        print(f"Error getting video data: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get video data: {str(e)}'
        }), 500

@app.route('/delivery')
@app.route('/delivery/<processing_id>')
def delivery_page(processing_id=None):
    return send_file('templates/delivery.html', mimetype='text/html')

@app.route('/export')
@app.route('/export/<processing_id>')
def export_page(processing_id=None):
    return send_file('templates/export.html', mimetype='text/html')

@app.route('/<path:filename>')
def serve_static(filename):
    return safe_send_file(filename)

@app.route('/ai_segment_detect', methods=['POST'])
def ai_segment_detect():
    data = request.json
    video_id = data.get('video_id')
    project_id = data.get('project_id')
    detection_interval = data.get('detection_interval', 2.0)   
    unfurnished_mode = data.get('unfurnished_mode', False)   
    
    
    video_path = None
    if project_id and project_id in app.projects:
        video_path = app.projects[project_id]['video_path']
        print(f"AI segment detection for project {project_id}: {video_path} (unfurnished_mode: {unfurnished_mode})")
    elif video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"AI segment detection for legacy video: {video_path} (unfurnished_mode: {unfurnished_mode})")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent video for AI segment detection: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    try:
        print(f"Starting AI segment detection with interval: {detection_interval}s (unfurnished_mode: {unfurnished_mode})")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detection_id = f"detect_{project_id or 'legacy'}_{timestamp}_{uuid.uuid4().hex[:6]}"
        
        
        if project_id and project_id in app.projects:
            detection_sessions = app.projects[project_id]['detection_sessions']
            for existing_id, existing_session in list(detection_sessions.items()):
                if existing_session.get('status') == 'in_progress':
                    print(f"Cancelling existing detection session for project {project_id}: {existing_id}")
                    existing_session['status'] = 'cancelled'
                    existing_session['stop_flag'] = True
        else:
            
            if not hasattr(app, 'detection_sessions'):
                app.detection_sessions = {}
            for existing_id, existing_session in list(app.detection_sessions.items()):
                if existing_session.get('status') == 'in_progress' and existing_session.get('video_path') == video_path:
                    print(f"Cancelling existing legacy detection session: {existing_id}")
                    existing_session['status'] = 'cancelled'
                    existing_session['stop_flag'] = True
        
        
        detection_session = {
            'video_path': video_path,
            'project_id': project_id,
            'status': 'in_progress',
            'segments': [],
            'created_at': timestamp,
            'stop_flag': False,
            'unfurnished_mode': unfurnished_mode  
        }
        
        if project_id and project_id in app.projects:
            app.projects[project_id]['detection_sessions'][detection_id] = detection_session
        else:
            app.detection_sessions[detection_id] = detection_session
        
        def detection_callback(update):
            
            session = None
            if project_id and project_id in app.projects:
                session = app.projects[project_id]['detection_sessions'].get(detection_id)
            else:
                session = app.detection_sessions.get(detection_id)
            
            if session:
                if session.get('stop_flag', False):
                    print(f"Detection {detection_id} stopped by flag")
                    return False  
                
                if update['type'] == 'segment_complete':
                    session['segments'] = [s for s in session['segments'] if not (s.get('temporary') and s.get('room') == update['segment']['room'])]
                    session['segments'].append(update['segment'])
                    print(f"Segment detected: {update['segment']['display_name']} ({update['segment']['start']:.1f}s - {update['segment']['end']:.1f}s)")
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
                segments = detect_room_transitions_realtime(video_path, detection_callback, detection_interval, unfurnished_mode)
                
                
                if project_id and project_id in app.projects and detection_id in app.projects[project_id]['detection_sessions']:
                    app.projects[project_id]['detection_sessions'][detection_id]['status'] = 'completed'
                    app.projects[project_id]['detection_sessions'][detection_id]['segments'] = segments
                    print(f"AI detection completed for project {project_id}: {detection_id}")
                elif detection_id in app.detection_sessions:
                    app.detection_sessions[detection_id]['status'] = 'completed'
                    app.detection_sessions[detection_id]['segments'] = segments
                    print(f"AI detection completed for legacy session: {detection_id}")
                
                save_projects()
                
            except Exception as e:
                print(f"AI detection error for {detection_id}: {e}")
                
                if project_id and project_id in app.projects and detection_id in app.projects[project_id]['detection_sessions']:
                    app.projects[project_id]['detection_sessions'][detection_id]['status'] = 'failed'
                    app.projects[project_id]['detection_sessions'][detection_id]['error'] = str(e)
                elif detection_id in app.detection_sessions:
                    app.detection_sessions[detection_id]['status'] = 'failed'
                    app.detection_sessions[detection_id]['error'] = str(e)
                
                save_projects()
        
        thread = threading.Thread(target=run_detection)
        thread.daemon = True
        thread.start()
        
        save_projects()
        
        return jsonify({
            'success': True,
            'detection_id': detection_id,
            'project_id': project_id,
            'unfurnished_mode': unfurnished_mode,
            'message': 'AI segment detection started'
        })
        
    except Exception as e:
        print(f"AI segment detection failed: {e}")
        return jsonify({'error': f'AI segment detection failed: {str(e)}'}), 500

@app.route('/check_detection_status/<detection_id>', methods=['GET'])
def check_detection_status(detection_id):
    
    session = None
    
    
    for project_id, project_data in app.projects.items():
        if detection_id in project_data.get('detection_sessions', {}):
            session = project_data['detection_sessions'][detection_id]
            break
    
    
    if not session and hasattr(app, 'detection_sessions') and detection_id in app.detection_sessions:
        session = app.detection_sessions[detection_id]
    
    if not session:
        return jsonify({'status': 'not_found', 'message': 'Detection ID not found'}), 404
    
    status = session.get('status', 'in_progress')
    segments = session.get('segments', [])
    
    if status == 'completed':
        return jsonify({
            'status': 'completed',
            'segments': segments,
            'segments_count': len(segments),
            'project_id': session.get('project_id')
        })
    elif status == 'failed':
        return jsonify({
            'status': 'failed',
            'error': session.get('error', 'Unknown error'),
            'project_id': session.get('project_id')
        })
    else:
        return jsonify({
            'status': 'in_progress',
            'progress': session.get('progress', 0),
            'segments': segments,
            'segments_count': len(segments),
            'project_id': session.get('project_id')
        })

@app.route('/auto_detect_room_label', methods=['POST'])
def auto_detect_room_label():
    data = request.json
    video_id = data.get('video_id')
    project_id = data.get('project_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    unfurnished_mode = data.get('unfurnished_mode', False)  
    
    if not all([start_time is not None, end_time is not None]):
        return jsonify({'error': 'Missing required parameters: start_time, end_time'}), 400
    
    
    video_path = None
    if project_id and project_id in app.projects:
        video_path = app.projects[project_id]['video_path']
        print(f"Auto-detecting room label for project {project_id}, segment: {start_time}s - {end_time}s (unfurnished_mode: {unfurnished_mode})")
    elif video_id and video_id in uploaded_videos:
        video_path = uploaded_videos[video_id]
        print(f"Auto-detecting room label for legacy video, segment: {start_time}s - {end_time}s (unfurnished_mode: {unfurnished_mode})")
    elif len(uploaded_videos) > 0:
        video_path = list(uploaded_videos.values())[-1]
        print(f"Using most recent video for auto-detection: {video_path}")
    else:
        return jsonify({'error': 'No video uploaded. Please upload a video first.'}), 400
    
    if not os.path.exists(video_path):
        return jsonify({'error': f'Video file not found: {video_path}'}), 400
    
    try:
        
        print(f"Auto-detecting room label for segment {start_time}s - {end_time}s (unfurnished_mode: {unfurnished_mode})")
        room_label = detect_scene_label(video_path, start_time, end_time, unfurnished_mode=unfurnished_mode)
        
        if room_label:
            display_name = get_room_display_name(room_label)
            
            return jsonify({
                'success': True,
                'room_label': room_label,
                'display_name': display_name,
                'unfurnished_mode': unfurnished_mode,
                'project_id': project_id,
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
    try:
        data = request.json or {}
        project_id = data.get('project_id')
        
        stopped_count = 0
        
        if project_id and project_id in app.projects:
            
            detection_sessions = app.projects[project_id]['detection_sessions']
            for detection_id, session in detection_sessions.items():
                if session.get('status') == 'in_progress':
                    print(f"Stopping AI detection session for project {project_id}: {detection_id}")
                    session['status'] = 'stopped'
                    session['stop_flag'] = True
                    stopped_count += 1
        else:
            
            
            for pid, project_data in app.projects.items():
                detection_sessions = project_data.get('detection_sessions', {})
                for detection_id, session in detection_sessions.items():
                    if session.get('status') == 'in_progress':
                        print(f"Stopping AI detection session for project {pid}: {detection_id}")
                        session['status'] = 'stopped'
                        session['stop_flag'] = True
                        stopped_count += 1
            
            
            if hasattr(app, 'detection_sessions'):
                for detection_id, session in app.detection_sessions.items():
                    if session.get('status') == 'in_progress':
                        print(f"Stopping legacy AI detection session: {detection_id}")
                        session['status'] = 'stopped'
                        session['stop_flag'] = True
                        stopped_count += 1
        
        save_projects()
        
        return jsonify({
            'success': True,
            'message': f'Stopped {stopped_count} active detection sessions'
        })
        
    except Exception as e:
        print(f"Error stopping AI detection: {e}")
        return jsonify({'error': f'Failed to stop detection: {str(e)}'}), 500

@app.route('/cleanup_temp_files', methods=['POST'])
def cleanup_temp_files_endpoint():
    try:
        result = _cleanup_temp_files(force=False)
        
        if not result['cleaned_count'] and not result['errors']:
            return jsonify({
                'success': True,
                'message': 'No temp files found that needed cleaning'
            })
        
        if result['errors']:
            return jsonify({
                'success': True,
                'warning': True,
                'message': f'Cleanup completed with some warnings. Removed {result["cleaned_count"]} files.',
                'errors': result['errors']
            })
        
        return jsonify({
            'success': True,
            'message': f'Temporary files cleanup completed. Removed {result["cleaned_count"]} files.'
        })
    except Exception as e:
        print(f"Error during manual cleanup: {e}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500





        





        







        




        





@app.route('/save_session_data', methods=['POST'])
def save_session_data():
    
    try:
        data = request.json
        project_id = data.get('project_id')
        processing_id = data.get('processing_id')
        session_data = data.get('session_data')
        
        if not project_id:
            return jsonify({'success': False, 'error': 'Project ID is required'}), 400
        
        if not session_data:
            return jsonify({'success': False, 'error': 'Session data is required'}), 400
        
        
        project_dir = None
        
        
        if project_id:
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            potential_project_dir = os.path.join(uploads_dir, project_id)
            if os.path.exists(potential_project_dir):
                project_dir = potential_project_dir
        
        
        if not project_dir and project_id in app.projects:
            project_dir = app.projects[project_id].get('project_dir')
        
        
        if not project_dir and processing_id:
            for pid, proj_data in app.projects.items():
                if proj_data.get('processing_id') == processing_id:
                    project_dir = proj_data.get('project_dir')
                    break
        
        if not project_dir:
            return jsonify({'success': False, 'error': 'Project directory not found'}), 404
        
        
        session_file = os.path.join(project_dir, 'session_data.json')
        
        
        session_data_with_meta = {
            'project_id': project_id,
            'processing_id': processing_id,
            'saved_at': datetime.now().isoformat(),
            'data': session_data
        }
        
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data_with_meta, f, separators=(',', ':'), ensure_ascii=False)
        
        
        return jsonify({
            'success': True,
            'message': 'Session data saved successfully',
            'file_path': session_file
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/load_session_data', methods=['POST'])
def load_session_data():
    
    try:
        data = request.json
        project_id = data.get('project_id')
        processing_id = data.get('processing_id')
        
        if not project_id:
            return jsonify({'success': False, 'error': 'Project ID is required'}), 400
        
        
        project_dir = None
        
        
        if project_id:
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            potential_project_dir = os.path.join(uploads_dir, project_id)
            if os.path.exists(potential_project_dir):
                project_dir = potential_project_dir
        
        
        if not project_dir and project_id in app.projects:
            project_dir = app.projects[project_id].get('project_dir')
        
        
        if not project_dir and processing_id:
            for pid, proj_data in app.projects.items():
                if proj_data.get('processing_id') == processing_id:
                    project_dir = proj_data.get('project_dir')
                    break
        
        if not project_dir:
            return jsonify({'success': False, 'error': 'Project directory not found'}), 404
        
        
        session_file = os.path.join(project_dir, 'session_data.json')
        
        if not os.path.exists(session_file):
            print(f"Session data file not found: {session_file}")
            return jsonify({
                'success': False,
                'error': 'Session data file not found'
            }), 404
        
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data_with_meta = json.load(f)
        
        session_data = session_data_with_meta.get('data', {})
        saved_at = session_data_with_meta.get('saved_at', 'Unknown')
        
        print(f"Session data loaded from: {session_file}")
        print(f"   Saved at: {saved_at}")
        print(f"   Data keys: {list(session_data.keys()) if session_data else 'None'}")
        
        return jsonify({
            'success': True,
            'session_data': session_data,
            'saved_at': saved_at,
            'file_path': session_file
        })
        
    except Exception as e:
        print(f"Load session data error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test_session_endpoints', methods=['GET'])
def test_session_endpoints():
    
    return jsonify({
        'success': True,
        'message': 'Session endpoints are working',
        'endpoints': ['/save_session_data', '/load_session_data', '/debug_session']
    })

@app.route('/debug_session', methods=['POST'])
def debug_session():
    
    try:
        data = request.json
        project_id = data.get('project_id')
        processing_id = data.get('processing_id')
        video_id = data.get('video_id')
        
        print(f"🔍 Session Debug Request:")
        print(f"   Project ID: {project_id}")
        print(f"   Processing ID: {processing_id}")
        print(f"   Video ID: {video_id}")
        
        
        project_found = False
        project_dir = None
        if project_id and project_id in app.projects:
            project_found = True
            project_data = app.projects[project_id]
            project_dir = project_data.get('project_dir')
            print(f"   Project found: {project_data}")
        else:
            print(f"   Project NOT found in app.projects")
            print(f"   Available projects: {list(app.projects.keys())}")
        
        
        session_file_exists = False
        session_file_path = None
        if project_dir:
            session_file_path = os.path.join(project_dir, 'session_data.json')
            session_file_exists = os.path.exists(session_file_path)
            print(f"   Session file exists: {session_file_exists}")
            print(f"   Session file path: {session_file_path}")
        
        return jsonify({
            'success': True,
            'project_found': project_found,
            'project_id': project_id,
            'processing_id': processing_id,
            'video_id': video_id,
            'available_projects': list(app.projects.keys()),
            'project_dir': project_dir,
            'session_file_exists': session_file_exists,
            'session_file_path': session_file_path
        })
        
    except Exception as e:
        print(f"Session debug error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)  