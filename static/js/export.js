        // Global variables
        let exportData = null;
        let qrPath = null;

        // Initialize the application
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Export page loaded');
            console.log('Current URL:', window.location.pathname);
            
            // Try to get processing ID from URL
            const pathParts = window.location.pathname.split('/');
            const processingId = pathParts[pathParts.length - 1];
            console.log('Path parts:', pathParts);
            console.log('Processing ID from URL:', processingId);
            
            // First check if we have export data in session storage
            const storedData = sessionStorage.getItem('exportData');
            if (storedData) {
                exportData = JSON.parse(storedData);
                console.log('Loaded export data from session storage:', exportData);
                
                // If we have a processing ID in the URL, add it to the export data
                if (processingId && processingId !== 'export') {
                    exportData.processing_id = processingId;
                    console.log('Updated export data with processing ID from URL:', processingId);
                }
            } else if (processingId && processingId !== 'export') {
                // If no session data but we have a processing ID in URL, create minimal export data
                exportData = {
                    processing_id: processingId,
                    processing_status: 'unknown'
                };
                console.log('Created minimal export data from URL processing ID:', processingId);
            } else {
                alert('No export data found. Please go back to the edit page.');
                window.location.href = '/edit';
            }
            
            setupEventListeners();
        });

        function setupEventListeners() {
            // DLD verification
            document.getElementById('verifyListingBtn').addEventListener('click', verifyListing);
            
            // Custom file upload
            setupCustomFileUpload();
        }





        function verifyListing() {
            const tradeLicense = document.getElementById('tradeLicenseInput').value.trim();
            const listingNumber = document.getElementById('listingNumberInput').value.trim();

            if (!tradeLicense || !listingNumber) {
                showStatus('Please enter trade license and listing number', 'error');
                return;
            }

            const statusEl = document.getElementById('verifyStatus');
            statusEl.style.display = 'flex';
            statusEl.className = 'verification-status loading';
            statusEl.textContent = 'Verifying listing...';

            fetch('/verify_listing', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    trade_license_number: tradeLicense,
                    listing_number: listingNumber,
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    qrPath = data.qr_path;
                    showStatus('Listing verified - QR code ready for export', 'success');
                    console.log('Listing verified, QR:', qrPath);
                } else {
                    qrPath = null;
                    showStatus('❌ ' + (data.error || 'Verification failed'), 'error');
                }
            })
            .catch(err => {
                qrPath = null;
                showStatus('❌ ' + err.message, 'error');
            });
        }

        function showStatus(message, type) {
            const statusEl = document.getElementById('verifyStatus');
            statusEl.style.display = 'flex';
            statusEl.className = `verification-status ${type}`;
            statusEl.textContent = message;
        }

        function goBack() {
            // Keep the export data in session storage for when they return
            if (exportData && exportData.processing_id) {
                window.location.href = `/edit/${exportData.processing_id}`;
            } else {
                window.location.href = '/edit';
            }
        }

        async function createTour() {
            if (!exportData) {
                alert('No export data available');
                return;
            }

            const agentName = document.getElementById('agentName').value.trim();
            const agentPhone = document.getElementById('agentPhone').value.trim();

            // Validate phone number format only if provided
            const phonePattern = /^\+971[0-9]{8,9}$/;
            if (agentPhone && !phonePattern.test(agentPhone)) {
                alert('Please enter a valid UAE phone number in format +971XXXXXXXXX');
                return;
            }

            // Gather property details
            const beds = document.getElementById('beds').value.trim();
            const baths = document.getElementById('baths').value.trim();
            const sqft = document.getElementById('sqft').value.trim();

            // Read agency logo (if provided) as base64
            let logoBase64 = null;
            const logoInput = document.getElementById('agencyLogo');
            console.log('Logo input element:', logoInput);
            console.log('Logo files:', logoInput?.files);
            if (logoInput && logoInput.files && logoInput.files[0]) {
                console.log('Logo file selected:', logoInput.files[0].name, logoInput.files[0].size);
                logoBase64 = await toBase64(logoInput.files[0]);
                console.log('Logo converted to base64, length:', logoBase64?.length);
            } else {
                console.log('No logo file selected');
            }

            // Show loading overlay
            showLoadingOverlay();
            
            const requestData = {
                processing_id: exportData.processing_id,
                qr_path: qrPath || undefined,
                agent_name: agentName || undefined,
                agent_phone: agentPhone || undefined,
                agency_logo_data: logoBase64 || undefined,
                beds: beds || undefined,
                baths: baths || undefined,
                sqft: sqft || undefined
            };

            console.log('Starting tour creation...', requestData);
            
            // Start with video processing status check
            waitForProcessingAndCreateTour(requestData);
        }

        async function waitForProcessingAndCreateTour(requestData) {
            // Start simulated progress
            simulateProcessing();
            
            // Wait for processing to complete
            await waitForProcessingCompletion();
            
            // Now create the tour with overlays
            console.log('Processing complete, adding overlays...');
            updateProgress(80, 'Adding agent watermark...');
            
            // Keep trying to create the tour until it succeeds
            let success = false;
            let attempts = 0;
            const maxAttempts = 10;
            
            while (!success && attempts < maxAttempts) {
                try {
                    const response = await fetch('/create_tour', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestData)
                    });

                    const data = await response.json();
                    
                    if (data.success) {
                        updateProgress(100, 'Tour created successfully!');
                        success = true;
                        
                        // Brief delay to show completion
                        setTimeout(() => {
                            hideLoadingOverlay();
                            // Store result data and redirect to delivery page with processing ID
                            sessionStorage.setItem('tourResult', JSON.stringify(data));
                            window.location.href = `/delivery/${exportData.processing_id}`;
                        }, 500);
                    } else {
                        console.log('Tour creation not ready yet, retrying...', data.error);
                        attempts++;
                        
                        // Wait 3 seconds before retrying
                        await new Promise(resolve => setTimeout(resolve, 3000));
                        updateProgress(Math.min(80 + attempts * 2, 95), 'Finalizing tour creation...');
                    }
                } catch (error) {
                    console.log('Tour creation attempt failed, retrying...', error);
                    attempts++;
                    
                    // Wait 3 seconds before retrying
                    await new Promise(resolve => setTimeout(resolve, 3000));
                    updateProgress(Math.min(80 + attempts * 2, 95), 'Finalizing tour creation...');
                }
            }
            
            // If we've exhausted all attempts, try once more with a longer wait
            if (!success) {
                console.log('Final attempt after extended wait...');
                updateProgress(90, 'Almost ready...');
                await new Promise(resolve => setTimeout(resolve, 10000)); // Wait 10 seconds
                
                try {
                    const response = await fetch('/create_tour', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(requestData)
                    });

                    const data = await response.json();
                    
                    if (data.success) {
                        updateProgress(100, 'Tour created successfully!');
                        
                        setTimeout(() => {
                            hideLoadingOverlay();
                            sessionStorage.setItem('tourResult', JSON.stringify(data));
                            window.location.href = `/delivery/${exportData.processing_id}`;
                        }, 500);
                    } else {
                        // Final fallback - just continue to delivery page
                        console.log('Final attempt failed, proceeding anyway');
                        hideLoadingOverlay();
                        window.location.href = `/delivery/${exportData.processing_id}`;
                    }
                } catch (error) {
                    // Final fallback - just continue to delivery page
                    console.log('Final attempt failed, proceeding anyway', error);
                    hideLoadingOverlay();
                    window.location.href = `/delivery/${exportData.processing_id}`;
                }
            }
        }

        async function waitForProcessingCompletion() {
            if (!exportData.processing_id) {
                console.log('No processing ID, assuming processing is complete');
                return; // No processing ID, assume processing is complete
            }

            console.log('Waiting for processing completion, ID:', exportData.processing_id);
            const maxAttempts = 120; // 10 minutes max (120 * 5 seconds)
            let attempts = 0;
            
            while (attempts < maxAttempts) {
                try {
                    console.log(`Processing check attempt ${attempts + 1}/${maxAttempts}`);
                    const response = await fetch(`/check_processing_status/${exportData.processing_id}`);
                    console.log('Processing check response status:', response.status);
                    
                    if (!response.ok) {
                        console.log('Processing check failed, response not ok:', response.status);
                        if (response.status === 404) {
                            console.log('Processing ID not found, assuming complete');
                            return; // Session not found, proceed anyway
                        }
                        // Other error, wait and try again
                        await new Promise(resolve => setTimeout(resolve, 5000));
                        attempts++;
                        continue;
                    }
                    
                    const result = await response.json();
                    console.log('Processing check result:', result);
                    
                    if (result.status === 'completed') {
                        console.log('Processing completed successfully');
                        return; // Processing is done
                    } else if (result.status === 'in_progress') {
                        console.log('Processing still in progress, waiting...');
                        updateProgress(Math.min(20 + (attempts * 2), 75), 'Processing video segments...');
                        
                        // Wait 5 seconds before checking again
                        await new Promise(resolve => setTimeout(resolve, 5000));
                        attempts++;
                    } else if (result.status === 'not_found') {
                        console.log('Processing session not found, assuming complete');
                        return; // Session not found, proceed anyway
                    } else {
                        console.log('Unknown processing status:', result.status);
                        return; // Unknown status, proceed anyway
                    }
                } catch (error) {
                    console.error('Error checking processing status:', error);
                    // If we can't check status, wait a bit and try again
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    attempts++;
                }
            }
            
            console.log('Processing check timed out, proceeding anyway');
            // If we timeout, proceed anyway
        }

        // Loading modal functions
        function showLoadingOverlay() {
            const modal = document.getElementById('loadingModal');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            
            modal.style.display = 'flex';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        }

        function hideLoadingOverlay() {
            const modal = document.getElementById('loadingModal');
            modal.style.display = 'none';
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
                { progress: 50, status: 'Adding agent watermark...', delay: 800 },
                { progress: 65, status: 'Applying speed adjustments...', delay: 1000 },
                { progress: 80, status: 'Processing video effects...', delay: 1500 },
                { progress: 90, status: 'Combining segments...', delay: 1000 },
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

        function formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        // Utility: convert File object to base64 string
        function toBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => resolve(reader.result);
                reader.onerror = (err) => reject(err);
            });
        }

        // Custom file upload functionality
        function setupCustomFileUpload() {
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('agencyLogo');
            const fileInfo = document.getElementById('fileInfo');
            const fileName = document.getElementById('fileName');
            const removeFile = document.getElementById('removeFile');

            // Click to upload
            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            // Drag and drop functionality
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });

            uploadArea.addEventListener('dragleave', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    handleFileSelect(files[0]);
                }
            });

            // File input change
            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    handleFileSelect(e.target.files[0]);
                }
            });

            // Remove file
            removeFile.addEventListener('click', (e) => {
                e.stopPropagation();
                clearFileSelection();
            });

            function handleFileSelect(file) {
                console.log('File selected:', file.name, file.type, file.size);
                
                // Validate file type
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file.');
                    return;
                }

                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    alert('File size must be less than 5MB.');
                    return;
                }

                // Create a new FileList-like object and assign it to the input
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                
                console.log('File assigned to input, files length:', fileInput.files.length);

                // Update UI
                fileName.textContent = file.name;
                fileInfo.style.display = 'flex';
                
                // Hide upload text
                const uploadText = uploadArea.querySelector('.upload-text');
                uploadText.style.display = 'none';
                
                console.log('File selection UI updated');
            }

            function clearFileSelection() {
                fileInput.value = '';
                fileInfo.style.display = 'none';
                fileName.textContent = '';
                
                // Show upload text
                const uploadText = uploadArea.querySelector('.upload-text');
                uploadText.style.display = 'flex';
            }
        } 