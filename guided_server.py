
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
import threading
from post_processor import add_combined_overlays

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
            print(f"No label detected for segment {start_time:.1f}s-{end_time:.1f}s")
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
            
            if export_mode == 'segments':
                success = editor.create_tour(temp_filename, quality=quality)
            elif export_mode == 'speedup':
                success = editor.create_speedup_tour_simple(temp_filename, speed_factor)
            else:
                success = editor.create_tour(temp_filename, quality=quality)
            
            if not success:
                app.processing_results[processing_id]['status'] = 'failed'
                app.processing_results[processing_id]['error'] = 'Failed to process video segments'
                return
            
            if music_path and os.path.exists(music_path):
                print(f"Adding music overlay: {music_path} (volume: {music_volume})")
                music_success = editor.add_music_overlay(temp_filename, music_path, music_volume)
                if music_success:
                    print("Music overlay added successfully")
                else:
                    print("Failed to add music overlay - continuing without music")
            
            app.processing_results[processing_id]['status'] = 'completed'
            print(f"Background processing completed for {processing_id}")
            
        except Exception as e:
            print(f"Background processing error for {processing_id}: {e}")
            app.processing_results[processing_id]['status'] = 'failed'
            app.processing_results[processing_id]['error'] = str(e)
    
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
    agency_name = data.get('agency_name')
    agent_phone = data.get('agent_phone')
    
    if not processing_id:
        return jsonify({'error': 'Processing ID required'}), 400
    
    if not agent_name or not agency_name:
        return jsonify({'error': 'Agent name and agency name are required'}), 400
    
    if not hasattr(app, 'processing_results') or processing_id not in app.processing_results:
        return jsonify({'error': 'Processing ID not found or expired'}), 404
    
    processing_result = app.processing_results[processing_id]
    temp_file = processing_result['temp_file']
    
    if not os.path.exists(temp_file):
        return jsonify({'error': 'Processed video file not found'}), 404
    
    print(f"Adding overlays to processed video: {temp_file}")
    print(f"Agent info: {agent_name} @ {agency_name} | {agent_phone}")
    
    try:
        archive_dir = 'archive'
        os.makedirs(archive_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = os.path.join(archive_dir, f'guided_tour_{timestamp}.mp4')
        
        import shutil
        shutil.copy2(temp_file, output_filename)
        
        if qr_path and os.path.exists(qr_path):
            print(f"Adding combined overlays with QR code")
            overlay_success = add_combined_overlays(
                output_filename,
                agent_name,
                agency_name,
                agent_phone=agent_phone,
                qr_image_path=qr_path,
                qr_position='top_right'
            )
        else:
            print(f"Adding agent watermark only")
            overlay_success = add_combined_overlays(
                output_filename,
                agent_name,
                agency_name,
                agent_phone=agent_phone
            )
        
        if not overlay_success:
            print("Failed to add overlays - using video without overlays")
        
        try:
            os.remove(temp_file)
            print(f"Cleaned up temporary file: {temp_file}")
        except OSError as e:
            print(f"Warning: Could not remove temporary file {temp_file}: {e}")
        
        if qr_path and os.path.exists(qr_path):
            try:
                os.remove(qr_path)
                print(f"Cleaned up QR file: {qr_path}")
            except OSError as e:
                print(f"Warning: Could not remove QR file {qr_path}: {e}")
        
        # Store the output file path in processing results for later retrieval
        app.processing_results[processing_id]['output_file'] = output_filename
        
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
    
    if 'output_file' in processing_result:
        print(f"Output file found: {processing_result['output_file']}")
        return jsonify({
            'success': True,
            'output_file': processing_result['output_file'],
            'message': 'Tour created successfully!',
            'export_mode': processing_result['export_mode'],
            'speed_factor': processing_result.get('speed_factor'),
            'quality': processing_result.get('quality'),
            'segments_count': processing_result.get('segments_count')
        })
    else:
        print(f"No output_file in processing result")
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)  