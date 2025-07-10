# AI Real Estate Video Compiler

## Quick Start (Testing Phase)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test Basic Functionality

#### Option A: Multiple Short Clips (Original Mode)
```bash
mkdir test_videos

# Run the compiler on multiple clips
python video_compiler.py test_videos --output property_tour.mp4
```

#### Option B: Single Walkthrough Video (NEW: Auto-Split Mode)
```bash
# Auto-split a long walkthrough video into room clips
python video_compiler.py my_walkthrough.mp4 --split --output final_tour.mp4

# Advanced splitting options
python video_compiler.py walkthrough.mp4 --split --split-interval 2.0 --min-scene-duration 3.0
```

### 3. Current Status
✅ Video file discovery and validation  
✅ Real AI scene classification (OpenAI Vision API)
✅ Intelligent video trimming and assembly
✅ **NEW: Auto-split walkthrough videos**

### Features
- **Multiple Clips Mode**: Process folder of short video clips
- **Walkthrough Mode**: Auto-split long walkthrough videos into scenes
- **AI Classification**: Real room type detection (exterior, living room, kitchen, bedroom, bathroom)
- **Smart Trimming**: Remove awkward starts/ends automatically
- **Professional Assembly**: Logical scene ordering with smooth transitions
- **Ready Output**: Upload-ready MP4 files

### Usage Examples
- `python video_compiler.py clips_folder/` - Process multiple clips
- `python video_compiler.py walkthrough.mp4 --split` - Auto-split long video
- Outputs professional property tour videos automatically!

### Dependencies
- Python 3.10+
- OpenCV (for video analysis)
- MoviePy (for video editing)
- OpenAI API (for scene classification) 

## DLD API Credentials

Create a `.env` file (not committed) alongside `guided_server.py` with either:

```
DLD_USERNAME=your_api_username
DLD_PASSWORD=your_api_password
```

or

```
DLD_BEARER_TOKEN=your_bearer_token
```

The server automatically loads these at startup (via `python-dotenv`). If you still supply credentials through the listing-verification form, those override the environment values. 