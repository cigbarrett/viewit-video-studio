// Tutorial System for Video Editor
class TutorialSystem {
    constructor() {
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        this.tutorialCompleted = localStorage.getItem('tutorialCompleted') === 'true';
        
        // Define tutorial steps with targets, positions, and content
        this.steps = [
            {
                target: '.video-player-container',
                title: 'Welcome to Video Editor! 🎬',
                description: 'This is your video preview area. Your uploaded video will play here, and you can see filters and effects applied in real-time.',
                position: 'right',
                highlightPadding: 8,
                action: () => {
                    // Switch to segments tab if not already there
                    this.switchToTab('segments');
                }
            },
            {
                target: '.editor-tabs',
                title: 'Feature Tabs 📑',
                description: 'These tabs give you access to different editing features: Segments for selecting parts of your video, Filters for visual effects, Music for background audio, and Export for final output.',
                position: 'bottom',
                highlightPadding: 8
            },
            {
                target: '.ai-detect-btn',
                title: 'AI Segment Detection 🤖',
                description: 'Click this magic button to let AI automatically detect different rooms and areas in your property tour video. It\'ll create segments for each room transition!',
                position: 'bottom',
                highlightPadding: 12,
                action: () => {
                    this.switchToTab('segments');
                }
            },
            {
                target: '.shortcuts-collapsible',
                title: 'Keyboard Shortcuts ⌨️',
                description: 'Click here to see all available keyboard shortcuts. These can speed up your editing workflow significantly - try Space for play/pause or I/O for setting in/out points.',
                position: 'bottom',
                highlightPadding: 8
            },
            {
                target: '.manual-selection-section',
                title: 'Manual Segment Creation ✂️',
                description: 'Use these controls to manually create segments. Set start/end times, choose the room type, and add segments to build your property tour.',
                position: 'bottom',
                highlightPadding: 12
            },
            {
                target: '[data-tab="filters"]',
                title: 'Video Filters Tab 🎨',
                description: 'Switch to this tab to enhance your video with filters. Adjust brightness, contrast, saturation, and apply preset looks like "Cinematic" or "Warm".',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('filters');
                }
            },
            {
                target: '[data-tab="music"]',
                title: 'Background Music Tab 🎵',
                description: 'Add background music to your property tour. Browse suggested tracks or search for specific moods and genres to enhance the viewing experience.',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('music');
                }
            },
            {
                target: '[data-tab="export"]',
                title: 'Export Settings Tab 📤',
                description: 'Configure your final video output. Choose between "Segments Only" (remove transitions) or "Speed up transitions" (keep all footage but speed up walking).',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('export');
                }
            },
            {
                target: '#exportButton',
                title: 'Export Your Video 🚀',
                description: 'Once you\'ve created segments and applied your desired effects, click here to export your final property tour video. High-quality 1080p output guaranteed!',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('segments');
                }
            }
        ];
    }

    init() {
        this.createTutorialButton();
        
        // Auto-start tutorial for new users
        if (!this.tutorialCompleted) {
            // Wait for page to be fully loaded
            setTimeout(() => {
                this.startTutorial();
            }, 1500);
        }
    }

    createTutorialButton() {
        // The help button is now inline in the header, no need to create it dynamically
        // This method is kept for compatibility but doesn't do anything
    }

    startTutorial() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentStep = 0;
        document.body.classList.add('tutorial-active');
        
        this.createOverlay();
        this.showStep(0);
        
        // Add scroll listener to reposition tutorial elements
        this.scrollHandler = () => {
            if (this.isActive) {
                const step = this.steps[this.currentStep];
                if (step) {
                    this.positionSpotlight(step);
                    this.updateTooltip(step, this.currentStep);
                }
            }
        };
        window.addEventListener('scroll', this.scrollHandler);
        
        // Pause any playing video
        const video = document.getElementById('videoPlayer');
        if (video && !video.paused) {
            video.pause();
        }
    }

    createOverlay() {
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'tutorial-overlay';
        
        // Create spotlight
        this.spotlight = document.createElement('div');
        this.spotlight.className = 'tutorial-spotlight';
        
        // Create tooltip
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tutorial-tooltip';
        
        document.body.appendChild(this.overlay);
        document.body.appendChild(this.spotlight);
        document.body.appendChild(this.tooltip);
        
        // Close tutorial when clicking overlay (but not spotlight or tooltip)
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.closeTutorial();
            }
        });
    }

    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) return;
        
        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];
        
        // Execute step action if any
        if (step.action) {
            step.action();
        }
        
        // Wait for any tab transitions
        setTimeout(() => {
            this.positionSpotlight(step);
            this.updateTooltip(step, stepIndex);
        }, step.action ? 300 : 0);
    }

    positionSpotlight(step) {
        const target = document.querySelector(step.target);
        if (!target) {
            console.warn(`Tutorial target not found: ${step.target}`);
            return;
        }

        const rect = target.getBoundingClientRect();
        const padding = step.highlightPadding || 8;
        
        // Account for page scroll
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        
        // Add highlight class to target
        document.querySelectorAll('.tutorial-highlighted').forEach(el => {
            el.classList.remove('tutorial-highlighted');
        });
        target.classList.add('tutorial-highlighted');
        
        // Position spotlight with scroll offset
        this.spotlight.style.left = (rect.left + scrollLeft - padding) + 'px';
        this.spotlight.style.top = (rect.top + scrollTop - padding) + 'px';
        this.spotlight.style.width = (rect.width + padding * 2) + 'px';
        this.spotlight.style.height = (rect.height + padding * 2) + 'px';
        
        // Add pulse effect for important steps
        if (step.target === '.ai-detect-btn' || step.target === '#exportButton') {
            this.spotlight.classList.add('pulse');
        } else {
            this.spotlight.classList.remove('pulse');
        }
    }

    updateTooltip(step, stepIndex) {
        const target = document.querySelector(step.target);
        if (!target) return;

        const rect = target.getBoundingClientRect();
        
        // Account for page scroll
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        
        // Remove old position classes
        this.tooltip.className = 'tutorial-tooltip';
        
        // Calculate position with scroll offset
        let position = step.position || 'bottom';
        let left, top;
        
        switch (position) {
            case 'top':
                left = rect.left + scrollLeft + rect.width / 2 - 150; // Assuming tooltip width ~300px
                top = rect.top + scrollTop - 220; // Above the element
                this.tooltip.classList.add('position-top');
                break;
            case 'bottom':
                left = rect.left + scrollLeft + rect.width / 2 - 150;
                top = rect.bottom + scrollTop + 20; // Below the element
                this.tooltip.classList.add('position-bottom');
                break;
            case 'left':
                left = rect.left + scrollLeft - 320 - 20; // To the left
                top = rect.top + scrollTop + rect.height / 2 - 100;
                this.tooltip.classList.add('position-left');
                break;
            case 'right':
                left = rect.right + scrollLeft + 20; // To the right
                top = rect.top + scrollTop + rect.height / 2 - 100;
                this.tooltip.classList.add('position-right');
                break;
        }
        
        // Ensure tooltip stays within viewport (considering scroll)
        const viewport = {
            width: window.innerWidth + scrollLeft,
            height: window.innerHeight + scrollTop
        };
        
        left = Math.max(20 + scrollLeft, Math.min(left, viewport.width - 340));
        top = Math.max(20 + scrollTop, Math.min(top, viewport.height - 300));
        
        this.tooltip.style.left = left + 'px';
        this.tooltip.style.top = top + 'px';
        
        // Update tooltip content
        this.tooltip.innerHTML = this.createTooltipContent(step, stepIndex);
        
        // Add event listeners for navigation
        this.setupTooltipEventListeners();
    }

    createTooltipContent(step, stepIndex) {
        const isFirst = stepIndex === 0;
        const isLast = stepIndex === this.steps.length - 1;
        const progress = ((stepIndex + 1) / this.steps.length) * 100;
        
        return `
            <div class="tutorial-header">
                <div class="tutorial-step-counter">Step ${stepIndex + 1} of ${this.steps.length}</div>
                <button class="tutorial-close" onclick="tutorial.closeTutorial()">×</button>
            </div>
            
            <h3 class="tutorial-title">${step.title}</h3>
            <p class="tutorial-description">${step.description}</p>
            
            <div class="tutorial-controls">
                <div class="tutorial-nav">
                    <button class="tutorial-btn" onclick="tutorial.previousStep()" ${isFirst ? 'disabled' : ''}>
                        ← Previous
                    </button>
                    <button class="tutorial-btn primary" onclick="tutorial.nextStep()">
                        ${isLast ? 'Finish' : 'Next'} ${isLast ? '✓' : '→'}
                    </button>
                </div>
                <button class="tutorial-skip" onclick="tutorial.closeTutorial()">Skip Tour</button>
            </div>
            
            <div class="tutorial-progress">
                <div class="tutorial-progress-fill" style="width: ${progress}%"></div>
            </div>
        `;
    }

    setupTooltipEventListeners() {
        // Event listeners are handled via onclick attributes in the HTML
        // This method can be used for additional event setup if needed
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        } else {
            this.completeTutorial();
        }
    }

    previousStep() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    switchToTab(tabName) {
        // Find and click the tab
        const tabButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (tabButton && !tabButton.classList.contains('active')) {
            tabButton.click();
        }
    }

    completeTutorial() {
        localStorage.setItem('tutorialCompleted', 'true');
        this.tutorialCompleted = true;
        this.closeTutorial();
        
        // Show completion message
        this.showCompletionMessage();
    }

    showCompletionMessage() {
        const message = document.createElement('div');
        message.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
            border: 2px solid #00ff88;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            z-index: 10000;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
            max-width: 400px;
        `;
        
        message.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 16px;">🎉</div>
            <h3 style="color: #ffffff; margin: 0 0 12px 0; font-size: 20px;">Tutorial Complete!</h3>
            <p style="color: #b0bec5; margin: 0 0 20px 0; font-size: 14px;">
                You're now ready to create amazing walkthroughs! 
                Start by adding segments or letting AI detect them automatically.
            </p>
            <button onclick="this.parentElement.remove()" style="
                background: linear-gradient(135deg, #0A3696, #1e4db7);
                border: none;
                color: #ffffff;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            ">
                Start Editing
            </button>
        `;
        
        document.body.appendChild(message);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (message.parentElement) {
                message.remove();
            }
        }, 5000);
    }

    closeTutorial() {
        this.isActive = false;
        document.body.classList.remove('tutorial-active');
        
        // Remove scroll listener
        if (this.scrollHandler) {
            window.removeEventListener('scroll', this.scrollHandler);
            this.scrollHandler = null;
        }
        
        // Remove tutorial elements
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
        if (this.spotlight) {
            this.spotlight.remove();
            this.spotlight = null;
        }
        if (this.tooltip) {
            this.tooltip.remove();
            this.tooltip = null;
        }
        
        // Remove highlight classes
        document.querySelectorAll('.tutorial-highlighted').forEach(el => {
            el.classList.remove('tutorial-highlighted');
        });
    }

    resetTutorial() {
        localStorage.removeItem('tutorialCompleted');
        this.tutorialCompleted = false;
        this.startTutorial();
    }
}

// Initialize tutorial system
let tutorial;

document.addEventListener('DOMContentLoaded', function() {
    tutorial = new TutorialSystem();
    tutorial.init();
});

// Keyboard shortcuts for tutorial
document.addEventListener('keydown', function(e) {
    if (!tutorial || !tutorial.isActive) return;
    
    if (e.key === 'Escape') {
        tutorial.closeTutorial();
    } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault();
        tutorial.nextStep();
    } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        tutorial.previousStep();
    }
});