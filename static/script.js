let currentTool = 'brush';
let isDrawing = false;
const canvas = document.getElementById('pixelCanvas');
const ctx = canvas.getContext('2d', { willReadFrequently: true });

// Undo/Redo Stack
const historyStack = [];
let historyStep = -1;
const MAX_HISTORY = 50;

function saveState() {
    // Remove any redo steps
    if (historyStep < historyStack.length - 1) {
        historyStack.splice(historyStep + 1);
    }
    
    historyStack.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    historyStep++;
    
    // Limit history size
    if (historyStack.length > MAX_HISTORY) {
        historyStack.shift();
        historyStep--;
    }
}

function undo() {
    if (historyStep > 0) {
        historyStep--;
        ctx.putImageData(historyStack[historyStep], 0, 0);
    }
}

function redo() {
    if (historyStep < historyStack.length - 1) {
        historyStep++;
        ctx.putImageData(historyStack[historyStep], 0, 0);
    }
}

// Initialize Canvas
ctx.fillStyle = '#000000';
ctx.fillRect(0, 0, canvas.width, canvas.height);
ctx.imageSmoothingEnabled = false;
saveState(); // Initial state

// Tab Logic
function openTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(tabName).classList.add('active');
    // Find the button that calls this function (approximate)
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => {
        if(btn.textContent.toLowerCase().includes(tabName)) {
            btn.classList.add('active');
        }
    });
}

// Tool Logic
function setTool(tool) {
    currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`btn-${tool}`).classList.add('active');
}

function clearCanvas() {
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    saveState();
}

// Drawing Logic
const colorPicker = document.getElementById('colorPicker');
const brushSize = document.getElementById('brushSize');
const brushSizeVal = document.getElementById('brushSizeVal');

brushSize.addEventListener('input', (e) => {
    brushSizeVal.textContent = e.target.value;
});

function getMousePos(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
        x: Math.floor((evt.clientX - rect.left) * scaleX),
        y: Math.floor((evt.clientY - rect.top) * scaleY)
    };
}

function drawPixel(x, y, color, size) {
    ctx.fillStyle = color;
    const offset = Math.floor(size / 2);
    ctx.fillRect(x - offset, y - offset, size, size);
}

// Flood Fill Algorithm
function floodFill(startX, startY, fillColor) {
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const width = imageData.width;
    const height = imageData.height;
    const stack = [[startX, startY]];
    
    // Helper to get color at x,y
    const getPixelColor = (x, y) => {
        const i = (y * width + x) * 4;
        return [imageData.data[i], imageData.data[i+1], imageData.data[i+2]]; // Ignore alpha
    };

    // Parse hex color to rgb
    const r = parseInt(fillColor.slice(1, 3), 16);
    const g = parseInt(fillColor.slice(3, 5), 16);
    const b = parseInt(fillColor.slice(5, 7), 16);
    const targetRgb = [r, g, b];

    const startColor = getPixelColor(startX, startY);

    // If trying to fill with same color, return
    if (startColor[0] === targetRgb[0] && startColor[1] === targetRgb[1] && startColor[2] === targetRgb[2]) return;

    const matchStartColor = (x, y) => {
        const c = getPixelColor(x, y);
        return c[0] === startColor[0] && c[1] === startColor[1] && c[2] === startColor[2];
    };

    const setPixelColor = (x, y) => {
        const i = (y * width + x) * 4;
        imageData.data[i] = targetRgb[0];
        imageData.data[i+1] = targetRgb[1];
        imageData.data[i+2] = targetRgb[2];
        imageData.data[i+3] = 255;
    };

    while (stack.length) {
        const [x, y] = stack.pop();
        
        if (x < 0 || x >= width || y < 0 || y >= height) continue;
        if (matchStartColor(x, y)) {
            setPixelColor(x, y);
            stack.push([x + 1, y]);
            stack.push([x - 1, y]);
            stack.push([x, y + 1]);
            stack.push([x, y - 1]);
        }
    }
    
    ctx.putImageData(imageData, 0, 0);
    saveState();
}

canvas.addEventListener('mousedown', (e) => {
    isDrawing = true;
    const pos = getMousePos(e);
    
    if (currentTool === 'bucket') {
        floodFill(pos.x, pos.y, colorPicker.value);
    } else {
        const color = currentTool === 'eraser' ? '#000000' : colorPicker.value;
        drawPixel(pos.x, pos.y, color, parseInt(brushSize.value));
    }
});

canvas.addEventListener('mousemove', (e) => {
    if (!isDrawing || currentTool === 'bucket') return;
    const pos = getMousePos(e);
    const color = currentTool === 'eraser' ? '#000000' : colorPicker.value;
    drawPixel(pos.x, pos.y, color, parseInt(brushSize.value));
});

canvas.addEventListener('mouseup', () => {
    if (isDrawing) {
        isDrawing = false;
        saveState();
    }
});

canvas.addEventListener('mouseleave', () => {
    if (isDrawing) {
        isDrawing = false;
        saveState();
    }
});

// Touch Support for Mobile
canvas.addEventListener('touchstart', (e) => {
    e.preventDefault();
    isDrawing = true;
    const touch = e.touches[0];
    const pos = getMousePos(touch);
    
    if (currentTool === 'bucket') {
        floodFill(pos.x, pos.y, colorPicker.value);
    } else {
        const color = currentTool === 'eraser' ? '#000000' : colorPicker.value;
        drawPixel(pos.x, pos.y, color, parseInt(brushSize.value));
    }
}, { passive: false });

canvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    if (!isDrawing || currentTool === 'bucket') return;
    const touch = e.touches[0];
    const pos = getMousePos(touch);
    const color = currentTool === 'eraser' ? '#000000' : colorPicker.value;
    drawPixel(pos.x, pos.y, color, parseInt(brushSize.value));
}, { passive: false });

canvas.addEventListener('touchend', (e) => {
    e.preventDefault();
    if (isDrawing) {
        isDrawing = false;
        saveState();
    }
}, { passive: false });

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'z') {
        e.preventDefault();
        undo();
    } else if (e.ctrlKey && e.key === 'y') {
        e.preventDefault();
        redo();
    }
});

// API Calls
async function sendDrawing() {
    const dataUrl = canvas.toDataURL('image/png');
    
    try {
        const response = await fetch('/api/draw', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image: dataUrl })
        });
        const result = await response.json();
        showToast(result.message || 'Drawing sent!', 'success');
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to send drawing.', 'error');
    }
}

// Fullscreen Logic
function toggleFullscreen() {
    const container = document.getElementById('canvasContainer');
    container.classList.toggle('fullscreen');
    
    // If entering fullscreen, try to request browser fullscreen for better immersion
    if (container.classList.contains('fullscreen')) {
        if (container.requestFullscreen) {
            container.requestFullscreen().catch(err => {
                console.log(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
            });
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen().catch(err => {
                // Ignore error if not in fullscreen
            });
        }
    }
}

// Listen for fullscreen change events (e.g. user presses Esc)
document.addEventListener('fullscreenchange', () => {
    const container = document.getElementById('canvasContainer');
    if (!document.fullscreenElement && container.classList.contains('fullscreen')) {
        container.classList.remove('fullscreen');
    }
});

// Upload Logic
function updateUploadInputs() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const groupB = document.getElementById('input-group-b');
    
    if (mode === 'separate') {
        groupB.style.display = 'block';
    } else {
        groupB.style.display = 'none';
    }
}

async function uploadFiles() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const fileA = document.getElementById('fileA').files[0];
    const fileB = document.getElementById('fileB').files[0];
    
    const formData = new FormData();
    formData.append('mode', mode);
    
    if (fileA) formData.append('file_a', fileA);
    if (mode === 'separate' && fileB) formData.append('file_b', fileB);
    
    const statusDiv = document.getElementById('uploadStatus');
    statusDiv.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        statusDiv.textContent = '';
        if (response.ok) {
            showToast(result.message || 'Upload successful!', 'success');
        } else {
            showToast(result.error || 'Upload failed.', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        statusDiv.textContent = '';
        showToast('Upload failed.', 'error');
    }
}

async function clearMatrix() {
    try {
        const response = await fetch('/api/clear', { method: 'POST' });
        const result = await response.json();
        showToast(result.message, 'info');
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to clear matrix.', 'error');
    }
}

// Toast Notification Logic
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Add icon based on type
    let icon = '';
    if (type === 'success') icon = '✓ ';
    else if (type === 'error') icon = '✕ ';
    else if (type === 'info') icon = 'ℹ ';
    
    toast.textContent = icon + message;
    
    container.appendChild(toast);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('animationend', () => {
            toast.remove();
        });
    }, 3000);
}

// Admin Logic
function loadUsers() {
    const userList = document.getElementById('user-list');
    if (!userList) return; // Not on admin tab or not admin

    fetch('/api/admin/users')
        .then(res => res.json())
        .then(users => {
            userList.innerHTML = '';
            users.forEach(user => {
                const card = document.createElement('div');
                card.className = 'user-card';
                
                let roleBadge = user.is_admin ? '<span class="badge badge-admin">Admin</span>' : '';
                let statusBadge = user.is_approved ? '<span class="badge badge-approved">Approved</span>' : '<span class="badge badge-pending">Pending</span>';
                
                let actions = '';
                if (!user.is_approved) {
                    actions += `<button onclick="approveUser(${user.id})" class="tool-btn active">Approve</button>`;
                }
                if (!user.is_admin && user.is_approved) {
                    actions += `<button onclick="promoteUser(${user.id})" class="tool-btn">Promote</button>`;
                }
                actions += `<button onclick="kickUser(${user.id})" class="tool-btn danger">Kick</button>`;

                card.innerHTML = `
                    <div class="user-info">
                        <span class="user-name">${user.username}</span>
                        <div class="user-role">
                            ${roleBadge} ${statusBadge}
                        </div>
                    </div>
                    <div class="user-actions">
                        ${actions}
                    </div>
                `;
                userList.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to load users', 'error');
        });
}

function approveUser(id) {
    fetch(`/api/admin/approve/${id}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast(data.message, 'success');
            loadUsers();
        });
}

function promoteUser(id) {
    if(!confirm('Promote this user to Admin?')) return;
    fetch(`/api/admin/promote/${id}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast(data.message, 'success');
            loadUsers();
        });
}

function kickUser(id) {
    if(!confirm('Are you sure you want to delete this user?')) return;
    fetch(`/api/admin/kick/${id}`, { method: 'POST' })
        .then(res => {
            if(res.ok) return res.json();
            throw new Error('Failed to kick user');
        })
        .then(data => {
            showToast(data.message, 'success');
            loadUsers();
        })
        .catch(err => showToast(err.message, 'error'));
}

// Hook into tab switching to load users
const originalOpenTab = window.openTab;
window.openTab = function(tabName) {
    originalOpenTab(tabName);
    if (tabName === 'admin') {
        loadUsers();
    } else if (tabName === 'settings') {
        loadSettings();
        startTelemetryPoll();
    } else if (tabName === 'sdcard') {
        loadSDFiles();
    } else {
        stopTelemetryPoll();
    }
};

// SD Card Logic
function loadSDFiles() {
    const list = document.getElementById('sd-file-list');
    if (!list) return;

    fetch('/api/sd/files')
        .then(res => res.json())
        .then(data => {
            list.innerHTML = '';
            if (data.files.length === 0) {
                list.innerHTML = '<p>No files found.</p>';
                return;
            }
            
            data.files.forEach(filename => {
                const card = document.createElement('div');
                card.className = 'user-card'; // Reuse user-card style
                card.innerHTML = `
                    <div class="user-info">
                        <span class="user-name">${filename}</span>
                    </div>
                    <div class="user-actions">
                        <button onclick="deleteSDFile('${filename}')" class="tool-btn danger">Delete</button>
                    </div>
                `;
                list.appendChild(card);
            });
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to load files', 'error');
        });
}

async function uploadSDFile() {
    const fileInput = document.getElementById('fileSD');
    const file = fileInput.files[0];
    const mode = document.querySelector('input[name="sd_mode"]:checked').value;

    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    
    const statusDiv = document.getElementById('sdUploadStatus');
    statusDiv.textContent = 'Uploading...';
    
    try {
        const response = await fetch('/api/sd/upload', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        statusDiv.textContent = '';
        if (response.ok) {
            showToast(result.message, 'success');
            fileInput.value = ''; // Clear input
            loadSDFiles(); // Refresh list
        } else {
            showToast(result.error || 'Upload failed', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        statusDiv.textContent = '';
        showToast('Upload failed', 'error');
    }
}

function deleteSDFile(filename) {
    if(!confirm(`Delete ${filename}?`)) return;
    
    fetch(`/api/sd/files/${filename}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
            } else {
                showToast(data.message, 'success');
                loadSDFiles();
            }
        })
        .catch(err => showToast('Failed to delete file', 'error'));
}

function playSDCard() {
    fetch('/api/sd/play', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
            } else {
                showToast(data.message, 'success');
            }
        })
        .catch(err => showToast('Failed to start playback', 'error'));
}

function stopSDCard() {
    fetch('/api/sd/stop', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                showToast(data.error, 'error');
            } else {
                showToast(data.message, 'success');
            }
        })
        .catch(err => showToast('Failed to stop playback', 'error'));
}

// Settings & Telemetry Logic
let telemetryInterval;

function startTelemetryPoll() {
    stopTelemetryPoll();
    loadSettings(); // Initial load
    telemetryInterval = setInterval(loadSettings, 2000); // Poll every 2s
}

function stopTelemetryPoll() {
    if (telemetryInterval) {
        clearInterval(telemetryInterval);
        telemetryInterval = null;
    }
}

function loadSettings() {
    fetch('/api/admin/settings')
        .then(res => res.json())
        .then(data => {
            updateTelemetryUI(data.telemetry, data.telemetry_age);
            
            // Only update form if not currently being edited (simple check: active element)
            if (!document.getElementById('config-form').contains(document.activeElement)) {
                updateConfigForm(data.settings);
            }
        })
        .catch(err => console.error("Failed to load settings", err));
}

function updateTelemetryUI(telemetry, age) {
    const statusEl = document.getElementById('tel-status');
    if (age !== null && age < 10) {
        statusEl.textContent = 'Online';
        statusEl.style.color = '#4CAF50';
    } else {
        statusEl.textContent = 'Offline';
        statusEl.style.color = '#f44336';
    }

    if (telemetry && telemetry.network) {
        document.getElementById('tel-ip').textContent = telemetry.network.ip || '-';
        document.getElementById('tel-network').textContent = `${telemetry.network.type} (${telemetry.network.ssid || ''})`;
    }
    
    if (telemetry) {
        document.getElementById('tel-refresh').textContent = telemetry.refresh_rate ? `${telemetry.refresh_rate} Hz` : '-';
    }
}

function updateConfigForm(settings) {
    if (!settings) return;
    
    document.getElementById('conf-brightness').value = settings.brightness;
    document.getElementById('val-brightness').textContent = settings.brightness;
    document.getElementById('conf-polling').value = settings.polling_rate;
    document.getElementById('conf-gpio').value = settings.gpio_slowdown;
    
    // New fields
    document.getElementById('conf-rows').value = settings.matrix_rows || 64;
    document.getElementById('conf-cols').value = settings.matrix_cols || 64;
    document.getElementById('conf-chain').value = settings.matrix_chain || 2;
    document.getElementById('conf-parallel').value = settings.matrix_parallel || 1;
    document.getElementById('conf-pwm').value = settings.matrix_pwm_lsb_nanoseconds || 130;
    
    document.getElementById('conf-slide-duration').value = settings.sd_slide_duration || 30.0;
    document.getElementById('conf-video-fps').value = settings.sd_video_fps || 30.0;
    document.getElementById('conf-playlist-refresh').value = settings.sd_playlist_refresh_rate || 10.0;

    document.getElementById('conf-pos1').value = settings.position_1;
    document.getElementById('val-pos1').textContent = settings.position_1; // Update display
    document.getElementById('conf-pos2').value = settings.position_2 || 0;
    
    document.getElementById('conf-req-rate').value = settings.request_send_rate;
    
    document.getElementById('conf-wifi-ssid').value = settings.wifi_ssid || '';
    document.getElementById('conf-wifi-pass').value = settings.wifi_password || '';

    document.getElementById('conf-pulsing').checked = settings.hardware_pulsing;
}

function rotatePosition1() {
    let current = parseInt(document.getElementById('conf-pos1').value) || 0;
    current = (current + 90) % 360;
    document.getElementById('conf-pos1').value = current;
    document.getElementById('val-pos1').textContent = current;
}

function saveSettings() {
    const data = {
        brightness: parseInt(document.getElementById('conf-brightness').value),
        polling_rate: parseFloat(document.getElementById('conf-polling').value),
        gpio_slowdown: parseInt(document.getElementById('conf-gpio').value),
        
        // New fields
        matrix_rows: parseInt(document.getElementById('conf-rows').value),
        matrix_cols: parseInt(document.getElementById('conf-cols').value),
        matrix_chain: parseInt(document.getElementById('conf-chain').value),
        matrix_parallel: parseInt(document.getElementById('conf-parallel').value),
        matrix_pwm_lsb_nanoseconds: parseInt(document.getElementById('conf-pwm').value),
        
        sd_slide_duration: parseFloat(document.getElementById('conf-slide-duration').value),
        sd_video_fps: parseFloat(document.getElementById('conf-video-fps').value),
        sd_playlist_refresh_rate: parseFloat(document.getElementById('conf-playlist-refresh').value),

        position_1: parseInt(document.getElementById('conf-pos1').value),
        position_2: parseInt(document.getElementById('conf-pos2').value),
        request_send_rate: parseFloat(document.getElementById('conf-req-rate').value),
        
        wifi_ssid: document.getElementById('conf-wifi-ssid').value,
        wifi_password: document.getElementById('conf-wifi-pass').value,
        no_wifi_update: document.getElementById('conf-no-wifi-update').checked,

        hardware_pulsing: document.getElementById('conf-pulsing').checked
    };

    fetch('/api/admin/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(result => {
        if (result.error) {
            showToast(result.error, 'error');
        } else {
            showToast('Configuration saved!', 'success');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Failed to save settings', 'error');
    });
}

function togglePasswordVisibility(id) {
    const input = document.getElementById(id);
    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }
}

// Status Polling
function updateStatus() {
    fetch('/api/status')
        .then(res => res.json())
        .then(data => {
            const statusPi = document.getElementById('status-pi');
            
            // If either A or B is connected, show as connected
            if (data.a || data.b) {
                statusPi.classList.add('connected');
            } else {
                statusPi.classList.remove('connected');
            }
        })
        .catch(err => console.error("Status poll error", err));
}

// Poll every 2 seconds
setInterval(updateStatus, 2000);
updateStatus();
