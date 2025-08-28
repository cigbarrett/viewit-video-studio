// Enhanced Tutorial System for Video Editor
class TutorialSystem {
    constructor() {
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.spotlight = null;
        this.tooltip = null;
        this.tutorialCompleted = localStorage.getItem('tutorialCompleted') === 'true';
        this.tutorialMode = localStorage.getItem('tutorialMode') || 'beginner'; // beginner, intermediate, advanced
        
        // Simplified tutorial steps - shorter and mobile-friendly
        this.steps = [
            {
                target: '.video-player-container',
                title: 'Video Preview',
                description: 'Your video plays here. Use Space to play/pause, arrows to skip 5 seconds.',
                position: 'right',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('segments');
                }
            },
            {
                target: '.ai-detect-btn',
                title: 'AI Room Detection',
                description: 'Click here to automatically detect rooms in your video. AI will create segments for each room.',
                position: 'bottom',
                highlightPadding: 12,
                action: () => {
                    this.switchToTab('segments');
                },
                isImportant: true
            },
            {
                target: '.manual-selection-section',
                title: 'Create a Segment',
                description: 'Let\'s create a segment manually. Press I to set start point, O for end point, then click Add Segment.',
                position: 'bottom',
                highlightPadding: 12,
                interactive: true,
                interactiveSteps: [
                    {
                        instruction: 'Press I key to set the start point',
                        checkAction: () => this.checkKeyPress('i'),
                        successMessage: 'Start point set!'
                    },
                    {
                        instruction: 'Press O key to set the end point',
                        checkAction: () => this.checkKeyPress('o'),
                        successMessage: 'End point set!'
                    },
                    {
                        instruction: 'Click the Add Segment button',
                        target: '#addSegmentBtn',
                        successMessage: 'Segment added!'
                    }
                ]
            },
            {
                target: '[data-tab="filters"]',
                title: 'Video Filters',
                description: 'Apply filters to enhance your video. Try Cinematic, Warm, or Cool presets.',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('filters');
                }
            },
            {
                target: '[data-tab="music"]',
                title: 'Background Music',
                description: 'Add music to your tour. Click play buttons to preview tracks.',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('music');
                }
            },
            {
                target: '#exportButton',
                title: 'Create Tour',
                description: 'Ready to export? Click here to create your final property tour video.',
                position: 'bottom',
                highlightPadding: 8,
                action: () => {
                    this.switchToTab('segments');
                },
                isImportant: true
            }
        ];


    }

    init() {
        this.createTutorialButton();
        
        // Auto-start tutorial for new users
        if (!this.tutorialCompleted) {
            setTimeout(() => {
                this.startTutorial();
            }, 1500);
        }
    }

    createTutorialButton() {
        // Enhanced help button with more options
        const existingButton = document.querySelector('.tutorial-help-btn-inline');
        if (existingButton) {
            existingButton.innerHTML = '?';
            existingButton.title = 'Take a guided tour or get help';
            existingButton.onclick = () => this.showHelpMenu();
        }
    }

    showHelpMenu() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const menu = document.createElement('div');
        menu.className = 'help-menu';
        menu.style.cssText = `
            background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
            border: 2px solid #4B91F7;
            border-radius: 12px;
            padding: 20px;
            max-width: 400px;
            width: 90%;
            position: relative;
        `;

        menu.innerHTML = `
            <div style="position: relative;">
                <button id="closeHelpBtn" style="
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background: transparent;
                    border: none;
                    color: #b0bec5;
                    width: 24px;
                    height: 24px;
                    font-size: 16px;
                    cursor: pointer;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1;
                ">
                    ×
                </button>
                
                <h3 style="color: #ffffff; margin: 0 0 15px 0; text-align: center;">Help</h3>
                
                <div style="margin-bottom: 15px;">
                    <button id="startTutorialBtn" style="
                        width: 100%;
                        background: linear-gradient(135deg, #0A3696, #1e4db7);
                        border: none;
                        color: #ffffff;
                        padding: 12px;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        margin-bottom: 8px;
                    ">
                        Start Tutorial
                    </button>
                    
                    <button id="showQuickTipsBtn" style="
                        width: 100%;
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        color: #ffffff;
                        padding: 12px;
                        border-radius: 6px;
                        font-size: 14px;
                        cursor: pointer;
                    ">
                        Quick Tips
                    </button>
                </div>
            </div>
        `;

        overlay.appendChild(menu);
        document.body.appendChild(overlay);
        
        // Add event listeners to buttons
        const closeBtn = menu.querySelector('#closeHelpBtn');
        const startTutorialBtn = menu.querySelector('#startTutorialBtn');
        const showQuickTipsBtn = menu.querySelector('#showQuickTipsBtn');
        
        closeBtn.addEventListener('click', () => {
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
        });
        
        startTutorialBtn.addEventListener('click', () => {
            tutorial.startTutorial();
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
        });
        
        showQuickTipsBtn.addEventListener('click', () => {
            tutorial.showQuickTips();
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
        });
        
        // Close on outside click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        });
        
        // Close on ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    showQuickTips() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const tips = document.createElement('div');
        tips.className = 'quick-tips';
        tips.style.cssText = `
            background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
            border: 2px solid #00ff88;
            border-radius: 12px;
            padding: 20px;
            max-width: 450px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        `;

        tips.innerHTML = `
            <div style="position: relative;">
                <button id="closeTipsBtn" style="
                    position: absolute;
                    top: -10px;
                    right: -10px;
                    background: transparent;
                    border: none;
                    color: #b0bec5;
                    width: 24px;
                    height: 24px;
                    font-size: 16px;
                    cursor: pointer;
                    font-weight: bold;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1;
                ">
                    ×
                </button>
                
                <h3 style="color: #ffffff; margin: 0 0 15px 0; text-align: center;">Quick Tips</h3>
                
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #00ff88; margin: 0 0 8px 0;">Video Controls</h4>
                    <div style="color: #b0bec5; font-size: 13px; line-height: 1.5;">
                        <div><strong>Space</strong> - Play/Pause</div>
                        <div><strong>← →</strong> - Skip 5 seconds</div>
                        <div><strong>Click timeline</strong> - Jump to time</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #00ff88; margin: 0 0 8px 0;">Segments</h4>
                    <div style="color: #b0bec5; font-size: 13px; line-height: 1.5;">
                        <div><strong>I</strong> - Set start point</div>
                        <div><strong>O</strong> - Set end point</div>
                        <div><strong>Enter</strong> - Add segment</div>
                        <div><strong>Drag timeline</strong> - Refine segment edges</div>
                        <div><strong>Click segment</strong> - Edit room label</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <h4 style="color: #00ff88; margin: 0 0 8px 0;">Workflow Tips</h4>
                    <div style="color: #b0bec5; font-size: 13px; line-height: 1.5;">
                        <div>• Use AI detection first, then refine manually</div>
                        <div>• Check for missed short segments (1-2 seconds)</div>
                        <div>• Drag timeline edges to adjust segment timing</div>
                        <div>• Click segment labels to change room types</div>
                    </div>
                </div>
            </div>
        `;

        overlay.appendChild(tips);
        document.body.appendChild(overlay);
        
        // Add event listener to close button
        const closeBtn = tips.querySelector('#closeTipsBtn');
        closeBtn.addEventListener('click', () => {
            overlay.remove();
            document.removeEventListener('keydown', escHandler);
        });
        
        // Close on outside click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        });
        
        // Close on ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }



    startTutorial() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentStep = 0;
        this.interactiveStepIndex = 0;
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
        
        // Add resize listener for mobile orientation changes
        this.resizeHandler = () => {
            if (this.isActive) {
                const step = this.steps[this.currentStep];
                if (step) {
                    this.positionSpotlight(step);
                    this.updateTooltip(step, this.currentStep);
                }
            }
        };
        window.addEventListener('resize', this.resizeHandler);
        
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
        this.interactiveStepIndex = 0;
        const step = this.steps[stepIndex];
        
        // Execute step action if any
        if (step.action) {
            step.action();
        }
        
        // Wait for any tab transitions
        setTimeout(() => {
            this.positionSpotlight(step);
            this.updateTooltip(step, stepIndex);
            
            // Start interactive step if needed
            if (step.interactive) {
                this.startInteractiveStep(step);
            }
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
        
        // Mobile adjustments
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            // Ensure spotlight is visible on mobile
            const viewportHeight = window.innerHeight;
            const spotlightBottom = rect.top + rect.height + padding;
            
            // If spotlight would be cut off at bottom, adjust position
            if (spotlightBottom > viewportHeight - 100) {
                const newTop = Math.max(10, viewportHeight - rect.height - padding - 100);
                this.spotlight.style.top = (newTop + scrollTop) + 'px';
            }
            
            // Ensure spotlight doesn't go off-screen horizontally
            const viewportWidth = window.innerWidth;
            if (rect.left < 10) {
                this.spotlight.style.left = (10 + scrollLeft) + 'px';
                this.spotlight.style.width = (Math.min(rect.width + padding * 2, viewportWidth - 20)) + 'px';
            }
        }
        
        // Add pulse effect for important steps
        if (step.isImportant) {
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
        
        // Mobile adjustments
        const isMobile = window.innerWidth <= 768;
        
        // Calculate position with scroll offset
        let position = step.position || 'bottom';
        let left, top;
        
        if (isMobile) {
            // On mobile, always position tooltip at bottom center
            position = 'bottom';
            left = window.innerWidth / 2 - 150;
            top = rect.bottom + scrollTop + 20;
            this.tooltip.classList.add('position-bottom');
        } else {
            switch (position) {
                case 'top':
                    left = rect.left + scrollLeft + rect.width / 2 - 150;
                    top = rect.top + scrollTop - 220;
                    this.tooltip.classList.add('position-top');
                    break;
                case 'bottom':
                    left = rect.left + scrollLeft + rect.width / 2 - 150;
                    top = rect.bottom + scrollTop + 20;
                    this.tooltip.classList.add('position-bottom');
                    break;
                case 'left':
                    left = rect.left + scrollLeft - 320 - 20;
                    top = rect.top + scrollTop + rect.height / 2 - 100;
                    this.tooltip.classList.add('position-left');
                    break;
                case 'right':
                    left = rect.right + scrollLeft + 20;
                    top = rect.top + scrollTop + rect.height / 2 - 100;
                    this.tooltip.classList.add('position-right');
                    break;
            }
        }
        
        // Ensure tooltip stays within viewport
        const viewport = {
            width: window.innerWidth + scrollLeft,
            height: window.innerHeight + scrollTop
        };
        
        if (isMobile) {
            // Mobile-specific viewport constraints
            left = Math.max(10 + scrollLeft, Math.min(left, viewport.width - 310));
            top = Math.max(10 + scrollTop, Math.min(top, viewport.height - 250));
        } else {
            left = Math.max(20 + scrollLeft, Math.min(left, viewport.width - 340));
            top = Math.max(20 + scrollTop, Math.min(top, viewport.height - 300));
        }
        
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
                        Previous
                    </button>
                    <button class="tutorial-btn primary" onclick="tutorial.nextStep()">
                        ${isLast ? 'Finish' : 'Next'}
                    </button>
                </div>
                <button class="tutorial-skip" onclick="tutorial.closeTutorial()">Skip</button>
            </div>
            
            <div class="tutorial-progress">
                <div class="tutorial-progress-fill" style="width: ${progress}%"></div>
            </div>
        `;
    }

    setupTooltipEventListeners() {
        // Event listeners are handled via onclick attributes in the HTML
    }

    nextStep() {
        // Remove interactive listeners when moving to next step
        this.removeInteractiveListeners();
        
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        } else {
            this.completeTutorial();
        }
    }

    previousStep() {
        // Remove interactive listeners when moving to previous step
        this.removeInteractiveListeners();
        
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
        
        // Show enhanced completion message
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
            padding: 20px;
            text-align: center;
            z-index: 10000;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
            max-width: 350px;
            width: 90%;
        `;
        
        message.innerHTML = `
            <h3 style="color: #ffffff; margin: 0 0 10px 0; font-size: 18px;">Tutorial Complete!</h3>
            <p style="color: #b0bec5; margin: 0 0 15px 0; font-size: 13px; line-height: 1.4;">
                You're ready to create property tours! Try AI detection, apply filters, and add music.
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
            ">
                Start Creating
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
        this.currentStep = 0;
        this.interactiveStepIndex = 0;
        document.body.classList.remove('tutorial-active');
        
        // Remove interactive listeners
        this.removeInteractiveListeners();
        
        // Remove scroll listener
        if (this.scrollHandler) {
            window.removeEventListener('scroll', this.scrollHandler);
            this.scrollHandler = null;
        }
        
        // Remove resize listener
        if (this.resizeHandler) {
            window.removeEventListener('resize', this.resizeHandler);
            this.resizeHandler = null;
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

    // Interactive step functionality
    startInteractiveStep(step) {
        if (!step.interactiveSteps || step.interactiveSteps.length === 0) return;
        
        this.currentInteractiveStep = step.interactiveSteps[0];
        this.showInteractiveInstruction();
        this.setupInteractiveListeners();
    }

    showInteractiveInstruction() {
        if (!this.currentInteractiveStep) return;
        
        const instruction = this.currentInteractiveStep.instruction;
        const tooltip = document.querySelector('.tutorial-tooltip');
        if (tooltip) {
            const descriptionEl = tooltip.querySelector('.tutorial-description');
            if (descriptionEl) {
                descriptionEl.innerHTML = `
                    <div style="margin-bottom: 10px;">${instruction}</div>
                    <div style="color: #4B91F7; font-weight: 600; font-size: 12px;">Click or press the key when ready</div>
                `;
            }
        }
    }

    setupInteractiveListeners() {
        // Remove existing listeners
        this.removeInteractiveListeners();
        
        if (this.currentInteractiveStep.checkAction) {
            // For key press actions
            this.keyListener = (e) => {
                if (e.key.toLowerCase() === this.currentInteractiveStep.checkAction()) {
                    this.completeInteractiveStep();
                }
            };
            document.addEventListener('keydown', this.keyListener);
        }
        
        if (this.currentInteractiveStep.target) {
            // For click actions
            const target = document.querySelector(this.currentInteractiveStep.target);
            if (target) {
                this.clickListener = () => {
                    this.completeInteractiveStep();
                };
                target.addEventListener('click', this.clickListener);
            }
        }
    }

    removeInteractiveListeners() {
        if (this.keyListener) {
            document.removeEventListener('keydown', this.keyListener);
            this.keyListener = null;
        }
        if (this.clickListener) {
            const target = document.querySelector(this.currentInteractiveStep?.target);
            if (target) {
                target.removeEventListener('click', this.clickListener);
            }
            this.clickListener = null;
        }
    }

    completeInteractiveStep() {
        this.removeInteractiveListeners();
        
        // Show success message
        if (this.currentInteractiveStep.successMessage) {
            this.showSuccessMessage(this.currentInteractiveStep.successMessage);
        }
        
        // Move to next interactive step or complete
        const step = this.steps[this.currentStep];
        this.interactiveStepIndex++;
        
        if (this.interactiveStepIndex < step.interactiveSteps.length) {
            // Next interactive step
            this.currentInteractiveStep = step.interactiveSteps[this.interactiveStepIndex];
            setTimeout(() => {
                this.showInteractiveInstruction();
                this.setupInteractiveListeners();
            }, 1000);
        } else {
            // All interactive steps complete
            setTimeout(() => {
                this.nextStep();
            }, 1500);
        }
    }

    showSuccessMessage(message) {
        const successEl = document.createElement('div');
        successEl.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0, 255, 136, 0.9);
            color: #000;
            padding: 12px 20px;
            border-radius: 6px;
            font-weight: 600;
            z-index: 10001;
            animation: fadeInOut 2s ease-in-out;
        `;
        successEl.textContent = message;
        
        // Add CSS animation
        if (!document.querySelector('#tutorial-animations')) {
            const style = document.createElement('style');
            style.id = 'tutorial-animations';
            style.textContent = `
                @keyframes fadeInOut {
                    0% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
                    20% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
                    80% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
                    100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(successEl);
        setTimeout(() => successEl.remove(), 2000);
    }

    checkKeyPress(expectedKey) {
        return expectedKey;
    }

    // Simple contextual help
    showContextualHelp(context) {
        const helpData = {
            'segments': {
                title: 'Segments',
                content: 'Click "Segment with AI" to automatically detect rooms. Use I/O keys to manually create segments.'
            },
            'filters': {
                title: 'Filters',
                content: 'Try Cinematic for luxury properties, Warm for cozy homes, or Cool for modern apartments.'
            },
            'music': {
                title: 'Music',
                content: 'Click play buttons to preview tracks. Choose music that matches your property style.'
            },
            'export': {
                title: 'Export',
                content: 'Use Cinematic Mode for longer videos, Walkthrough Mode for smaller units.'
            }
        };

        const help = helpData[context];
        if (!help) return;

        const helpModal = document.createElement('div');
        helpModal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
            border: 2px solid #4B91F7;
            border-radius: 12px;
            padding: 20px;
            z-index: 10000;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
            max-width: 350px;
            width: 90%;
        `;

        helpModal.innerHTML = `
            <h3 style="color: #ffffff; margin: 0 0 15px 0; text-align: center;">${help.title}</h3>
            <p style="color: #b0bec5; font-size: 14px; line-height: 1.5; margin: 0 0 20px 0;">
                ${help.content}
            </p>
            <button onclick="this.parentElement.remove()" style="
                width: 100%;
                background: linear-gradient(135deg, #0A3696, #1e4db7);
                border: none;
                color: #ffffff;
                padding: 10px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
            ">
                Got it!
            </button>
        `;

        document.body.appendChild(helpModal);
        
        helpModal.addEventListener('click', (e) => {
            if (e.target === helpModal) {
                helpModal.remove();
            }
        });
    }
}

// Initialize tutorial system
let tutorial;

document.addEventListener('DOMContentLoaded', function() {
    tutorial = new TutorialSystem();
    tutorial.init();
});

// Enhanced keyboard shortcuts for tutorial
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