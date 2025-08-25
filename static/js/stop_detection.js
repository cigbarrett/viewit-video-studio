// Stop AI detection when page is refreshed or navigated away
window.addEventListener('beforeunload', function() {
    // Get project ID from stored video data
    const projectId = window.uploadedVideoData?.project_id;
    const requestBody = projectId ? { project_id: projectId } : {};
    
    // Use sendBeacon for reliable delivery even during page unload
    fetch('/stop_ai_detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        keepalive: true
    }).catch(() => {
        // Fallback to sendBeacon if fetch fails
        navigator.sendBeacon('/stop_ai_detection', JSON.stringify(requestBody));
    });
});

// Also stop detection when navigating to a different page
window.addEventListener('pagehide', function() {
    // Get project ID from stored video data
    const projectId = window.uploadedVideoData?.project_id;
    const requestBody = projectId ? { project_id: projectId } : {};
    
    fetch('/stop_ai_detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody),
        keepalive: true
    }).catch(() => {
        navigator.sendBeacon('/stop_ai_detection', JSON.stringify(requestBody));
    });
});
