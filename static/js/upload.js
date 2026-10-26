/**
 * PlagiarismAI — Document Check & Upload Script
 * Handles real file validation, drag-and-drop, client preview, remove file, and processing overlay
 */

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzoneBox');
    const fileInput = document.getElementById('documentFileInput');
    const btnBrowse = document.getElementById('btnBrowseFile');
    const selectedDisplay = document.getElementById('fileSelectedDisplay');
    const selectedName = document.getElementById('selectedFileName');
    const selectedSize = document.getElementById('selectedFileSize');
    const selectedExt = document.getElementById('selectedFileExt');
    const btnRemove = document.getElementById('btnRemoveFile');
    const uploadForm = document.getElementById('documentUploadForm');
    const btnSubmit = document.getElementById('btnSubmitCheck');
    const submitText = document.getElementById('submitBtnText');
    const processingOverlay = document.getElementById('processingOverlay');
    const statusDesc = document.getElementById('processingStatusDesc');

    const radioSubmitted = document.getElementById('radioRoleSubmitted');
    const radioReference = document.getElementById('radioRoleReference');
    const immediateWrap = document.getElementById('immediateAnalyzeWrap');
    const scopeBox = document.getElementById('comparisonScopeBox');

    if (!dropzone || !fileInput) return;

    // Helper: format bytes to human-readable size
    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    // Update role toggle UI
    function handleRoleChange() {
        const isReference = radioReference && radioReference.checked;
        if (immediateWrap) {
            immediateWrap.style.display = isReference ? 'none' : 'block';
        }
        if (scopeBox) {
            scopeBox.style.display = isReference ? 'none' : 'block';
        }
        if (submitText) {
            submitText.textContent = isReference ? 'Upload Reference Document' : 'Run Document Check';
        }
    }

    if (radioSubmitted && radioReference) {
        radioSubmitted.addEventListener('change', handleRoleChange);
        radioReference.addEventListener('change', handleRoleChange);
        handleRoleChange();
    }

    // Display selected file preview
    function setFile(file) {
        if (!file) {
            clearFile();
            return;
        }

        const allowed = ['pdf', 'docx', 'txt'];
        const ext = file.name.split('.').pop().toLowerCase();

        if (!allowed.includes(ext)) {
            alert('Unsupported file format. Please select a PDF (.pdf), Word (.docx), or plain text (.txt) document.');
            clearFile();
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            alert('The selected document exceeds the 10 MB maximum file size limit.');
            clearFile();
            return;
        }

        selectedName.textContent = file.name;
        selectedSize.textContent = formatBytes(file.size);
        selectedExt.textContent = ext.toUpperCase();
        selectedDisplay.style.display = 'flex';
        dropzone.style.display = 'none';
    }

    // Clear file selection
    function clearFile() {
        fileInput.value = '';
        selectedDisplay.style.display = 'none';
        dropzone.style.display = 'block';
    }

    if (btnBrowse) {
        btnBrowse.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    });

    if (btnRemove) {
        btnRemove.addEventListener('click', (e) => {
            e.preventDefault();
            clearFile();
        });
    }

    // Drag and drop event listeners
    ['dragenter', 'dragover'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt.files && dt.files[0]) {
            fileInput.files = dt.files;
            setFile(dt.files[0]);
        }
    });

    // Form submission & realistic processing progression (Section 6)
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            if (!fileInput.files || fileInput.files.length === 0) {
                alert('Please select a document file to proceed.');
                e.preventDefault();
                return;
            }

            const isReference = radioReference && radioReference.checked;

            if (btnSubmit) {
                btnSubmit.disabled = true;
            }

            if (!isReference && processingOverlay) {
                processingOverlay.style.display = 'flex';

                // Progression indicators corresponding to server stages
                setTimeout(() => {
                    const step1 = document.getElementById('step1');
                    const step2 = document.getElementById('step2');
                    if (step1) {
                        step1.className = 'step-row step-completed';
                        step1.querySelector('.step-icon-indicator').innerHTML = '&#10003;';
                    }
                    if (step2) {
                        step2.className = 'step-row step-active';
                        step2.querySelector('.step-icon-indicator').innerHTML = '&bull;';
                    }
                    if (statusDesc) statusDesc.textContent = 'Extracting and normalizing document text...';
                }, 600);

                setTimeout(() => {
                    const step2 = document.getElementById('step2');
                    const step3 = document.getElementById('step3');
                    if (step2) {
                        step2.className = 'step-row step-completed';
                        step2.querySelector('.step-icon-indicator').innerHTML = '&#10003;';
                    }
                    if (step3) {
                        step3.className = 'step-row step-active';
                        step3.querySelector('.step-icon-indicator').innerHTML = '&bull;';
                    }
                    if (statusDesc) statusDesc.textContent = 'Executing TF-IDF vectorization and comparing reference corpus...';
                }, 1400);

                setTimeout(() => {
                    const step3 = document.getElementById('step3');
                    const step4 = document.getElementById('step4');
                    if (step3) {
                        step3.className = 'step-row step-completed';
                        step3.querySelector('.step-icon-indicator').innerHTML = '&#10003;';
                    }
                    if (step4) {
                        step4.className = 'step-row step-active';
                        step4.querySelector('.step-icon-indicator').innerHTML = '&bull;';
                    }
                    if (statusDesc) statusDesc.textContent = 'Aligning matching sentences and calculating coverage...';
                }, 2200);
            }
        });
    }
});
