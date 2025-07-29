# Viewit Video Studio

A web-based AI-powered video editing platform specifically designed for creating professional property walktrhough videos. 

Features intelligent scene detection, agent branding, background music integration, and Dubai Land Department (DLD) listing verification.


## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys
Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key

FREESOUND_API_KEY=your_freesound_api_key

DLD_USERNAME=your_dld_username
DLD_PASSWORD=your_dld_password
# OR
DLD_BEARER_TOKEN=your_dld_bearer_token
```

### 3. Run the Application
```bash
python guided_server.py
```

The application will be available at `http://localhost:5000`

## Usage Workflow

1. **Upload Video**: Navigate to the upload page and drag/drop your property walkthrough video
2. **Edit Segments**: Use the interactive editor to select and label video segments or segment with AI
3. **Add Music**: Search and select background music from Freesound library
4. **Agent Details**: Add agent/agency information for branding
5. **Export**: Export your professional walkthrough
6. **Delivery**: Download or share your completed video

## API Endpoints

The Flask application provides several API endpoints:

- `POST /upload` - Upload video files
- `POST /ai_segment_detect` - AI-powered scene detection
- `POST /search_music` - Search background music
- `POST /start_video_processing` - Begin video processing
- `POST /verify_listing` - DLD listing verification
- `GET /delivery/<processing_id>` - Access completed videos

## Technical Architecture

### Core Components
- **guided_server.py** - Main Flask web server
- **guided_editor.py** - Video editing logic and segment management
- **scene_detection.py** - AI-powered room/scene classification
- **video_processor.py** - Video processing and manipulation
- **post_processor.py** - Overlays, watermarks, and final output
- **tour_creator.py** - Video assembly and tour creation
- **dld_api.py** - Dubai Land Department integration

### Dependencies
- **Flask** - Web framework and API server
- **OpenCV** - Video analysis and processing
- **MoviePy** - Video editing and manipulation
- **OpenAI** - AI scene classification


## Configuration

### Video Processing
- Supports MP4 format
- Multiple quality presets (standard, high quality)
- Variable speed processing (1x to 5x)

### AI Scene Detection
Automatically detects and classifies:
- Living rooms
- Kitchens  
- Bedrooms
- Bathrooms
- Exterior views
- Other room types
