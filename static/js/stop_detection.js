// Stop AI detection when page is refreshed or navigated away
window.addEventListener('beforeunload', function() {
    // Use sendBeacon for reliable delivery even during page unload
    fetch('/stop_ai_detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({}),
        keepalive: true
    }).catch(() => {
        // Fallback to sendBeacon if fetch fails
        navigator.sendBeacon('/stop_ai_detection', JSON.stringify({}));
    });
});

// Also stop detection when navigating to a different page
window.addEventListener('pagehide', function() {
    fetch('/stop_ai_detection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({}),
        keepalive: true
    }).catch(() => {
        navigator.sendBeacon('/stop_ai_detection', JSON.stringify({}));
    });
});
