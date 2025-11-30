from flask import Flask, render_template, request, jsonify, send_file
from PIL import Image, ImageDraw
import io
import base64

app = Flask(__name__)

class MatrixController:
    def __init__(self):
        self.width = 64
        self.height = 64
        # Initialize with black images
        self.image_a = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        self.image_b = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        print("Matrix Controller Initialized")

    def process_image(self, image, target_size=(64, 64)):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image.resize(target_size, Image.Resampling.LANCZOS)

    def display_on_a(self, image):
        img = self.process_image(image)
        self.image_a = img
        print("Displaying image on Matrix A")
        # self.matrix_a.SetImage(img)

    def display_on_b(self, image):
        img = self.process_image(image)
        self.image_b = img
        print("Displaying image on Matrix B")
        # self.matrix_b.SetImage(img)

    def display_split(self, image):
        # Resize to 128x64
        img = self.process_image(image, target_size=(128, 64))
        # Crop
        img_a = img.crop((0, 0, 64, 64))
        img_b = img.crop((64, 0, 128, 64))
        
        print("Displaying split image on Matrix A and B")
        self.display_on_a(img_a)
        self.display_on_b(img_b)

    def get_image_bytes(self, matrix='a'):
        img = self.image_a if matrix == 'a' else self.image_b
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

controller = MatrixController()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/matrix/<a>', methods=['GET'])
def get_matrix_image(a):
    if a not in ['a', 'b']:
        return jsonify({'error': 'Invalid matrix identifier. Use "a" or "b".'}), 400
    return send_file(controller.get_image_bytes(a), mimetype='image/png')

@app.route('/api/draw', methods=['POST'])
def handle_draw():
    try:
        data = request.json
        image_data = data.get('image') # Base64 string
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400

        # Remove header if present (e.g., "data:image/png;base64,")
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # The drawing canvas is treated as "Split" mode (spanning both)
        # or we could add a mode selector for drawing too. 
        # For now, let's assume drawing covers the whole 128x64 area.
        controller.display_split(image)
        
        return jsonify({'status': 'success', 'message': 'Drawing displayed'})
    except Exception as e:
        print(f"Error in draw: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def handle_upload():
    try:
        mode = request.form.get('mode')
        file_a = request.files.get('file_a')
        file_b = request.files.get('file_b') # Only for 'separate' mode
        
        if not mode:
            return jsonify({'error': 'Mode not specified'}), 400

        if mode == 'separate':
            if not file_a or not file_b:
                return jsonify({'error': 'Both files required for separate mode'}), 400
            
            img_a = Image.open(file_a)
            img_b = Image.open(file_b)
            controller.display_on_a(img_a)
            controller.display_on_b(img_b)
            
        else:
            if not file_a:
                return jsonify({'error': 'File required'}), 400
            
            img = Image.open(file_a)
            
            if mode == 'matrix_a':
                controller.display_on_a(img)
            elif mode == 'matrix_b':
                controller.display_on_b(img)
            elif mode == 'both':
                controller.display_on_a(img)
                controller.display_on_b(img)
            elif mode == 'split':
                controller.display_split(img)
            else:
                return jsonify({'error': 'Invalid mode'}), 400

        return jsonify({'status': 'success', 'message': f'Uploaded in {mode} mode'})
        
    except Exception as e:
        print(f"Error in upload: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
