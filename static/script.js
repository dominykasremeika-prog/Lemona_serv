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
        alert(result.message || 'Drawing sent!');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to send drawing.');
    }
}

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
        statusDiv.textContent = result.message || result.error;
    } catch (error) {
        console.error('Error:', error);
        statusDiv.textContent = 'Upload failed.';
    }
}
