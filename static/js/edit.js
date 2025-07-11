        // Global variables
        let video = null;
        let videoDuration = 0;
        let segments = [];
        let selectionMode = 'click';
        
        // Music-related variables
        let musicTracks = [];
        let selectedMusicTrack = null;
        let musicAudio = null;  // For music preview
        
        // Export state tracking
        let isMusicLoading = false;
        let detectingSegments = 0;  // Count of segments currently being detected

        // Export button management
        function shouldDisableExport() {
            return isMusicLoading || detectingSegments > 0;
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

        // Initialize the application
        document.addEventListener('DOMContentLoaded', function() {
            // Load video data from sessionStorage
            const videoData = sessionStorage.getItem('uploadedVideoData');
            if (videoData) {
                window.uploadedVideoData = JSON.parse(videoData);
                console.log('Loaded video data:', window.uploadedVideoData);
                videoDuration = window.uploadedVideoData.duration;
                initializeVideoPlayer();
            } else {
                alert('No video data found. Please upload a video first.');
                window.location.href = '/';
            }
            
            setupEventListeners();
            setupGlobalKeyboardShortcuts();
            setupMusicControls();
            loadMusicSuggestions(); // Auto-load vlog music suggestions
            
            // Initialize export button state
            updateExportButtonState();
        });

        function initializeVideoPlayer() {
            video = document.getElementById('videoPlayer');
            
            // Set the video source to the uploaded video
            video.src = `/${window.uploadedVideoData.video_path}`;
            
            video.addEventListener('loadedmetadata', function() {
                console.log('Video loaded:', video.src);
                console.log('Video duration:', video.duration);
                // Update videoDuration with actual video duration if different
                if (Math.abs(video.duration - videoDuration) > 1) {
                    videoDuration = video.duration;
                    createTimelineMarkers();
                }
            });
            
            video.addEventListener('error', function(e) {
                console.error('Video loading error:', e);
                console.error('Video src:', video.src);
                alert('Failed to load video. Please try uploading again.');
            });
            
            video.addEventListener('timeupdate', updateTimeDisplay);
            video.addEventListener('timeupdate', updatePlayhead);
            
            // Keep play/pause button in sync with video state
            video.addEventListener('play', function() {
                document.getElementById('playButton').innerHTML = '❚❚';
            });
            video.addEventListener('pause', function() {
                document.getElementById('playButton').innerHTML = '▶';
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
            document.getElementById('timeline').addEventListener('click', handleTimelineClick);
            
            // Volume control
            document.getElementById('volumeSlider').addEventListener('input', function() {
                if (video) {
                    video.volume = this.value;
                }
            });

            // Export mode changes
            document.querySelectorAll('input[name="exportMode"]').forEach(radio => {
                radio.addEventListener('change', handleExportModeChange);
            });
            
            // Speed slider
            document.getElementById('speedSlider').addEventListener('input', function() {
                document.getElementById('speedValue').textContent = this.value + 'x';
            });
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
                // Only apply shortcuts when not typing in inputs
                const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
                
                if (!video) return; // No video loaded
                
                switch(e.key) {
                    case ' ': // Spacebar - Play/Pause
                        if (!isTyping) {
                            e.preventDefault();
                            togglePlay();
                        }
                        break;
                        
                    case 'ArrowLeft': // Left Arrow - Skip backward
                        if (!isTyping) {
                            e.preventDefault();
                            skipBackward();
                        }
                        break;
                        
                    case 'ArrowRight': // Right Arrow - Skip forward
                        if (!isTyping) {
                            e.preventDefault();
                            skipForward();
                        }
                        break;
                        
                    case 'i': // I - Set start time (In point)
                    case 'I':
                        if (!isTyping) {
                            e.preventDefault();
                            setInPoint();
                        }
                        break;
                        
                    case 'o': // O - Set end time (Out point)
                    case 'O':
                        if (!isTyping) {
                            e.preventDefault();
                            setOutPoint();
                        }
                        break;
                        
                    case 'Enter': // Enter - Add segment
                        if (!isTyping) {
                            e.preventDefault();
                            const startTime = parseFloat(document.getElementById('startTime').value);
                            const endTime = parseFloat(document.getElementById('endTime').value);
                            if (!isNaN(startTime) && !isNaN(endTime)) {
                                addSegment();
                            }
                        }
                        break;
                        
                    case 'e': // E - Export Video
                    case 'E':
                        if (!isTyping) {
                            e.preventDefault();
                            goToExport();
                        }
                        break;
                        
                    case '1': // Number keys to switch modes
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
                        
                    case 'Escape': // Escape - Clear selection
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
                video.currentTime = Math.min(video.duration, video.currentTime + 5);
                console.log(`Skipped forward to ${video.currentTime.toFixed(1)}s`);
            }
        }

        function previewSegment() {
            const startTime = parseFloat(document.getElementById('startTime').value);
            const endTime = parseFloat(document.getElementById('endTime').value);
            
            if (!isNaN(startTime) && !isNaN(endTime) && video) {
                video.currentTime = startTime;
                video.play();
                
                // Stop at end time
                const stopPreview = () => {
                    if (video.currentTime >= endTime) {
                        video.pause();
                        video.removeEventListener('timeupdate', stopPreview);
                        console.log(`Preview complete: ${startTime.toFixed(1)}s - ${endTime.toFixed(1)}s`);
                    }
                };
                
                video.addEventListener('timeupdate', stopPreview);
                console.log(`Previewing segment: ${startTime.toFixed(1)}s - ${endTime.toFixed(1)}s`);
            } else {
                console.log('Invalid segment times for preview');
            }
        }

        function togglePlay() {
            if (video && video.paused) {
                video.play();
                document.getElementById('playButton').innerHTML = '❚❚';
            } else if (video) {
                video.pause();
                document.getElementById('playButton').innerHTML = '▶';
            }
        }

        function skipBackward() {
            if (video) video.currentTime = Math.max(0, video.currentTime - 5);
        }

        function skipForward() {
            if (video) video.currentTime = Math.min(videoDuration, video.currentTime + 5);
        }

        function toggleMute() {
            if (video) {
                video.muted = !video.muted;
                document.getElementById('muteButton').innerHTML = video.muted ? '✕' : '♪';
            }
        }

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

        async function addSegment() {
            const startTime = parseFloat(document.getElementById('startTime').value);
            const endTime = parseFloat(document.getElementById('endTime').value);
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
            
            // Create initial segment
            const segment = {
                id: Date.now(),
                start: startTime,
                end: endTime,
                duration: endTime - startTime,
                room: roomType === 'auto' ? null : roomType,
                detecting: roomType === 'auto'  // Flag to show loading state
            };
            
            segments.push(segment);
            console.log('Segment added:', segment);
            
            // Update UI immediately to show the segment
            updateSegmentsList();
            updateTimeline();
            
            // Clear inputs
            document.getElementById('startTime').value = '';
            document.getElementById('endTime').value = '';
            
            // If auto-detection is selected, detect the label immediately
            if (roomType === 'auto') {
                try {
                    console.log('🔍 Starting real-time auto-detection...');
                    detectingSegments++;
                    updateExportButtonState();
                    
                    const response = await fetch('/detect_segment_label', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            video_id: window.uploadedVideoData?.video_id,
                            start_time: startTime,
                            end_time: endTime
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        // Update the segment with detected label
                        const segmentIndex = segments.findIndex(s => s.id === segment.id);
                        if (segmentIndex !== -1) {
                            segments[segmentIndex].room = result.detected_label;
                            segments[segmentIndex].display_name = result.display_name;
                            segments[segmentIndex].detecting = false;
                            segments[segmentIndex].confidence = result.confidence;
                            
                            console.log(`✅ Auto-detected: "${result.display_name}" (${result.confidence} confidence)`);
                        
                        // Update UI with detected label
                        updateSegmentsList();
                        updateTimeline();
                        
                        // Update export button state
                        detectingSegments--;
                        updateExportButtonState();
                        }
                    } else {
                        // Handle detection failure
                        const segmentIndex = segments.findIndex(s => s.id === segment.id);
                        if (segmentIndex !== -1) {
                            segments[segmentIndex].room = result.fallback_label || 'unlabeled';
                            segments[segmentIndex].display_name = result.fallback_display || 'Unlabeled';
                            segments[segmentIndex].detecting = false;
                            segments[segmentIndex].confidence = 'failed';
                            
                            console.log(`❌ Auto-detection failed: ${result.error}`);
                        updateSegmentsList();
                        updateTimeline();
                        
                        // Update export button state
                        detectingSegments--;
                        updateExportButtonState();
                        }
                    }
                } catch (error) {
                    console.error('Auto-detection error:', error);
                    
                    // Handle network/fetch errors
                    const segmentIndex = segments.findIndex(s => s.id === segment.id);
                    if (segmentIndex !== -1) {
                        segments[segmentIndex].room = 'unlabeled';
                        segments[segmentIndex].display_name = 'Unlabeled (Detection Failed)';
                        segments[segmentIndex].detecting = false;
                        segments[segmentIndex].confidence = 'error';
                        
                        updateSegmentsList();
                        updateTimeline();
                        
                        // Update export button state
                        detectingSegments--;
                        updateExportButtonState();
                    }
                }
            }
            
            console.log('Total segments:', segments.length);
        }

        function updateSegmentsList() {
            const container = document.getElementById('segmentsList');
            
            if (segments.length === 0) {
                container.innerHTML = '<p style="color: #90a4ae; text-align: center; padding: 20px;">No segments selected yet</p>';
                document.getElementById('totalDuration').textContent = 'Total: 0.0s';
                return;
            }
            
            let html = '';
            let totalDuration = 0;
            
            segments.sort((a, b) => a.start - b.start);
            
            segments.forEach((segment, index) => {
                totalDuration += segment.duration;
                const roomLabels = {
                    kitchen: 'Kitchen',
                    bedroom: 'Bedroom',
                    bathroom: 'Bathroom',
                    living_room: 'Living Room',
                    closet: 'Closet',
                    exterior: 'Exterior',
                    office: 'Office',
                    common_area: 'Common Area',
                    dining_room: 'Dining Room',
                    balcony: 'Balcony',
                    unlabeled: 'Unlabeled'
                };
                
                let roomDisplayName, statusIcon, statusColor, titleClass;
                
                if (segment.detecting) {
                    // Show loading state during detection
                    roomDisplayName = 'Detecting...';
                    statusIcon = '⏳';
                    statusColor = '#ff9800';
                    titleClass = 'detecting';
                } else if (segment.display_name) {
                    // Use the detected display name
                    roomDisplayName = segment.display_name;
                    if (segment.confidence === 'high') {
                        statusIcon = '✅';
                        statusColor = '#4caf50';
                    } else if (segment.confidence === 'low') {
                        statusIcon = '❓';
                        statusColor = '#ff9800';
                    } else if (segment.confidence === 'failed' || segment.confidence === 'error') {
                        statusIcon = '❌';
                        statusColor = '#f44336';
                    } else {
                        statusIcon = '';
                        statusColor = '#ffffff';
                    }
                    titleClass = 'detected';
                } else if (segment.room) {
                    // Manual selection
                    roomDisplayName = roomLabels[segment.room] || segment.room.replace('_', ' ');
                    statusIcon = '👤';
                    statusColor = '#2196f3';
                    titleClass = 'manual';
                } else {
                    // Fallback
                    roomDisplayName = 'Auto-detect';
                    statusIcon = '';
                    statusColor = '#90a4ae';
                    titleClass = '';
                }
                
                html += `
                    <div class="segment-item ${segment.detecting ? 'detecting' : ''}">
                        <div class="segment-info">
                            <div class="segment-title ${titleClass}">
                                <span class="status-icon" style="color: ${statusColor}; margin-right: 6px;"></span>
                                ${roomDisplayName}
                            </div>
                            <div class="segment-details">
                                ${formatTime(segment.start)} - ${formatTime(segment.end)} 
                                (${segment.duration.toFixed(1)}s)
                            </div>
                        </div>
                        <button class="btn btn-danger" onclick="removeSegment(${segment.id})" style="padding: 6px 12px; font-size: 12px;">
                            ×
                        </button>
                    </div>
                `;
            });
            
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
                
                div.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (video) video.currentTime = segment.start;
                });
                
                track.appendChild(div);
            });
        }

        function previewSegment() {
            const startTime = parseFloat(document.getElementById('startTime').value);
            const endTime = parseFloat(document.getElementById('endTime').value);
            
            if (isNaN(startTime) || isNaN(endTime)) {
                alert('Please set valid start and end times');
                return;
            }
            
            if (video) {
                video.currentTime = startTime;
                video.play();
                
                // Stop at end time
                const checkTime = () => {
                    if (video.currentTime >= endTime) {
                        video.pause();
                    } else {
                        requestAnimationFrame(checkTime);
                    }
                };
                requestAnimationFrame(checkTime);
            }
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
                // Don't complete to 100% here - let the actual API response handle completion
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
            document.getElementById('playhead').style.left = percent + '%';
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

        // ========== MUSIC FUNCTIONALITY ==========
        
        function setupMusicControls() {
            // Setup Enter key for custom music search
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
            
            // Random vlog-style search terms
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
                        page_size: 8
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
            
            // Format duration
            const durationText = formatTime(track.duration);
            
            // Format tags (show only first 2-3)
            const displayTags = track.tags.slice(0, 2).join(', ');
            const tagsText = track.tags.length > 2 
                ? displayTags + '...'
                : displayTags;
            
            div.innerHTML = `
                <div class="music-card-header">
                    <div class="music-card-title">${track.name}</div>
                    <button class="music-card-play" onclick="previewTrackFromCard(event, '${track.id}')">
                        ▶
                    </button>
                </div>
                <div class="music-card-details">
                    <span class="music-card-duration">${durationText}</span>
                    <span>by ${track.username}</span>
                </div>
                <div class="music-card-tags">${tagsText}</div>
            `;
            
            // Add click handler for selecting track (but not on play button)
            div.addEventListener('click', (e) => {
                if (!e.target.closest('.music-card-play')) {
                    selectMusicTrack(track);
                }
            });
            
            return div;
        }

        async function selectMusicTrack(track) {
            console.log('Selecting music track:', track);
            
            // Set music loading state
            isMusicLoading = true;
            updateExportButtonState();
            
            try {
                // Download the track
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
                    
                    // Update UI - highlight selected card and show selected music section
                    document.querySelectorAll('.music-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    
                    // Find and highlight the selected card by track id in play button
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
                // Clear music loading state
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

        // Preview track from individual card play button
        function previewTrackFromCard(event, trackId) {
            event.stopPropagation(); // Prevent card selection
            
            const track = musicTracks.find(t => t.id == trackId);
            if (!track) return;
            
            const playButton = event.target;
            const wasPlaying = playButton.textContent === '⏸';
            
            // Stop any currently playing preview
            if (musicAudio) {
                musicAudio.pause();
                musicAudio = null;
            }
            
            // Reset all play buttons
            document.querySelectorAll('.music-card-play').forEach(btn => {
                btn.textContent = '▶';
                btn.style.background = 'linear-gradient(145deg, #0A3696, #1e4db7)';
            });
            
            // If we were playing this track, just stop
            if (wasPlaying) {
                return;
            }
            
            const previewUrl = track.preview_mp3 || track.preview_ogg;
            if (!previewUrl) {
                alert('No preview available for this track');
                return;
            }
            
            musicAudio = new Audio(previewUrl);
            musicAudio.volume = 0.7; // Default preview volume
            
            // Update button to show playing state
            playButton.textContent = '⏸';
            playButton.style.background = 'linear-gradient(145deg, #00ff88, #00cc6a)';
            
            musicAudio.play().then(() => {
                console.log('Card preview started for:', track.name);
                
                // Auto-stop after 15 seconds
                setTimeout(() => {
                    if (musicAudio && !musicAudio.paused) {
                        musicAudio.pause();
                        musicAudio = null;
                        playButton.textContent = '▶';
                        playButton.style.background = 'linear-gradient(145deg, #0A3696, #1e4db7)';
                        console.log('Card preview auto-stopped');
                    }
                }, 15000);
                
                // Handle when preview ends naturally
                musicAudio.addEventListener('ended', () => {
                    playButton.textContent = '▶';
                    playButton.style.background = 'linear-gradient(145deg, #0A3696, #1e4db7)';
                    musicAudio = null;
                });
                
            }).catch(error => {
                console.error('Card preview failed:', error);
                playButton.textContent = '▶';
                playButton.style.background = 'linear-gradient(145deg, #0A3696, #1e4db7)';
                alert('Failed to preview music');
            });
        }

        function previewMusic() {
            if (!selectedMusicTrack) return;
            
            // Stop any currently playing preview
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
                
                // Auto-stop after 10 seconds
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
            
            // Stop music preview if playing
            if (musicAudio) {
                musicAudio.pause();
                musicAudio = null;
            }
            
            // Update UI
            document.getElementById('selectedMusicTimeline').style.display = 'none';
            document.querySelectorAll('.music-card').forEach(card => card.classList.remove('selected'));
            
            console.log('Selected music cleared');
        }

        // Go to export page with segment data
        async function goToExport() {
            // Check if export is currently disabled
            if (shouldDisableExport()) {
                console.log('Export blocked: Processing in progress');
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
            
            // Get export mode and speed factor
            const exportMode = document.querySelector('input[name="exportMode"]:checked').value;
            const speedFactor = document.getElementById('speedSlider').value;
            
            // Prepare processing data
            const processingData = {
                video_id: window.uploadedVideoData.video_id,
                segments: segments.map(seg => ({
                    start: seg.start,
                    end: seg.end,
                    room: seg.room
                })),
                export_mode: exportMode,
                speed_factor: parseFloat(speedFactor),
                quality: exportMode === 'speedup' ? 'standard' : 'high',
                music_path: selectedMusicTrack ? selectedMusicTrack.local_path : undefined,
                music_volume: selectedMusicTrack ? 1.0 : undefined
            };

            // Start background processing and wait for processing ID
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
                    
                    // Prepare export data for the export page with correct processing ID
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

                    // Store data for export page
                    sessionStorage.setItem('exportData', JSON.stringify(exportData));
                    
                    // Redirect to export page
                    window.location.href = '/export';
                } else {
                    console.error('Background processing failed:', result.error);
                    alert('Failed to start video processing: ' + result.error);
                }
            } catch (error) {
                console.error('Failed to start background processing:', error);
                alert('Failed to start video processing: ' + error.message);
            }
        } 