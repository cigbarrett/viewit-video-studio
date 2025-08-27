        let video = null;
        let videoDuration = 0;
        let segments = [];
        let selectionMode = 'click';
        
        let musicTracks = [];
        let selectedMusicTrack = null;
        let musicAudio = null;
        
        let isMusicLoading = false;
        let isDetectionLoading = false;

        function shouldDisableExport() {
            return isMusicLoading || isDetectionLoading;
        }
        
        function updateExportButtonState() {
            const exportButton = document.getElementById('exportButton');
            const shouldDisable = shouldDisableExport();
            
            if (shouldDisable) {
                exportButton.disabled = true;
                exportButton.classList.add('disabled');
            } else {
                exportButton.disabled = false;
                exportButton.classList.remove('disabled');
            }
        }
        
        // Function to fetch video data from server using processing ID
        function fetchVideoData(processingId) {
            // Check if processingId exists on the server
            fetch(`/get_video_data/${processingId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Processing ID not found');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        // Store the video data
                        window.uploadedVideoData = data.video_data;
                        console.log('Loaded video data from server:', window.uploadedVideoData);
                        videoDuration = window.uploadedVideoData.duration;
                        
                        // Save to session storage for persistence
                        sessionStorage.setItem('uploadedVideoData', JSON.stringify(window.uploadedVideoData));
                        
                        // Initialize the video player
                        initializeVideoPlayer();
                    } else {
                        throw new Error(data.error || 'Failed to load video data');
                    }
                })
                .catch(error => {
                    console.error('Error loading video data:', error);
                    alert('Processing ID not found. Redirecting to upload page.');
                    window.location.href = '/';
                });
        }
        
        // Function to update URL with processing ID without reloading the page
        function updateUrlWithProcessingId(processingId) {
            if (processingId && window.location.pathname !== `/edit/${processingId}`) {
                const newUrl = `/edit/${processingId}`;
                window.history.pushState({ path: newUrl }, '', newUrl);
                console.log('Updated URL with processing ID:', processingId);
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            console.log('Edit page loaded');
            console.log('Current URL:', window.location.pathname);
            
            // Try to get processing ID from URL
            const pathParts = window.location.pathname.split('/');
            const processingId = pathParts[pathParts.length - 1];
            console.log('Path parts:', pathParts);
            console.log('Processing ID from URL:', processingId);
            
            // First check if we have a specific processing ID in the URL
            if (processingId && processingId !== 'edit') {
                console.log('Loading video data from processing ID:', processingId);
                // Fetch the video data using the processing ID
                fetchVideoData(processingId);
            } else {
                // Fall back to session storage data
                const videoData = sessionStorage.getItem('uploadedVideoData');
                if (videoData) {
                    window.uploadedVideoData = JSON.parse(videoData);
                    console.log('Loaded video data from session storage:', window.uploadedVideoData);
                    videoDuration = window.uploadedVideoData.duration;
                    initializeVideoPlayer();
                    
                    // Update URL with processing ID for shareable link
                    if (window.uploadedVideoData.processing_id) {
                        updateUrlWithProcessingId(window.uploadedVideoData.processing_id);
                    }
                } else {
                    alert('No video data found. Please upload a video first.');
                    window.location.href = '/';
                }
            }
            
            setupEventListeners();
            setupGlobalKeyboardShortcuts();
            setupMusicControls();
            setupFilterControls();
            loadMusicSuggestions();
            loadFilterPresets();
            initializeFilters(); // Initialize filters with proper defaults
            
            updateExportButtonState();
        });

        function initializeVideoPlayer() {
            video = document.getElementById('videoPlayer');
            
            video.src = `/${window.uploadedVideoData.video_path}`;
            
            video.addEventListener('loadedmetadata', function() {
                console.log('Video loaded:', video.src);
                console.log('Video duration:', video.duration);
                if (Math.abs(video.duration - videoDuration) > 1) {
                    videoDuration = video.duration;
                    createTimelineMarkers();
                }
                
                // Initialize scrub bar position
                updatePlayhead();
            });
            
            video.addEventListener('error', function(e) {
                console.error('Video loading error:', e);
                console.error('Video src:', video.src);
                alert('Failed to load video. Please try uploading again.');
            });
            
            video.addEventListener('timeupdate', updateTimeDisplay);
            video.addEventListener('timeupdate', updatePlayheadThrottled);
            
            video.addEventListener('play', function() {
                document.getElementById('playButton').innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                    </svg>
                `;
            });
            video.addEventListener('pause', function() {
                document.getElementById('playButton').innerHTML = `
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
            });
            
            initializeVideoInterface();
        }

        function initializeVideoInterface() {
            createTimelineMarkers();
            document.getElementById('startTime').max = videoDuration;
            document.getElementById('endTime').max = videoDuration;
            updateTimeDisplay();
        }

        function createTimelineMarkers() {
            const markers = document.getElementById('timelineMarkers');
            markers.innerHTML = '';
            const intervals = 10;
            for (let i = 0; i <= intervals; i++) {
                const time = (videoDuration / intervals) * i;
                const marker = document.createElement('span');
                marker.textContent = formatTime(time);
                markers.appendChild(marker);
            }
        }

        function setupEventListeners() {
            const timeline = document.getElementById('timeline');
            
            // Set up scrub bar functionality
            const scrubBar = document.getElementById('scrubBar');
            if (scrubBar) {
                scrubBar.addEventListener('click', handleScrubBarClick);
                scrubBar.addEventListener('mousedown', handleScrubBarMouseDown);
            }
            
            timeline.addEventListener('click', handleTimelineClick);
            
            let isScrubbing = false;
            let wasPlaying = false;
            
            timeline.addEventListener('mousedown', function(e) {
                if (!video) return;
                
                isScrubbing = true;
                wasPlaying = !video.paused;
                
                if (!video.paused) {
                    video.pause();
                }
                
                timeline.classList.add('scrubbing');
                
                handleScrub(e);
                
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', function(e) {
                if (isScrubbing && video) {
                    handleScrub(e);
                }
            });
            
            document.addEventListener('mouseup', function() {
                if (isScrubbing) {
                    isScrubbing = false;
                    timeline.classList.remove('scrubbing');
                    
                    if (wasPlaying && video.paused) {
                        video.play().catch(error => {
                            console.error('Error resuming playback after scrubbing:', error);
                        });
                    }
                }
            });
            
            document.getElementById('volumeSlider').addEventListener('input', function() {
                if (video) {
                    video.volume = this.value;
                }
            });

            document.querySelectorAll('input[name="exportMode"]').forEach(radio => {
                radio.addEventListener('change', handleExportModeChange);
            });
            
            document.getElementById('speedSlider').addEventListener('input', function() {
                document.getElementById('speedValue').textContent = this.value + 'x';
            });
            
            document.getElementById('segmentLengthSlider').addEventListener('input', function() {
                document.getElementById('segmentLengthValue').textContent = this.value + 's';
            });
        }

        function handleScrubBarClick(e) {
            if (!video) return;
            
            const rect = e.currentTarget.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const percent = Math.max(0, Math.min(1, mouseX / rect.width));
            const scrubTime = percent * videoDuration;
            
            video.currentTime = scrubTime;
            updatePlayhead();
        }
        
        function handleScrubBarMouseDown(e) {
            if (!video) return;
            
            const scrubBar = e.currentTarget;
            const wasPlaying = !video.paused;
            
            if (wasPlaying) {
                video.pause();
            }
            
            // Handle initial position
            handleScrubBarMove(e);
            
            // Set up mouse move and mouse up handlers
            function handleMouseMove(moveEvent) {
                handleScrubBarMove(moveEvent);
            }
            
            function handleMouseUp() {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
                
                if (wasPlaying) {
                    video.play().catch(error => console.error('Error resuming playback:', error));
                }
            }
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            
            e.preventDefault();
        }
        
        function handleScrubBarMove(e) {
            if (!video) return;
            
            const scrubBar = document.getElementById('scrubBar');
            const rect = scrubBar.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const percent = Math.max(0, Math.min(1, mouseX / rect.width));
            const scrubTime = percent * videoDuration;
            
            video.currentTime = scrubTime;
            updatePlayhead();
        }
        
        function handleScrub(e) {
            if (!video) return;
            
            const timeline = document.getElementById('timeline');
            const rect = timeline.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const percent = Math.max(0, Math.min(1, mouseX / rect.width));
            const scrubTime = percent * videoDuration;
            
            video.currentTime = scrubTime;
            
            updateTimeDisplay();
            
            updatePlayheadThrottled();
        }

        function handleExportModeChange(e) {
            const speedSettings = document.getElementById('speedSettings');
            if (e.target.value === 'speedup') {
                speedSettings.style.display = 'block';
            } else {
                speedSettings.style.display = 'none';
            }
        }

        function setupGlobalKeyboardShortcuts() {
            document.addEventListener('keydown', function(e) {
                const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
                
                if (!video) return;
                
                switch(e.key) {
                    case ' ':
                        if (!isTyping) {
                            e.preventDefault();
                            togglePlay().catch(error => {
                                console.error('Error in keyboard play/pause:', error);
                            });
                        }
                        break;
                        
                    case 'ArrowLeft':
                        if (!isTyping) {
                            e.preventDefault();
                            skipBackward();
                        }
                        break;
                        
                    case 'ArrowRight':
                        if (!isTyping) {
                            e.preventDefault();
                            skipForward();
                        }
                        break;
                        
                    case 'i':
                    case 'I':
                        if (!isTyping) {
                            e.preventDefault();
                            setInPoint();
                        }
                        break;
                        
                    case 'o':
                    case 'O':
                        if (!isTyping) {
                            e.preventDefault();
                            setOutPoint();
                        }
                        break;
                        
                    case 'Enter':
                        if (!isTyping) {
                            e.preventDefault();
                            const startTime = parseFloat(document.getElementById('startTime').value);
                            const endTime = parseFloat(document.getElementById('endTime').value);
                            if (!isNaN(startTime) && !isNaN(endTime)) {
                                addSegment(startTime, endTime);
                            }
                        }
                        break;
                        
                    case 'e':
                    case 'E':
                        if (!isTyping) {
                            e.preventDefault();
                            goToExport();
                        }
                        break;
                        
                    case '1':
                        if (!isTyping) {
                            e.preventDefault();
                            setSelectionMode('click');
                        }
                        break;
                        
                    case '2':
                        if (!isTyping) {
                            e.preventDefault();
                            setSelectionMode('live');
                        }
                        break;
                        
                    case 'Escape':
                        if (!isTyping) {
                            e.preventDefault();
                            clearCurrentSelection();
                        }
                        break;
                }
            });
            
            console.log('Global keyboard shortcuts enabled');
            console.log('Shortcuts: Space=Play/Pause, I=In Point, O=Out Point, Enter=Add Segment, E=Export, 1/2=Switch Modes, Esc=Clear');
        }

        function handleTimelineClick(e) {
            // Don't handle clicks on segments or their children
            if (e.target.classList.contains('timeline-segment') || e.target.closest('.timeline-segment')) {
                return;
            }
            
            if (selectionMode !== 'click') return;
            
            const rect = e.currentTarget.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const percent = clickX / rect.width;
            const clickTime = percent * videoDuration;
            
            const startInput = document.getElementById('startTime');
            const endInput = document.getElementById('endTime');
            
            if (!startInput.value || (startInput.value && endInput.value)) {
                startInput.value = clickTime.toFixed(1);
                endInput.value = '';
                if (video) video.currentTime = clickTime;
            } else if (startInput.value && !endInput.value) {
                endInput.value = clickTime.toFixed(1);
            }
        }

        function setSelectionMode(mode) {
            selectionMode = mode;
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            document.getElementById(mode + 'Mode').classList.add('active');
        }

        function setInPoint() {
            const currentTime = video ? video.currentTime : 0;
            document.getElementById('startTime').value = currentTime.toFixed(1);
            console.log(`In Point set to ${currentTime.toFixed(1)}s`);
        }

        function setOutPoint() {
            const currentTime = video ? video.currentTime : 0;
            document.getElementById('endTime').value = currentTime.toFixed(1);
            console.log(`Out Point set to ${currentTime.toFixed(1)}s`);
        }

        // Segment capture toggle (works for both mobile and desktop)
        let isCapturing = false;
        function toggleSegmentCapture() {
            const mobileButton = document.getElementById('mobilePlayPauseBtn');
            const desktopButton = document.getElementById('desktopPlayPauseBtn');
            
            // Update both buttons (one will be hidden based on screen size)
            [mobileButton, desktopButton].forEach(button => {
                if (button) {
                    const playIcon = button.querySelector('.play-icon');
                    const pauseIcon = button.querySelector('.pause-icon');
                    
                    if (!isCapturing) {
                        // First click: Set start point and switch to pause icon
                        playIcon.style.display = 'none';
                        pauseIcon.style.display = 'block';
                        button.classList.add('recording');
                        button.title = 'Stop Segment Capture';
                    } else {
                        // Second click: Set end point and switch back to play icon
                        playIcon.style.display = 'block';
                        pauseIcon.style.display = 'none';
                        button.classList.remove('recording');
                        button.title = 'Start Segment Capture';
                    }
                }
            });
            
            if (!isCapturing) {
                setInPoint();
                isCapturing = true;
                console.log('Started segment capture');
            } else {
                setOutPoint();
                isCapturing = false;
                console.log('Stopped segment capture');
            }
        }

        function clearCurrentSelection() {
            document.getElementById('startTime').value = '';
            document.getElementById('endTime').value = '';
            console.log('Selection cleared');
        }

        function skipBackward() {
            if (video) {
                video.currentTime = Math.max(0, video.currentTime - 5);
                console.log(`Skipped backward to ${video.currentTime.toFixed(1)}s`);
            }
        }

        function skipForward() {
            if (video) {
                video.currentTime = Math.min(videoDuration, video.currentTime + 5);
                console.log(`Skipped forward to ${video.currentTime.toFixed(1)}s`);
            }
        }

        async function previewSegment() {
            const startTime = parseFloat(document.getElementById('startTime').value);
            const endTime = parseFloat(document.getElementById('endTime').value);
            
            if (isNaN(startTime) || isNaN(endTime)) {
                alert('Please set valid start and end times');
                return;
            }
            
            if (video) {
                video.currentTime = startTime;
                try {
                    await video.play();
                    
                    const checkTime = () => {
                        if (video.currentTime >= endTime) {
                            video.pause();
                        } else {
                            requestAnimationFrame(checkTime);
                        }
                    };
                    requestAnimationFrame(checkTime);
                } catch (error) {
                    console.error('Error playing segment preview:', error);
                }
            }
        }

        async function togglePlay() {
            if (!video) return;
            
            try {
                if (video.paused) {
                    await video.play();
                    // Button state will be updated by the 'play' event listener
                } else {
                    video.pause();
                    // Button state will be updated by the 'pause' event listener
                }
            } catch (error) {
                console.error('Error toggling play state:', error);
                // If play failed, the pause event listener will handle the button state
            }
        }

        function toggleMute() {
            if (video) {
                video.muted = !video.muted;
                document.getElementById('muteButton').innerHTML = video.muted ? `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>
                    </svg>
                ` : `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
                    </svg>
                `;
            }
        }

        function toggleFullscreen() {
            const videoContainer = document.getElementById('playerContainer');
            const videoPlayer = document.getElementById('videoPlayer');
            
            if (!document.fullscreenElement) {
                // Enter fullscreen
                if (videoContainer.requestFullscreen) {
                    videoContainer.requestFullscreen();
                } else if (videoContainer.webkitRequestFullscreen) {
                    videoContainer.webkitRequestFullscreen();
                } else if (videoContainer.msRequestFullscreen) {
                    videoContainer.msRequestFullscreen();
                }
                
                // Ensure video maintains aspect ratio in fullscreen
                if (videoPlayer) {
                    videoPlayer.style.objectFit = 'contain';
                }
                
                // Update fullscreen button icon
                document.getElementById('fullscreenButton').innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
                    </svg>
                `;
            } else {
                // Exit fullscreen
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
                
                // Reset video style if needed
                if (videoPlayer) {
                    videoPlayer.style.objectFit = '';
                }
                
                // Update fullscreen button icon
                document.getElementById('fullscreenButton').innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                    </svg>
                `;
            }
        }

        // Listen for fullscreen changes to update button icon
        document.addEventListener('fullscreenchange', function() {
            const fullscreenButton = document.getElementById('fullscreenButton');
            const videoPlayer = document.getElementById('videoPlayer');
            
            if (document.fullscreenElement) {
                // Ensure video maintains aspect ratio in fullscreen
                if (videoPlayer) {
                    videoPlayer.style.objectFit = 'contain';
                }
                
                fullscreenButton.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
                    </svg>
                `;
            } else {
                // Reset video style when exiting fullscreen (e.g., via Escape key)
                if (videoPlayer) {
                    videoPlayer.style.objectFit = '';
                }
                
                fullscreenButton.innerHTML = `
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
                    </svg>
                `;
            }
        });

        function captureCurrentTime() {
            const currentTime = video ? video.currentTime : 0;
            const startInput = document.getElementById('startTime');
            const endInput = document.getElementById('endTime');
            
            if (!startInput.value) {
                startInput.value = currentTime.toFixed(1);
            } else if (!endInput.value) {
                endInput.value = currentTime.toFixed(1);
            } else {
                startInput.value = currentTime.toFixed(1);
                endInput.value = '';
            }
        }

        async function addSegment(startTime, endTime) {
            // If parameters are not provided, get them from the input fields
            if (startTime === undefined || endTime === undefined) {
                startTime = parseFloat(document.getElementById('startTime').value);
                endTime = parseFloat(document.getElementById('endTime').value);
            }
            
            const roomType = document.getElementById('roomType').value;
            
            console.log('Adding segment:', { startTime, endTime, roomType, videoDuration });
            
            if (isNaN(startTime) || isNaN(endTime)) {
                alert('Please enter valid start and end times');
                return;
            }
            
            if (startTime >= endTime) {
                alert('End time must be after start time');
                return;
            }
            
            if (startTime < 0 || endTime > videoDuration) {
                alert(`Times must be within video duration (0 - ${videoDuration.toFixed(1)}s)`);
                return;
            }
            
            // Clear input fields immediately after validation
            document.getElementById('startTime').value = '';
            document.getElementById('endTime').value = '';
            
            const segment = {
                id: Date.now(),
                start: startTime,
                end: endTime,
                duration: endTime - startTime,
                room: roomType === 'auto' ? null : roomType,
                detecting: roomType === 'auto',
                manual: roomType !== 'auto',
                editable: true
            };
            
            segments.push(segment);
            console.log('Segment added:', segment);
            
            updateSegmentsList();
            updateTimeline();
            
            if (roomType === 'auto') {
                await autoDetectRoomLabel(segment);
            }
            
            console.log('Total segments:', segments.length);
        }

        function updateSegmentsList() {
            const container = document.getElementById('segmentsList');
            console.log('updateSegmentsList called with segments:', segments);
            
            if (segments.length === 0) {
                container.innerHTML = '<p style="color: #90a4ae; text-align: center; padding: 20px;">No segments selected yet</p>';
                document.getElementById('totalDuration').textContent = 'Total: 0.0s';
                return;
            }
            
            let html = '';
            let totalDuration = 0;
            
            segments.sort((a, b) => a.start - b.start);
            
            segments.forEach((segment, index) => {
                console.log(`Processing segment ${index}:`, segment);
                
                const segStart = typeof segment.start === 'number' ? segment.start : (segment.start_time ?? 0);
                const segEnd = typeof segment.end === 'number' ? segment.end : (segment.end_time ?? 0);
                const segDuration = typeof segment.duration === 'number' ? segment.duration : (segEnd - segStart);
                totalDuration += segDuration;
                const roomLabels = {
                    kitchen: 'Kitchen',
                    bedroom: 'Bedroom',
                    bathroom: 'Bathroom',
                    living_room: 'Living Room',
                    closet: 'Closet',
                    office: 'Office',
                    dining_room: 'Dining Room',
                    balcony: 'Balcony',
                    unlabeled: 'Unlabeled'
                };
                
                let roomDisplayName, statusIcon, statusColor, titleClass;
                
                // Use segment number instead of icons
                const segmentNumber = index + 1;
                statusIcon = segmentNumber;
                
                if (segment.detecting) {
                    roomDisplayName = 'Detecting...';
                    statusColor = '#ff9800';
                    titleClass = 'detecting';
                } else if (segment.room) {
                    roomDisplayName = roomLabels[segment.room] || segment.room.replace('_', ' ');
                    const isAutoDetected = segment.room && segment.room !== 'auto' && !segment.manual;
                    statusColor = isAutoDetected ? '#4caf50' : '#2196f3';
                    titleClass = isAutoDetected ? 'detected' : 'manual';
                } else {
                    roomDisplayName = 'Unlabeled';
                    statusColor = '#90a4ae';
                    titleClass = '';
                }
                
                html += `
                    <div class="segment-item ${segment.detecting ? 'detecting' : ''}" data-segment-id="${segment.id}">
                        <div class="segment-info">
                            <div class="segment-title ${titleClass}">
                                <span class="status-icon" style="color: ${statusColor}; margin-right: 6px;">${statusIcon}</span>
                                ${roomDisplayName}
                            </div>
                            <div class="segment-details">
                                ${formatTime(segStart)} - ${formatTime(segEnd)} 
                                (${segDuration ? segDuration.toFixed(1) : '?'}s)
                            </div>
                        </div>
                        <div class="segment-actions">
                            ${segment.editable ? `
                                <button class="btn btn-primary" onclick="editSegment(${segment.id})">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                                    </svg>
                                </button>
                            ` : ''}
                            <button class="btn btn-danger" onclick="removeSegment(${segment.id})">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
            });
            
            console.log('Generated HTML for segments list');
            container.innerHTML = html;
            document.getElementById('totalDuration').textContent = 
                `Total: ${totalDuration.toFixed(1)}s (${segments.length} segments)`;
        }

        function removeSegment(id) {
            segments = segments.filter(s => s.id !== id);
            updateSegmentsList();
            updateTimeline();
        }

        function updateTimeline() {
            const track = document.getElementById('timelineTrack');
            track.innerHTML = '';
            
            segments.forEach((segment, index) => {
                const startPercent = (segment.start / videoDuration) * 100;
                const widthPercent = (segment.duration / videoDuration) * 100;
                
                const div = document.createElement('div');
                const roomClass = segment.room || 'unlabeled';
                div.className = `timeline-segment ${roomClass}`;
                div.style.left = startPercent + '%';
                div.style.width = widthPercent + '%';
                div.textContent = `${index + 1}`;
                const roomTitle = segment.room || 'Auto-detect';
                div.title = `${roomTitle}: ${formatTime(segment.start)} - ${formatTime(segment.end)}`;
                div.setAttribute('data-segment-id', segment.id);
                
                console.log(`Creating segment ${index}:`, segment);
                console.log(`Segment editable:`, segment.editable);
                
                if (segment.editable) {
                    console.log(`Setting up drag/resize for segment ${index}`);
                    div.style.cursor = 'move';
                    div.setAttribute('draggable', 'true');
                    
                    const leftHandle = document.createElement('div');
                    leftHandle.className = 'resize-handle left';
                    
                    const rightHandle = document.createElement('div');
                    rightHandle.className = 'resize-handle right';
                    
                    div.appendChild(leftHandle);
                    div.appendChild(rightHandle);
                    
                    setupSegmentDragAndResize(div, segment);
                } else {
                    console.log(`Segment ${index} is not editable`);
                }
                
                div.addEventListener('click', function(e) {
                    if (!e.target.classList.contains('resize-handle')) {
                        e.stopPropagation();
                        if (video) video.currentTime = segment.start;
                    }
                });
                
                track.appendChild(div);
            });
        }

        function setupSegmentDragAndResize(element, segment) {
            console.log('Setting up drag and resize for segment:', segment);
            console.log('Element:', element);
            console.log('Segment editable:', segment.editable);
            
            let isDragging = false;
            let isResizing = false;
            let resizeHandle = null;
            let startX, startLeft, startWidth;
            
            element.addEventListener('mousedown', function(e) {
                console.log('Mouse down on segment:', e.target);
                e.stopPropagation(); // Prevent timeline click handler
                e.preventDefault(); // Prevent default drag behavior
                
                if (e.target.classList.contains('resize-handle')) {
                    console.log('Starting resize');
                    isResizing = true;
                    resizeHandle = e.target;
                    startX = e.clientX;
                    startLeft = parseFloat(element.style.left);
                    startWidth = parseFloat(element.style.width);
                } else {
                    console.log('Starting drag');
                    isDragging = true;
                    startX = e.clientX;
                    startLeft = parseFloat(element.style.left);
                }
            });
            
            document.addEventListener('mousemove', function(e) {
                if (!isDragging && !isResizing) return;
                
                const deltaX = e.clientX - startX;
                const timelineWidth = document.getElementById('timelineTrack').offsetWidth;
                const percentDelta = (deltaX / timelineWidth) * 100;
                
                if (isDragging) {
                    console.log('Dragging segment');
                    const newLeft = Math.max(0, Math.min(100 - parseFloat(element.style.width), startLeft + percentDelta));
                    element.style.left = newLeft + '%';
                    
                    const newStart = (newLeft / 100) * videoDuration;
                    segment.start = newStart;
                    segment.end = newStart + segment.duration;
                } else if (isResizing) {
                    console.log('Resizing segment');
                    if (resizeHandle.classList.contains('left')) {
                        const newLeft = Math.max(0, Math.min(startLeft + percentDelta, startLeft + startWidth - 5));
                        const newWidth = startWidth - (newLeft - startLeft);
                        
                        if (newWidth > 5) {
                            element.style.left = newLeft + '%';
                            element.style.width = newWidth + '%';
                            
                            segment.start = (newLeft / 100) * videoDuration;
                            segment.duration = (newWidth / 100) * videoDuration;
                            segment.end = segment.start + segment.duration;
                        }
                    } else if (resizeHandle.classList.contains('right')) {
                        const newWidth = Math.max(5, Math.min(100 - startLeft, startWidth + percentDelta));
                        element.style.width = newWidth + '%';
                        
                        segment.duration = (newWidth / 100) * videoDuration;
                        segment.end = segment.start + segment.duration;
                    }
                }
                
                updateSegmentsList();
            });
            
            document.addEventListener('mouseup', function() {
                if (isDragging || isResizing) {
                    console.log('Ending drag/resize');
                }
                isDragging = false;
                isResizing = false;
                resizeHandle = null;
            });
        }

        function clearAll() {
            if (confirm('Clear all segments?')) {
                segments = [];
                updateSegmentsList();
                updateTimeline();
                clearCurrentSelection();
                console.log('All segments cleared');
            }
        }

        async function autoDetectRoomLabel(segment) {
            try {
                console.log('Auto-detecting room label for segment:', segment);
                
                const response = await fetch('/auto_detect_room_label', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        video_id: window.uploadedVideoData?.video_id,
                        project_id: window.uploadedVideoData?.project_id,
                        start_time: segment.start,
                        end_time: segment.end
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    segment.room = result.room_label;
                    segment.detecting = false;
                    segment.manual = false;
                    console.log('Auto-detected room:', result.room_label);
                    
                    updateSegmentsList();
                    updateTimeline();
                    
                } else {
                    console.error('Auto-detection failed:', result.error);
                    segment.room = 'unlabeled';
                    segment.detecting = false;
                    updateSegmentsList();
                    updateTimeline();
                }
                
            } catch (error) {
                console.error('Auto-detection error:', error);
                segment.room = 'unlabeled';
                segment.detecting = false;
                updateSegmentsList();
                updateTimeline();
            }
        }

        function showLoadingOverlay() {
            const overlay = document.getElementById('loadingOverlay');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            overlay.style.display = 'flex';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        }

        function hideLoadingOverlay() {
            const overlay = document.getElementById('loadingOverlay');
            overlay.style.display = 'none';
        }

        function updateProgress(percentage, status) {
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const loadingStatus = document.getElementById('loadingStatus');
            
            progressFill.style.width = percentage + '%';
            progressText.textContent = percentage + '%';
            loadingStatus.textContent = status;
        }

        function simulateProcessing() {
            const steps = [
                { progress: 5, status: 'Initializing video processor...', delay: 500 },
                { progress: 15, status: 'Analyzing video segments...', delay: 800 },
                { progress: 30, status: 'Extracting selected clips...', delay: 1200 },
                { progress: 50, status: 'Applying speed adjustments...', delay: 1000 },
                { progress: 70, status: 'Processing video effects...', delay: 1500 },
                { progress: 85, status: 'Combining segments...', delay: 1000 },
                { progress: 95, status: 'Finalizing tour video...', delay: 800 }
            ];
            
            let currentStep = 0;
            
            function processNextStep() {
                if (currentStep < steps.length) {
                    const step = steps[currentStep];
                    updateProgress(step.progress, step.status);
                    
                    setTimeout(() => {
                        currentStep++;
                        processNextStep();
                    }, step.delay);
                }
            }
            
            processNextStep();
        }

        function updateTimeDisplay() {
            if (!video) return;
            
            const current = formatTime(video.currentTime || 0);
            const total = formatTime(videoDuration);
            document.getElementById('timeDisplay').textContent = `${current} / ${total}`;
        }

        function updatePlayhead() {
            if (!video || !videoDuration) return;
            
            const percent = (video.currentTime / videoDuration) * 100;
            const playhead = document.getElementById('playhead');
            
            // Update the main timeline playhead
            requestAnimationFrame(() => {
                playhead.style.left = percent + '%';
            });
            
            // Update the scrub bar progress and handle
            const scrubBarProgress = document.getElementById('scrubBarProgress');
            const scrubBarHandle = document.getElementById('scrubBarHandle');
            
            if (scrubBarProgress && scrubBarHandle) {
                requestAnimationFrame(() => {
                    scrubBarProgress.style.width = percent + '%';
                    scrubBarHandle.style.left = percent + '%';
                });
            }
        }

        let lastPlayheadUpdate = 0;
        const PLAYHEAD_UPDATE_THROTTLE = 16;

        function updatePlayheadThrottled() {
            const now = Date.now();
            if (now - lastPlayheadUpdate >= PLAYHEAD_UPDATE_THROTTLE) {
                updatePlayhead();
                lastPlayheadUpdate = now;
            }
        }

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        function clearSelectionOverlay() {
            if (selectionOverlay) {
                selectionOverlay.remove();
                selectionOverlay = null;
            }
        }

        function setupMusicControls() {
            const customMusicQuery = document.getElementById('customMusicQuery');
            if (customMusicQuery) {
                customMusicQuery.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        searchCustomMusic();
                    }
                });
            }
        }

        async function loadMusicSuggestions() {
            const loadingEl = document.getElementById('loadingMusic');
            const tracksEl = document.getElementById('musicTracksHorizontal');
            
            loadingEl.style.display = 'block';
            tracksEl.innerHTML = '';
            
            const vlogTerms = ['upbeat', 'background music', 'vlog', 'ambient', 'chill', 'cinematic', 'happy'];
            const randomTerm = vlogTerms[Math.floor(Math.random() * vlogTerms.length)];
            
            try {
                const response = await fetch('/search_music', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: randomTerm,
                        page_size: 9
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.results.length > 0) {
                    musicTracks = data.results;
                    displayMusicSuggestions(data.results);
                    console.log(`Loaded ${data.results.length} ${randomTerm} music suggestions`);
                } else {
                    tracksEl.innerHTML = '<div style="padding: 20px; color: #ff6b6b; text-align: center;">No music suggestions available</div>';
                }
                
            } catch (error) {
                console.error('Music suggestions error:', error);
                tracksEl.innerHTML = '<div style="padding: 20px; color: #ff6b6b; text-align: center;">Failed to load music suggestions</div>';
            } finally {
                loadingEl.style.display = 'none';
            }
        }

        function toggleCustomSearch() {
            const searchSection = document.getElementById('customSearchSection');
            const isVisible = searchSection.style.display !== 'none';
            searchSection.style.display = isVisible ? 'none' : 'block';
            
            if (!isVisible) {
                document.getElementById('customMusicQuery').focus();
            }
        }

        async function searchCustomMusic() {
            const query = document.getElementById('customMusicQuery').value.trim();
            const tracksEl = document.getElementById('musicTracksHorizontal');
            
            if (!query) {
                alert('Please enter a search term');
                return;
            }
            
            tracksEl.innerHTML = '<div style="padding: 20px; color: #b0bec5; text-align: center;">Searching...</div>';
            
            try {
                const response = await fetch('/search_music', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: query,
                        page_size: 12
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.results.length > 0) {
                    musicTracks = data.results;
                    displayMusicSuggestions(data.results);
                    console.log(`Found ${data.results.length} tracks for "${query}"`);
                } else {
                    tracksEl.innerHTML = '<div style="padding: 20px; color: #ff6b6b; text-align: center;">No tracks found for "' + query + '"</div>';
                }
                
            } catch (error) {
                console.error('Custom music search error:', error);
                tracksEl.innerHTML = '<div style="padding: 20px; color: #ff6b6b; text-align: center;">Search failed. Please try again.</div>';
            }
        }

        function displayMusicSuggestions(tracks) {
            const container = document.getElementById('musicTracksHorizontal');
            container.innerHTML = '';
            
            tracks.forEach(track => {
                const trackCard = createMusicCard(track);
                container.appendChild(trackCard);
            });
        }

        function createMusicCard(track) {
            const div = document.createElement('div');
            div.className = 'music-card';
            
            const durationText = formatTime(track.duration);
            
            const displayTags = track.tags.slice(0, 2).join(', ');
            const tagsText = track.tags.length > 2 
                ? displayTags + '...'
                : displayTags;
            
            div.innerHTML = `
                <div class="music-card-header">
                    <div class="music-card-title">${track.name}</div>
                    <button class="music-card-play" onclick="previewTrackFromCard(event, '${track.id}')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    </button>
                </div>
                <div class="music-card-details">
                    <span class="music-card-duration">${durationText}</span>
                    <span>by ${track.username}</span>
                </div>
                <div class="music-card-tags">${tagsText}</div>
            `;
            
            div.addEventListener('click', (e) => {
                if (!e.target.closest('.music-card-play')) {
                    selectMusicTrack(track);
                }
            });
            
            return div;
        }

        async function selectMusicTrack(track) {
            console.log('Selecting music track:', track);
            
            isMusicLoading = true;
            updateExportButtonState();
            
            try {
                const response = await fetch('/download_music', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        track_id: track.id,
                        preview_url: track.preview_mp3 || track.preview_ogg
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    selectedMusicTrack = {
                        ...track,
                        local_path: data.music_path,
                        cached: data.cached
                    };
                    
                    displaySelectedMusic(selectedMusicTrack);
                    
                    document.querySelectorAll('.music-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    
                    document.querySelectorAll('.music-card-play').forEach(playBtn => {
                        if (playBtn.getAttribute('onclick').includes(track.id)) {
                            playBtn.closest('.music-card').classList.add('selected');
                        }
                    });
                    document.getElementById('selectedMusicTimeline').style.display = 'block';
                    
                    console.log('Music track selected and downloaded:', selectedMusicTrack);
                } else {
                    alert('Failed to download music: ' + (data.error || 'Unknown error'));
                }
                
            } catch (error) {
                console.error('Music selection error:', error);
                alert('Failed to select music track. Please try again.');
            } finally {
                isMusicLoading = false;
                updateExportButtonState();
            }
        }

        function displaySelectedMusic(track) {
            const container = document.getElementById('selectedTrackDetails');
            
            const displayName = track.name.length > 40 
                ? track.name.substring(0, 40) + '...'
                : track.name;
            
            container.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 4px;">${displayName}</div>
                <div style="font-size: 11px; color: #e0e0e0;">
                    ${formatTime(track.duration)} • by ${track.username} • Ready for export
                </div>
            `;
        }

        function previewTrackFromCard(event, trackId) {
            event.stopPropagation();
            
            const track = musicTracks.find(t => t.id == trackId);
            if (!track) return;
            
            const playButton = event.target;
            const wasPlaying = playButton.innerHTML.includes('M6 19h4V5H6v14zm8-14v14h4V5h-4z');
            
            if (musicAudio) {
                musicAudio.pause();
                musicAudio = null;
            }
            
            document.querySelectorAll('.music-card-play').forEach(btn => {
                btn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
                btn.style.background = 'transparent';
                btn.style.color = '#4B91F7';
            });
            
            if (wasPlaying) {
                return;
            }
            
            const previewUrl = track.preview_mp3 || track.preview_ogg;
            if (!previewUrl) {
                alert('No preview available for this track');
                return;
            }
            
            musicAudio = new Audio(previewUrl);
            musicAudio.volume = 0.7;
            
            playButton.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                </svg>
            `;
            playButton.style.background = 'rgba(0, 255, 136, 0.1)';
            playButton.style.color = '#00ff88';
            
            musicAudio.play().then(() => {
                console.log('Card preview started for:', track.name);
                
                setTimeout(() => {
                    if (musicAudio && !musicAudio.paused) {
                        musicAudio.pause();
                        musicAudio = null;
                        playButton.innerHTML = `
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M8 5v14l11-7z"/>
                            </svg>
                        `;
                        playButton.style.background = 'transparent';
                        playButton.style.color = '#4B91F7';
                        console.log('Card preview auto-stopped');
                    }
                }, 15000);
                
                musicAudio.addEventListener('ended', () => {
                    playButton.innerHTML = `
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                    `;
                    playButton.style.background = 'transparent';
                    playButton.style.color = '#4B91F7';
                    musicAudio = null;
                });
                
            }).catch(error => {
                console.error('Card preview failed:', error);
                playButton.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                `;
                playButton.style.background = 'transparent';
                playButton.style.color = '#4B91F7';
                alert('Failed to preview music');
            });
        }

        function previewMusic() {
            if (!selectedMusicTrack) return;
            
            if (musicAudio) {
                musicAudio.pause();
                musicAudio = null;
            }
            
            const previewUrl = selectedMusicTrack.preview_mp3 || selectedMusicTrack.preview_ogg;
            if (!previewUrl) {
                alert('No preview available for this track');
                return;
            }
            
            musicAudio = new Audio(previewUrl);
            musicAudio.volume = 1.0;
            
            musicAudio.play().then(() => {
                console.log('Music preview started');
                
                setTimeout(() => {
                    if (musicAudio && !musicAudio.paused) {
                        musicAudio.pause();
                        console.log('Music preview auto-stopped');
                    }
                }, 10000);
            }).catch(error => {
                console.error('Music preview failed:', error);
                alert('Failed to preview music');
            });
        }

        function clearSelectedMusic() {
            selectedMusicTrack = null;
            
            if (musicAudio) {
                musicAudio.pause();
                musicAudio = null;
            }
            
            document.getElementById('selectedMusicTimeline').style.display = 'none';
            document.querySelectorAll('.music-card').forEach(card => card.classList.remove('selected'));
            
            console.log('Selected music cleared');
        }

        async function goToExport() {
            if (shouldDisableExport()) {
                console.log('Export blocked: Processing in progress');
                showDetectionStatus('Please wait for AI detection to complete before exporting.');
                return;
            }
            
            if (segments.length === 0) {
                alert('Please select at least one segment to export');
                return;
            }

            if (!window.uploadedVideoData) {
                alert('Please upload a video first');
                return;
            }
            
            const exportMode = document.querySelector('input[name="exportMode"]:checked').value;
            const speedFactor = document.getElementById('speedSlider').value;
            
            // Get filter settings
            const filterSettings = getFilterSettings();

            const processingData = {
                video_id: window.uploadedVideoData.video_id,
                project_id: window.uploadedVideoData.project_id,
                processing_id: window.uploadedVideoData.processing_id, // Include processing ID if available
                segments: segments.map(seg => ({
                    start: seg.start,
                    end: seg.end,
                    room: seg.room
                })),
                export_mode: exportMode,
                speed_factor: parseFloat(speedFactor),
                quality: 'high', // Always use high quality for 1080p exports
                music_path: selectedMusicTrack ? selectedMusicTrack.local_path : undefined,
                music_volume: selectedMusicTrack ? 1.0 : undefined,
                filter_settings: filterSettings
            };

            console.log('Starting background video processing...', processingData);
            
            try {
                const response = await fetch('/start_video_processing', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(processingData)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    console.log('Background processing started successfully:', result.processing_id);
                    
                    const exportData = {
                        processing_id: result.processing_id,
                        video_id: window.uploadedVideoData.video_id,
                        video_data: window.uploadedVideoData,
                        segments: processingData.segments,
                        export_mode: exportMode,
                        speed_factor: parseFloat(speedFactor),
                        music_data: selectedMusicTrack ? {
                            track: selectedMusicTrack,
                            volume: 1.0
                        } : null,
                        processing_status: 'in_progress'
                    };

                    sessionStorage.setItem('exportData', JSON.stringify(exportData));
                    
                    // Maintain processing ID in URL when going to export page
                    if (window.uploadedVideoData && window.uploadedVideoData.processing_id) {
                        window.location.href = `/export/${window.uploadedVideoData.processing_id}`;
                    } else {
                        window.location.href = '/export';
                    }
                } else {
                    console.error('Background processing failed:', result.error);
                    alert('Failed to start video processing: ' + result.error);
                }
            } catch (error) {
                console.error('Failed to start background processing:', error);
                alert('Failed to start video processing: ' + error.message);
            }
        } 

        async function startAISegmentDetection() {
            const aiDetectBtn = document.getElementById('aiDetectBtn');
            
            const detectionInterval = Math.min(3.5, Math.max(1.0, videoDuration / 20));
            
            isDetectionLoading = true;
            updateExportButtonState();
            
            aiDetectBtn.disabled = true;
            aiDetectBtn.innerHTML = '<span style="font-size: 16px; margin-right: 8px;"></span>AI Detection in Progress...';
            
            showDetectionStatus('AI detection started...');
            
            try {
                const response = await fetch('/ai_segment_detect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        video_id: window.uploadedVideoData?.video_id,
                        project_id: window.uploadedVideoData?.project_id,
                        detection_interval: detectionInterval
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    pollForAISegments(result.detection_id);
                    
                } else {
                    throw new Error(result.error || 'AI detection failed');
                }
                
            } catch (error) {
                console.error('AI detection error:', error);
                showDetectionStatus('AI detection failed. Please try again.');
                
                isDetectionLoading = false;
                updateExportButtonState();
                
                aiDetectBtn.disabled = false;
                aiDetectBtn.innerHTML = '<span style="font-size: 14px; margin-right: 6px;"></span>Segment with AI';
            }
        }

        async function pollForAISegments(detectionId) {
            const maxAttempts = 300;
            let attempts = 0;
            let lastSegmentCount = 0;
            let lastSegmentHash = '';
            
            while (attempts < maxAttempts) {
                try {
                    const response = await fetch(`/check_detection_status/${detectionId}`);
                    
                    if (!response.ok) {
                        if (response.status === 404) {
                            console.log('Detection ID not found, assuming complete');
                            return;
                        }
                        throw new Error(`HTTP ${response.status}`);
                    }
                    
                    const result = await response.json();
                    console.log('Polling result:', result);
                    
                    if (result.status === 'completed') {
                        console.log('AI detection completed');
                        if (result.segments && result.segments.length > 0) {
                            updateAISegmentsInUI(result.segments);
                        }
                        
                        isDetectionLoading = false;
                        updateExportButtonState();
                        
                        const aiDetectBtn = document.getElementById('aiDetectBtn');
                        aiDetectBtn.disabled = false;
                        aiDetectBtn.innerHTML = '<span style="font-size: 14px; margin-right: 6px;"></span>Segment with AI';
                        
                        showDetectionStatus('AI detection completed!');
                        return;
                        
                    } else if (result.status === 'failed') {
                        isDetectionLoading = false;
                        updateExportButtonState();
                        
                        const aiDetectBtn = document.getElementById('aiDetectBtn');
                        aiDetectBtn.disabled = false;
                        aiDetectBtn.innerHTML = '<span style="font-size: 14px; margin-right: 6px;"></span>Segment with AI';
                        
                        throw new Error(result.error || 'AI detection failed');
                        
                    } else if (result.status === 'in_progress') {
                        if (result.segments && result.segments.length > 0) {
                            const segmentHash = JSON.stringify(result.segments.map(s => ({start: s.start, end: s.end, room: s.room})));
                            
                            if (segmentHash !== lastSegmentHash) {
                                console.log(`Segments updated: ${result.segments.length} total`);
                                updateAISegmentsInUI(result.segments);
                                lastSegmentHash = segmentHash;
                                
                                const latestSegment = result.segments[result.segments.length - 1];
                                if (latestSegment && latestSegment.temporary) {
                                    console.log('Temporary segment detected:', latestSegment);
                                }
                            }
                        }
                        
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        attempts++;
                    }
                    
                } catch (error) {
                    console.error('Polling error:', error);
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    attempts++;
                }
            }
            
            console.log('AI detection polling timed out');
            
            isDetectionLoading = false;
            updateExportButtonState();
            
            const aiDetectBtn = document.getElementById('aiDetectBtn');
            aiDetectBtn.disabled = false;
            aiDetectBtn.innerHTML = '<span style="font-size: 14px; margin-right: 6px;"></span>Segment with AI';
            
            showDetectionStatus('AI detection timed out. Please try again.');
        }

        function updateAISegmentsInUI(aiSegments) {
            console.log('updateAISegmentsInUI called with:', aiSegments);
            console.log('Current segments before update:', segments);
            
            segments = segments.filter(s => s.manual);
            
            aiSegments.forEach((aiSegment, index) => {
                console.log(`Processing AI segment ${index}:`, aiSegment);
                
                const newSegment = {
                    id: Date.now() + Math.random(),
                    start: aiSegment.start,
                    end: aiSegment.end,
                    duration: aiSegment.end - aiSegment.start,
                    room: aiSegment.room,
                    manual: false,
                    display_name: aiSegment.display_name || getRoomDisplayName(aiSegment.room),
                    editable: true,
                    temporary: aiSegment.temporary || false
                };
                
                segments.push(newSegment);
                console.log('Added AI segment:', newSegment);
                
                if (aiSegment.temporary) {
                    showDetectionFeedback(aiSegment.room, aiSegment.start);
                }
            });
            
            console.log('Segments after update:', segments);
            console.log('Calling updateSegmentsList and updateTimeline');
            
            updateSegmentsList();
            updateTimeline();
        }

        function showDetectionStatus(message) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: #2196f3;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                z-index: 1000;
                box-shadow: 0 4px 16px rgba(33, 150, 243, 0.4);
                animation: slideInFromTop 0.3s ease-out;
            `;
            notification.innerHTML = `${message}`;
            
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideInFromTop {
                    from { transform: translateX(-50%) translateY(-100%); opacity: 0; }
                    to { transform: translateX(-50%) translateY(0); opacity: 1; }
                }
                @keyframes slideOutToTop {
                    from { transform: translateX(-50%) translateY(0); opacity: 1; }
                    to { transform: translateX(-50%) translateY(-100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOutToTop 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 2000);
        }

        function showDetectionFeedback(room, time) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #4caf50;
                color: white;
                padding: 12px 16px;
                border-radius: 6px;
                font-size: 14px;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                animation: slideIn 0.3s ease-out;
            `;
            notification.innerHTML = `Detecting: ${getRoomDisplayName(room)} at ${formatTime(time)}s`;
            
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300);
            }, 3000);
        }

        function showAISegmentEditing() {
            const editingPanel = document.getElementById('aiSegmentEditing');
            const segmentsList = document.getElementById('aiSegmentsList');
            
            editingPanel.style.display = 'block';
            
            let html = '';
            window.aiSegments.forEach((segment, index) => {
                const displayName = getRoomDisplayName(segment.room) || segment.display_name || segment.room;
                
                html += `
                    <div class="ai-segment-item" style="margin-bottom: 12px; padding: 12px; background: rgba(255, 255, 255, 0.05); border-radius: 6px; border: 1px solid #333;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 12px; color: #aaa;">Segment ${index + 1}</div>
                            <div style="font-size: 11px; color: #888;">${formatTime(segment.start)} - ${formatTime(segment.end)}</div>
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <select class="ai-segment-room" data-index="${index}" style="flex: 1; padding: 6px 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 12px;">
                                <option value="kitchen" ${segment.room === 'kitchen' ? 'selected' : ''}>Kitchen</option>
                                <option value="bedroom" ${segment.room === 'bedroom' ? 'selected' : ''}>Bedroom</option>
                                <option value="bathroom" ${segment.room === 'bathroom' ? 'selected' : ''}>Bathroom</option>
                                <option value="living_room" ${segment.room === 'living_room' ? 'selected' : ''}>Living Room</option>
                                <option value="closet" ${segment.room === 'closet' ? 'selected' : ''}>Closet</option>
                                <option value="office" ${segment.room === 'office' ? 'selected' : ''}>Office</option>
                                <option value="dining_room" ${segment.room === 'dining_room' ? 'selected' : ''}>Dining Room</option>
                                <option value="balcony" ${segment.room === 'balcony' ? 'selected' : ''}>Balcony</option>
                            </select>
                            <input type="number" class="ai-segment-start" data-index="${index}" value="${segment.start.toFixed(1)}" step="0.1" min="0" max="${videoDuration}" style="width: 60px; padding: 6px 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 12px;">
                            <input type="number" class="ai-segment-end" data-index="${index}" value="${segment.end.toFixed(1)}" step="0.1" min="0" max="${videoDuration}" style="width: 60px; padding: 6px 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 12px;">
                        </div>
                    </div>
                `;
            });
            
            segmentsList.innerHTML = html;
        }

        function applyAISegmentChanges() {
            const segmentLength = parseFloat(document.getElementById('segmentLengthSlider').value);
            const aiSegments = window.aiSegments || [];
            
            segments = [];
            
            aiSegments.forEach((aiSegment, index) => {
                const roomSelect = document.querySelector(`.ai-segment-room[data-index="${index}"]`);
                const startInput = document.querySelector(`.ai-segment-start[data-index="${index}"]`);
                const endInput = document.querySelector(`.ai-segment-end[data-index="${index}"]`);
                
                const room = roomSelect ? roomSelect.value : aiSegment.room;
                const start = startInput ? parseFloat(startInput.value) : aiSegment.start;
                const end = endInput ? parseFloat(endInput.value) : aiSegment.end;
                
                if (end - start >= segmentLength) {
                                segments.push({
                                    id: Date.now() + Math.random(),
                        start: start,
                        end: end,
                        duration: end - start,
                        room: room,
                        manual: false,
                        display_name: getRoomDisplayName(room)
                    });
                }
            });
            
            updateSegmentsList();
            updateTimeline();
            
            document.getElementById('aiSegmentEditing').style.display = 'none';
            
            console.log(`Applied ${segments.length} AI segments with minimum length ${segmentLength}s`);
        }

        function getRoomDisplayName(room) {
            const roomLabels = {
                kitchen: 'Kitchen',
                bedroom: 'Bedroom',
                bathroom: 'Bathroom',
                living_room: 'Living Room',
                closet: 'Closet',
                office: 'Office',
                dining_room: 'Dining Room',
                balcony: 'Balcony'
            };
            return roomLabels[room] || room;
        }

        function editSegment(segmentId) {
            const segment = segments.find(s => s.id === segmentId);
            if (!segment) return;
            
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            `;
            
            modal.innerHTML = `
                <div style="background: #1a1a1a; border-radius: 8px; padding: 24px; min-width: 400px; border: 1px solid #333;">
                    <h3 style="margin: 0 0 20px 0; color: #fff;">Edit Segment</h3>
                    <div style="margin-bottom: 16px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 4px;">Room Type</label>
                        <select id="editRoomType" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff;">
                            <option value="kitchen" ${segment.room === 'kitchen' ? 'selected' : ''}>Kitchen</option>
                            <option value="bedroom" ${segment.room === 'bedroom' ? 'selected' : ''}>Bedroom</option>
                            <option value="bathroom" ${segment.room === 'bathroom' ? 'selected' : ''}>Bathroom</option>
                            <option value="living_room" ${segment.room === 'living_room' ? 'selected' : ''}>Living Room</option>
                            <option value="closet" ${segment.room === 'closet' ? 'selected' : ''}>Closet</option>
                            <option value="exterior" ${segment.room === 'exterior' ? 'selected' : ''}>Exterior</option>
                            <option value="office" ${segment.room === 'office' ? 'selected' : ''}>Office</option>
                            <option value="common_area" ${segment.room === 'common_area' ? 'selected' : ''}>Common Area</option>
                            <option value="dining_room" ${segment.room === 'dining_room' ? 'selected' : ''}>Dining Room</option>
                            <option value="balcony" ${segment.room === 'balcony' ? 'selected' : ''}>Balcony</option>
                        </select>
                    </div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div style="flex: 1;">
                            <label style="color: #888; font-size: 12px; display: block; margin-bottom: 4px;">Start Time (s)</label>
                            <input type="number" id="editStartTime" value="${segment.start.toFixed(1)}" step="0.1" min="0" max="${videoDuration}" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff;">
                        </div>
                        <div style="flex: 1;">
                            <label style="color: #888; font-size: 12px; display: block; margin-bottom: 4px;">End Time (s)</label>
                            <input type="number" id="editEndTime" value="${segment.end.toFixed(1)}" step="0.1" min="0" max="${videoDuration}" style="width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff;">
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; justify-content: flex-end;">
                        <button onclick="closeEditModal()" style="padding: 8px 16px; border-radius: 4px; border: 1px solid #444; background: #333; color: #fff; cursor: pointer;">Cancel</button>
                        <button onclick="saveSegmentEdit(${segmentId})" style="padding: 8px 16px; border-radius: 4px; border: none; background: #4caf50; color: #fff; cursor: pointer;">Save</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            window.currentEditModal = modal;
        }

        function closeEditModal() {
            if (window.currentEditModal) {
                document.body.removeChild(window.currentEditModal);
                window.currentEditModal = null;
            }
        }

        function saveSegmentEdit(segmentId) {
            const segment = segments.find(s => s.id === segmentId);
            if (!segment) return;
            
            const roomType = document.getElementById('editRoomType').value;
            const startTime = parseFloat(document.getElementById('editStartTime').value);
            const endTime = parseFloat(document.getElementById('editEndTime').value);
            
            if (isNaN(startTime) || isNaN(endTime) || startTime >= endTime) {
                alert('Please enter valid start and end times');
                return;
            }
            
            segment.room = roomType;
            segment.start = startTime;
            segment.end = endTime;
            segment.duration = endTime - startTime;
            segment.display_name = getRoomDisplayName(roomType);
            
            updateSegmentsList();
            updateTimeline();
            
            closeEditModal();
        }

        // Video Filter Functions
        let isPreviewEnabled = true;
        let currentPreset = 'none';

        function setupFilterControls() {
            // Setup individual filter sliders
            const sliders = ['brightnessSlider', 'contrastSlider', 'saturationSlider', 'hueSlider', 'blurSlider', 'sharpenSlider'];
            sliders.forEach(sliderId => {
                const slider = document.getElementById(sliderId);
                if (slider) {
                    slider.addEventListener('input', updateFilterSlider);
                }
            });

            // Setup preset buttons
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.addEventListener('click', applyFilterPreset);
            });

            // Initialize video element for preview
            const videoPlayer = document.getElementById('videoPlayer');
            if (videoPlayer) {
                videoPlayer.classList.add('filter-preview-active');
            }
        }

        function updateFilterSlider(event) {
            const slider = event.target;
            const sliderId = slider.id;
            const value = parseFloat(slider.value);
            
            // Update display value
            const valueId = sliderId.replace('Slider', 'Value');
            const valueSpan = document.getElementById(valueId);
            
            if (valueSpan) {
                let displayValue;
                switch (sliderId) {
                    case 'brightnessSlider':
                        displayValue = value.toString();
                        break;
                    case 'contrastSlider':
                        displayValue = (value / 100).toFixed(1);
                        break;
                    case 'saturationSlider':
                        displayValue = (value / 100).toFixed(1);
                        break;
                    case 'hueSlider':
                        displayValue = value + '°';
                        break;
                    case 'blurSlider':
                        displayValue = value.toString();
                        break;
                    case 'sharpenSlider':
                        displayValue = value.toString();
                        break;
                    default:
                        displayValue = value.toString();
                }
                valueSpan.textContent = displayValue;
            }

            // Clear active preset when manually adjusting
            clearActivePreset();
            
            // Apply live preview
            if (isPreviewEnabled) {
                applyLivePreview();
            }
        }

        function applyFilterPreset(presetName) {
            // Clear other active presets
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.classList.remove('active');
            });

            // Apply preset values to sliders - updated for backend-compatible ranges
            const presets = {
                warm: {
                    brightness: 0.15,   // Slightly brighter for warm effect
                    contrast: 1.1,       // Subtle contrast boost
                    saturation: 1.3,     // Enhanced saturation for warmth
                    hue: 10,             // Slight warm tint
                    blur: 0,             // No blur
                    sharpen: 0           // No sharpening
                },
                cool: {
                    brightness: 0.1,    // Slight brightness boost
                    contrast: 1.15,      // Moderate contrast
                    saturation: 1.1,     // Slight saturation boost
                    hue: -10,            // Cool tint
                    blur: 0,             // No blur
                    sharpen: 0           // No sharpening
                },
                vibrant: {
                    brightness: 0.1,    // Slight brightness boost
                    contrast: 1.3,       // Strong contrast for vibrancy
                    saturation: 1.5,     // High saturation for vibrant colors
                    hue: 0,              // No hue shift
                    blur: 0,             // No blur
                    sharpen: 0.5         // Light sharpening for crispness
                },
                cinematic: {
                    brightness: 0.05,   // Subtle brightness
                    contrast: 1.25,      // Strong contrast for cinematic look
                    saturation: 1.1,     // Slight saturation boost
                    hue: 5,              // Very slight warm tint
                    blur: 0,             // No blur
                    sharpen: 0.2         // Light sharpening
                },
                vintage: {
                    brightness: 0.2,    // Brighter for vintage look
                    contrast: 1.4,       // High contrast for vintage feel
                    saturation: 0.7,     // Reduced saturation for vintage look
                    hue: 25,             // Warm vintage tint
                    blur: 1.5,           // Light blur for vintage softness
                    sharpen: 0           // No sharpening for vintage softness
                }
            };

            if (presets[presetName]) {
                const values = presets[presetName];
                
                // Update slider values
                document.getElementById('brightnessSlider').value = values.brightness;
                document.getElementById('contrastSlider').value = values.contrast;
                document.getElementById('saturationSlider').value = values.saturation;
                document.getElementById('hueSlider').value = values.hue;
                document.getElementById('blurSlider').value = values.blur;
                document.getElementById('sharpenSlider').value = values.sharpen;

                // Update display values
                updateFilterValue('brightness', values.brightness);
                updateFilterValue('contrast', values.contrast);
                updateFilterValue('saturation', values.saturation);
                updateFilterValue('hue', values.hue);
                updateFilterValue('blur', values.blur);
                updateFilterValue('sharpen', values.sharpen);
                
                // Mark the preset as active
                const presetButtons = document.querySelectorAll('.preset-btn');
                presetButtons.forEach(btn => {
                    if (btn.textContent.toLowerCase() === presetName.toLowerCase()) {
                        btn.classList.add('active');
                    }
                });
                
                console.log(`Applied ${presetName} preset with backend-compatible values`);
            }
        }

        function clearActivePreset() {
            currentPreset = 'none';
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.classList.remove('active');
            });
        }

        function updateAllDisplayValues() {
            const sliders = ['brightnessSlider', 'contrastSlider', 'saturationSlider', 'hueSlider', 'blurSlider', 'sharpenSlider'];
            sliders.forEach(sliderId => {
                const slider = document.getElementById(sliderId);
                if (slider) {
                    updateFilterSlider({ target: slider });
                }
            });
        }

        function applyLivePreview() {
            const videoPlayer = document.getElementById('videoPlayer');
            if (!videoPlayer) {
                console.error('Video player not found');
                return;
            }

            // Check if video is ready
            if (videoPlayer.readyState < 2) {
                console.log('Video not ready, skipping filter application');
                return;
            }

            // Check if video is actually playing or has loaded
            if (videoPlayer.videoWidth === 0 || videoPlayer.videoHeight === 0) {
                console.log('Video dimensions not available, skipping filter application');
                return;
            }

            // Get current values from sliders
            const brightness = parseFloat(document.getElementById('brightnessSlider').value);
            const contrast = parseFloat(document.getElementById('contrastSlider').value);
            const saturation = parseFloat(document.getElementById('saturationSlider').value);
            const hue = parseInt(document.getElementById('hueSlider').value);
            const blur = parseInt(document.getElementById('blurSlider').value);
            const sharpen = parseInt(document.getElementById('sharpenSlider').value);

            console.log('Filter values:', { brightness, contrast, saturation, hue, blur, sharpen });

            // Build CSS filter string with proper calculations
            let filterString = '';
            
            // Only apply filters if they differ from default values (backend expectations)
            if (brightness !== 0.0) {
                filterString += `brightness(${1 + brightness}) `; // CSS brightness is 1-based
            }
            
            if (contrast !== 1.0) {
                filterString += `contrast(${contrast}) `;
            }
            
            if (saturation !== 1.0) {
                filterString += `saturate(${saturation}) `;
            }
            
            if (hue !== 0) {
                filterString += `hue-rotate(${hue}deg) `;
            }
            
            if (blur > 0) {
                filterString += `blur(${blur}px) `;
            }

            // Apply CSS filters with error handling
            try {
                if (filterString.trim() === '') {
                    // No filters to apply, clear any existing filters
                    videoPlayer.style.filter = '';
                    console.log('Cleared all filters');
                } else {
                    videoPlayer.style.filter = filterString.trim();
                    console.log('Applied filters successfully:', filterString.trim());
                }
            } catch (error) {
                console.error('Error applying filters:', error);
                // Reset filters if there's an error
                videoPlayer.style.filter = '';
            }
        }

        function toggleFilterPreview() {
            isPreviewEnabled = !isPreviewEnabled;
            const toggleBtn = document.getElementById('togglePreviewBtn');
            const videoPlayer = document.getElementById('videoPlayer');
            
            if (isPreviewEnabled) {
                toggleBtn.style.color = '#3b82f6';
                applyLivePreview();
            } else {
                toggleBtn.style.color = '#ccc';
                if (videoPlayer) {
                    videoPlayer.style.filter = '';
                }
            }
        }

        function resetAllFilters() {
            // Reset all sliders to default
            document.getElementById('brightnessSlider').value = 0;
            document.getElementById('contrastSlider').value = 100;
            document.getElementById('saturationSlider').value = 100;
            document.getElementById('hueSlider').value = 0;
            document.getElementById('blurSlider').value = 0;
            document.getElementById('sharpenSlider').value = 0;

            // Clear active preset
            clearActivePreset();
            
            // Update display values
            updateAllDisplayValues();
            
            // Reset video preview
            const videoPlayer = document.getElementById('videoPlayer');
            if (videoPlayer) {
                videoPlayer.style.filter = '';
            }
        }

        function getFilterSettings() {
            const settings = {
                preset: currentPreset,
                custom: {}
            };
            
            // Get current slider values - use the actual values, don't divide by 100
            const brightness = parseFloat(document.getElementById('brightnessSlider').value);
            const contrast = parseFloat(document.getElementById('contrastSlider').value);
            const saturation = parseFloat(document.getElementById('saturationSlider').value);
            const hue = parseInt(document.getElementById('hueSlider').value);
            const blur = parseInt(document.getElementById('blurSlider').value);
            const sharpen = parseInt(document.getElementById('sharpenSlider').value);
            
            // Include non-default values (matching backend expectations)
            if (brightness !== 0.0) settings.custom.brightness = brightness;
            if (contrast !== 1.0) settings.custom.contrast = contrast;
            if (saturation !== 1.0) settings.custom.saturation = saturation;
            if (hue !== 0) settings.custom.hue = hue;
            if (blur > 0) settings.custom.blur = blur;
            if (sharpen > 0) settings.custom.sharpness = sharpen;
            
            return settings;
        }

        // Load filter presets from backend (keeping for backend integration)
        async function loadFilterPresets() {
            try {
                const response = await fetch('/get_filter_presets');
                const result = await response.json();
                
                if (result.success && result.presets) {
                    console.log('Filter presets loaded from backend:', result.presets);
                    // Presets are now handled by preset buttons, but we keep this for backend sync
                } else {
                    console.error('Failed to load filter presets:', result.error);
                }
            } catch (error) {
                console.error('Error loading filter presets:', error);
            }
        }

        // Tab switching functionality
        function setupTabSwitching() {
            const tabButtons = document.querySelectorAll('.tab-btn');
            const tabContents = document.querySelectorAll('.tab-content');
            
            tabButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const targetTab = this.getAttribute('data-tab');
                    
                    // Remove active class from all tabs and contents
                    tabButtons.forEach(btn => btn.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    // Add active class to clicked tab and corresponding content
                    this.classList.add('active');
                    document.getElementById(`tab-${targetTab}`).classList.add('active');
                    
                    console.log(`Switched to ${targetTab} tab`);
                });
            });
        }

        // Initialize tab switching when DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            setupTabSwitching();
        });

        // Additional utility functions for the new interface
        function updateFilterValue(filterName, value) {
            const videoPlayer = document.getElementById('videoPlayer');
            if (!videoPlayer) return;
            
            // Update the corresponding slider value display
            const valueElement = document.getElementById(`${filterName}Value`);
            if (valueElement) {
                let displayValue;
                switch (filterName) {
                    case 'brightness':
                        displayValue = parseFloat(value).toFixed(1);
                        break;
                    case 'contrast':
                        displayValue = parseFloat(value).toFixed(1);
                        break;
                    case 'saturation':
                        displayValue = parseFloat(value).toFixed(1);
                        break;
                    case 'hue':
                        displayValue = value + '°';
                        break;
                    case 'blur':
                        displayValue = value;
                        break;
                    case 'sharpen':
                        displayValue = value;
                        break;
                    default:
                        displayValue = value;
                }
                valueElement.textContent = displayValue;
            }
            
            // Apply live preview
            applyLivePreview();
        }

        function resetFilters() {
            // Reset all filter sliders to default values (matching backend expectations)
            const defaultValues = {
                'brightnessSlider': 0.0,  // Backend expects 0.0 as default
                'contrastSlider': 1.0,    // Backend expects 1.0 as default
                'saturationSlider': 1.0,  // Backend expects 1.0 as default
                'hueSlider': 0,           // Backend expects 0 as default
                'blurSlider': 0,          // Backend expects 0 as default
                'sharpenSlider': 0        // Backend expects 0 as default
            };
            
            // Apply default values
            Object.keys(defaultValues).forEach(sliderId => {
                const slider = document.getElementById(sliderId);
                if (slider) {
                    slider.value = defaultValues[sliderId];
                    const filterName = sliderId.replace('Slider', '');
                    updateFilterValue(filterName, defaultValues[sliderId]);
                }
            });
            
            // Clear active preset
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            console.log('Filters reset to backend-compatible default values');
        }

        function previewFilters() {
            // Toggle filter preview mode
            const videoPlayer = document.getElementById('videoPlayer');
            const previewBtn = document.getElementById('previewFiltersBtn');
            
            if (videoPlayer) {
                if (videoPlayer.style.filter === '') {
                    // Apply current filter values
                    applyLivePreview();
                    previewBtn.style.color = '#3b82f6'; // Blue when active
                } else {
                    // Remove filters
                    videoPlayer.style.filter = '';
                    previewBtn.style.color = '#ccc'; // Grey when inactive
                }
            }
        }

        // Music-related functions
        function toggleCustomSearch() {
            const searchSection = document.getElementById('customSearchSection');
            if (searchSection) {
                const isVisible = searchSection.style.display !== 'none';
                searchSection.style.display = isVisible ? 'none' : 'block';
                
                if (!isVisible) {
                    const searchInput = document.getElementById('customMusicQuery');
                    if (searchInput) {
                        searchInput.focus();
                    }
                }
            }
        }



        // Export mode functions
        function handleExportModeChange(event) {
            const speedSettings = document.getElementById('speedSettings');
            if (event.target.value === 'speedup') {
                speedSettings.style.display = 'block';
            } else {
                speedSettings.style.display = 'none';
            }
        }

        // Initialize all the new functionality
        document.addEventListener('DOMContentLoaded', function() {
            // Setup export mode change listeners
            document.querySelectorAll('input[name="exportMode"]').forEach(radio => {
                radio.addEventListener('change', handleExportModeChange);
            });
            
            // Initialize speed settings visibility based on default selection
            const defaultMode = document.querySelector('input[name="exportMode"]:checked');
            if (defaultMode) {
                handleExportModeChange({ target: defaultMode });
            }
            
            // Setup speed slider
            const speedSlider = document.getElementById('speedSlider');
            if (speedSlider) {
                speedSlider.addEventListener('input', function() {
                    const speedValue = document.getElementById('speedValue');
                    if (speedValue) {
                        speedValue.textContent = this.value + 'x';
                    }
                });
            }
            
            // Setup segment length slider
            const segmentLengthSlider = document.getElementById('segmentLengthSlider');
            if (segmentLengthSlider) {
                segmentLengthSlider.addEventListener('input', function() {
                    const segmentLengthValue = document.getElementById('segmentLengthValue');
                    if (segmentLengthValue) {
                        segmentLengthValue.textContent = this.value + 's';
                    }
                });
            }
            
            console.log('New interface functionality initialized');
        });

        function testFilterCompatibility() {
            const videoPlayer = document.getElementById('videoPlayer');
            if (!videoPlayer) return false;
            
            // Test if CSS filters are supported
            try {
                // Apply a simple test filter
                videoPlayer.style.filter = 'brightness(1.1)';
                const testFilter = videoPlayer.style.filter;
                videoPlayer.style.filter = '';
                
                console.log('CSS filters are supported:', testFilter);
                return true;
            } catch (error) {
                console.error('CSS filters not supported:', error);
                return false;
            }
        }

        function initializeFilters() {
            // Test filter compatibility first
            if (!testFilterCompatibility()) {
                console.warn('CSS filters not supported, disabling filter functionality');
                return;
            }
            
            // Set default values for all sliders - matching backend expectations
            const defaultValues = {
                'brightnessSlider': 0.0,  // Backend expects 0.0 as default
                'contrastSlider': 1.0,    // Backend expects 1.0 as default
                'saturationSlider': 1.0,  // Backend expects 1.0 as default
                'hueSlider': 0,           // Backend expects 0 as default
                'blurSlider': 0,          // Backend expects 0 as default
                'sharpenSlider': 0        // Backend expects 0 as default
            };
            
            // Apply default values
            Object.keys(defaultValues).forEach(sliderId => {
                const slider = document.getElementById(sliderId);
                if (slider) {
                    slider.value = defaultValues[sliderId];
                    const filterName = sliderId.replace('Slider', '');
                    updateFilterValue(filterName, defaultValues[sliderId]);
                }
            });
            
            // Clear any existing filters
            const videoPlayer = document.getElementById('videoPlayer');
            if (videoPlayer) {
                videoPlayer.style.filter = '';
            }
            
            console.log('Filters initialized with backend-compatible default values');
        }

// Mobile tab dropdown functionality (moved to global scope)
function toggleTabDropdown() {
    console.log('toggleTabDropdown called');
    const dropdown = document.getElementById('tabDropdown');
    const arrow = document.querySelector('.dropdown-arrow');
    
    console.log('Dropdown element:', dropdown);
    console.log('Arrow element:', arrow);
    
    if (dropdown && arrow) {
        if (dropdown.classList.contains('open')) {
            console.log('Closing dropdown');
            dropdown.classList.remove('open');
            arrow.classList.remove('open');
        } else {
            console.log('Opening dropdown');
            dropdown.classList.add('open');
            arrow.classList.add('open');
        }
    } else {
        console.log('Dropdown or arrow element not found');
    }
}

function selectMobileTab(tabId, tabName) {
    // Update the current tab name
    const currentTabName = document.querySelector('.current-tab-name');
    if (currentTabName) {
        currentTabName.textContent = tabName;
    }
    
    // Close the dropdown
    const dropdown = document.getElementById('tabDropdown');
    const arrow = document.querySelector('.dropdown-arrow');
    if (dropdown) dropdown.classList.remove('open');
    if (arrow) arrow.classList.remove('open');
    
    // Update active state in dropdown
    document.querySelectorAll('.tab-option').forEach(option => {
        option.classList.remove('active');
    });
    const selectedOption = document.querySelector(`.tab-option[data-tab="${tabId}"]`);
    if (selectedOption) {
        selectedOption.classList.add('active');
    }
    
    // Switch the actual tab content (reuse existing switchToTab function)
    if (typeof switchToTab === 'function') {
        switchToTab(tabId);
    } else {
        // Fallback tab switching
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const targetContent = document.getElementById(`tab-${tabId}`);
        const targetBtn = document.querySelector(`[data-tab="${tabId}"]`);
        
        if (targetContent) targetContent.classList.add('active');
        if (targetBtn) targetBtn.classList.add('active');
    }
}

        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            const tabSelector = document.querySelector('.mobile-tab-selector');
            if (tabSelector && !tabSelector.contains(e.target)) {
                const dropdown = document.getElementById('tabDropdown');
                const arrow = document.querySelector('.dropdown-arrow');
                if (dropdown) {
                    dropdown.classList.remove('open');
                }
                if (arrow) {
                    arrow.classList.remove('open');
                }
            }
        });

// Timeline toggle functionality for mobile
function toggleTimeline() {
    const timelineContent = document.getElementById('timelineContent');
    const timelineContainer = document.getElementById('timelineContainer');
    const toggleIcon = document.querySelector('.timeline-toggle-icon');
    
    console.log('toggleTimeline called');
    console.log('timelineContent:', timelineContent);
    console.log('timelineContainer:', timelineContainer);
    console.log('toggleIcon:', toggleIcon);
    
    if (timelineContent && toggleIcon && timelineContainer) {
        if (timelineContent.classList.contains('collapsed')) {
            // Expand timeline
            console.log('Expanding timeline');
            timelineContent.classList.remove('collapsed');
            timelineContainer.classList.remove('collapsed');
            toggleIcon.classList.remove('collapsed');
            console.log('Icon classes after expand:', toggleIcon.className);
        } else {
            // Collapse timeline
            console.log('Collapsing timeline');
            timelineContent.classList.add('collapsed');
            timelineContainer.classList.add('collapsed');
            toggleIcon.classList.add('collapsed');
            console.log('Icon classes after collapse:', toggleIcon.className);
        }
    } else {
        console.log('One or more elements not found');
    }
}

// Initialize timeline state on mobile
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on mobile and collapse timeline by default
    if (window.innerWidth <= 768) {
        const timelineContent = document.getElementById('timelineContent');
        const timelineContainer = document.getElementById('timelineContainer');
        const toggleIcon = document.querySelector('.timeline-toggle-icon');
        
        if (timelineContent && toggleIcon && timelineContainer) {
            timelineContent.classList.add('collapsed');
            timelineContainer.classList.add('collapsed');
            toggleIcon.classList.add('collapsed');
        }
    }
});

