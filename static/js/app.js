let uploadedFiles = [];
let currentJobId = null;

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const promptInput = document.getElementById('prompt');
const generateBtn = document.getElementById('generateBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressCount = document.getElementById('progressCount');
const progressLog = document.getElementById('progressLog');
const resultsSection = document.getElementById('resultsSection');
const gallery = document.getElementById('gallery');
const downloadAllBtn = document.getElementById('downloadAllBtn');

// Dropzone events
dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    addFiles(e.dataTransfer.files);
});
fileInput.addEventListener('change', () => addFiles(fileInput.files));

// Prompt presets
document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        promptInput.value = btn.dataset.prompt;
        updateGenerateButton();
    });
});

promptInput.addEventListener('input', updateGenerateButton);

function addFiles(fileListObj) {
    const newFiles = Array.from(fileListObj).filter(f => f.type.startsWith('image/'));
    uploadedFiles = [...uploadedFiles, ...newFiles];
    renderFileList();
    updateGenerateButton();
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    renderFileList();
    updateGenerateButton();
}

function renderFileList() {
    fileList.innerHTML = uploadedFiles.map((file, i) => `
        <div class="file-chip">
            <span>${escapeHtml(file.name)}</span>
            <span class="remove" onclick="removeFile(${i})">&times;</span>
        </div>
    `).join('');
}

function updateGenerateButton() {
    generateBtn.disabled = uploadedFiles.length === 0 || !promptInput.value.trim();
}

generateBtn.addEventListener('click', async () => {
    if (uploadedFiles.length === 0 || !promptInput.value.trim()) return;

    const prompt = promptInput.value.trim();
    const aspectRatio = document.getElementById('aspectRatio').value;
    const resolution = document.getElementById('resolution').value;

    // UI state
    generateBtn.disabled = true;
    generateBtn.querySelector('.btn-text').textContent = 'Generating...';
    generateBtn.querySelector('.spinner').classList.remove('hidden');
    progressSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    gallery.innerHTML = '';
    progressLog.innerHTML = '';
    progressFill.style.width = '0%';
    progressCount.textContent = `0 / ${uploadedFiles.length}`;

    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('aspect_ratio', aspectRatio);
    if (resolution) formData.append('resolution', resolution);
    uploadedFiles.forEach(file => formData.append('images', file));

    try {
        const res = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || 'Processing failed');
        }

        currentJobId = data.job_id;

        // Simulate progress based on results
        const total = uploadedFiles.length;
        const processed = data.results.length + data.error_details.length;
        const pct = (processed / total) * 100;
        progressFill.style.width = `${pct}%`;
        progressCount.textContent = `${processed} / ${total}`;

        // Log results
        data.results.forEach(r => {
            logMessage(`✓ ${escapeHtml(r.original)} → ${escapeHtml(r.generated)}`, 'success');
        });
        data.error_details.forEach(e => {
            logMessage(`✗ ${escapeHtml(e.original)}: ${escapeHtml(e.error)}`, 'error');
        });

        if (data.zip_available) {
            await loadGallery(data.job_id);
            resultsSection.classList.remove('hidden');
        }

        if (data.errors > 0 && data.success === 0) {
            logMessage('All images failed to process. Check your API key and try again.', 'error');
        }

    } catch (err) {
        logMessage(`Error: ${err.message}`, 'error');
    } finally {
        generateBtn.disabled = false;
        generateBtn.querySelector('.btn-text').textContent = 'Generate Product Photos';
        generateBtn.querySelector('.spinner').classList.add('hidden');
    }
});

function logMessage(text, type) {
    const div = document.createElement('div');
    div.className = `log-item log-${type}`;
    div.textContent = text;
    progressLog.appendChild(div);
    progressLog.scrollTop = progressLog.scrollHeight;
}

async function loadGallery(jobId) {
    try {
        const res = await fetch(`/api/preview/${jobId}`);
        const data = await res.json();

        gallery.innerHTML = data.files.map(f => `
            <div class="gallery-item">
                <img src="${f.base64}" alt="${escapeHtml(f.filename)}">
                <div class="info">
                    <div class="filename">${escapeHtml(f.filename)}</div>
                    <div class="actions">
                        <button onclick="downloadSingle('${jobId}', '${escapeHtml(f.filename)}')">Download</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load gallery', e);
    }
}

downloadAllBtn.addEventListener('click', () => {
    if (!currentJobId) return;
    window.location.href = `/api/download/${currentJobId}`;
});

function downloadSingle(jobId, filename) {
    window.location.href = `/api/download-single/${jobId}/${encodeURIComponent(filename)}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
