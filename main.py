from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from PIL import Image, ImageSequence
import io
import base64
import time
import os
import tempfile
import imageio
import threading
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here' # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
SD_UPLOAD_FOLDER = 'sd_uploads'
if not os.path.exists(SD_UPLOAD_FOLDER):
    os.makedirs(SD_UPLOAD_FOLDER)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.is_admin}', '{self.is_approved}')"

def get_client_ip():
    """Helper to get the client IP from telemetry or settings."""
    if 'network' in latest_telemetry and 'ip' in latest_telemetry['network']:
        return latest_telemetry['network']['ip']
    settings = ClientSettings.get_settings()
    if settings.last_ip:
        return settings.last_ip
    return None

class ClientSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    polling_rate = db.Column(db.Float, default=1.0)
    gpio_slowdown = db.Column(db.Integer, default=4)
    hardware_pulsing = db.Column(db.Boolean, default=True)
    brightness = db.Column(db.Integer, default=50)
    position_1 = db.Column(db.Integer, default=0)
    position_2 = db.Column(db.Integer, default=0)
    request_send_rate = db.Column(db.Float, default=1.0)
    wifi_ssid = db.Column(db.String(100), default="")
    wifi_password = db.Column(db.String(100), default="")
    # use_sd_card_fallback = db.Column(db.Boolean, default=False) # Deprecated
    
    # New fields
    matrix_rows = db.Column(db.Integer, default=64)
    matrix_cols = db.Column(db.Integer, default=64)
    matrix_chain = db.Column(db.Integer, default=2)
    matrix_parallel = db.Column(db.Integer, default=1)
    matrix_pwm_lsb_nanoseconds = db.Column(db.Integer, default=130)
    sd_slide_duration = db.Column(db.Float, default=30.0)
    sd_video_fps = db.Column(db.Float, default=30.0)
    sd_playlist_refresh_rate = db.Column(db.Float, default=10.0)
    
    # Telemetry fields (persisted)
    last_ip = db.Column(db.String(20), default="")
    last_ssid = db.Column(db.String(100), default="")
    last_network_type = db.Column(db.String(20), default="")
    last_refresh_rate = db.Column(db.Float, default=0.0)
    last_seen = db.Column(db.Float, default=0.0)
    
    # Default singleton retrieval
    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls(
                polling_rate=5.0, 
                gpio_slowdown=4, 
                hardware_pulsing=True, 
                brightness=50, 
                position_1=0,
                position_2=0,
                request_send_rate=1.0,
                wifi_ssid="",
                wifi_password="",
                # use_sd_card_fallback=False,
                matrix_rows=64,
                matrix_cols=64,
                matrix_chain=2,
                matrix_parallel=1,
                matrix_pwm_lsb_nanoseconds=130,
                sd_slide_duration=30.0,
                sd_video_fps=30.0,
                sd_playlist_refresh_rate=10.0
            )
            db.session.add(settings)
            db.session.commit()
        return settings

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Global State for Telemetry ---
latest_telemetry = {}

# --- Decorators ---
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return login_required(wrapper)

def approval_required(f):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_approved:
            if request.is_json:
                return jsonify({'error': 'Account not approved yet'}), 403
            else:
                flash('Your account is pending approval.', 'warning')
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return login_required(wrapper)

class MatrixController:
    def __init__(self):
        self.width = 64
        self.height = 64
        # Initialize with black images
        self.content_a = {'type': 'static', 'image': Image.new('RGB', (self.width, self.height), (0, 0, 0))}
        self.content_b = {'type': 'static', 'image': Image.new('RGB', (self.width, self.height), (0, 0, 0))}
        self.last_seen = {'a': 0, 'b': 0}
        print("Matrix Controller Initialized")

    def process_image(self, image, target_size=(64, 64)):
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image.resize(target_size, Image.Resampling.LANCZOS)

    def set_content(self, matrix, content):
        """
        content: dict with keys:
          - type: 'static' or 'animation'
          - image: PIL Image (for static)
          - frames: list of PIL Images (for animation)
          - durations: list of durations in seconds (for animation)
          - start_time: timestamp (for animation)
        """
        if matrix == 'a':
            self.content_a = content
        elif matrix == 'b':
            self.content_b = content

    def display_on_a(self, content):
        if isinstance(content, Image.Image):
             # Legacy support for direct image passing
             content = {'type': 'static', 'image': self.process_image(content)}
        elif content['type'] == 'static':
             content['image'] = self.process_image(content['image'])
        elif content['type'] == 'animation':
             content['frames'] = [self.process_image(f) for f in content['frames']]
             content['start_time'] = time.time()
        
        self.set_content('a', content)
        print("Displaying content on Matrix A")

    def display_on_b(self, content):
        if isinstance(content, Image.Image):
             content = {'type': 'static', 'image': self.process_image(content)}
        elif content['type'] == 'static':
             content['image'] = self.process_image(content['image'])
        elif content['type'] == 'animation':
             content['frames'] = [self.process_image(f) for f in content['frames']]
             content['start_time'] = time.time()

        self.set_content('b', content)
        print("Displaying content on Matrix B")

    def display_split(self, content):
        # Handle split for static images only for now (or simple frame split for animations)
        # For simplicity, let's assume split only works well for static images or we split each frame
        
        if isinstance(content, Image.Image):
             content = {'type': 'static', 'image': content}

        if content['type'] == 'static':
            img = self.process_image(content['image'], target_size=(128, 64))
            img_a = img.crop((0, 0, 64, 64))
            img_b = img.crop((64, 0, 128, 64))
            self.display_on_a(img_a)
            self.display_on_b(img_b)
        elif content['type'] == 'animation':
            # Split each frame
            frames_a = []
            frames_b = []
            for f in content['frames']:
                img = self.process_image(f, target_size=(128, 64))
                frames_a.append(img.crop((0, 0, 64, 64)))
                frames_b.append(img.crop((64, 0, 128, 64)))
            
            content_a = {
                'type': 'animation',
                'frames': frames_a,
                'durations': content['durations'],
                'start_time': time.time()
            }
            content_b = {
                'type': 'animation',
                'frames': frames_b,
                'durations': content['durations'],
                'start_time': time.time()
            }
            self.set_content('a', content_a)
            self.set_content('b', content_b)
        
        print("Displaying split content on Matrix A and B")
    
    def clear_matrix(self, matrix='both'):
        black = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        content = {'type': 'static', 'image': black}
        if matrix == 'a' or matrix == 'both':
            self.set_content('a', content)
        if matrix == 'b' or matrix == 'both':
            self.set_content('b', content)
        print(f"Cleared matrix {matrix}")

    def get_current_frame(self, content):
        if content['type'] == 'static':
            return content['image']
        elif content['type'] == 'animation':
            elapsed = time.time() - content['start_time']
            total_duration = sum(content['durations'])
            if total_duration == 0: return content['frames'][0]
            
            loop_time = elapsed % total_duration
            current_time = 0
            for i, duration in enumerate(content['durations']):
                current_time += duration
                if current_time > loop_time:
                    return content['frames'][i]
            return content['frames'][0]
        return Image.new('RGB', (64, 64), (0, 0, 0))

    def get_image_bytes(self, matrix='a'):
        # Update last seen timestamp
        self.last_seen[matrix] = time.time()
        
        content = self.content_a if matrix == 'a' else self.content_b
        img = self.get_current_frame(content)
        
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    
    def get_status(self):
        now = time.time()
        # Consider connected if seen within last 10 seconds
        connected_a = (now - self.last_seen['a']) < 10
        connected_b = (now - self.last_seen['b']) < 10
        return {'a': connected_a, 'b': connected_b}

controller = MatrixController()

def process_content_from_path(temp_path, filename):
    """Processes a file from a path and returns a content dict."""
    filename = filename.lower()
    
    try:
        if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            # Video processing using imageio
            reader = imageio.get_reader(temp_path)
            meta = reader.get_meta_data()
            fps = meta.get('fps', 30)
            duration_per_frame = 1.0 / fps
            
            frames = []
            durations = []
            
            # Limit frames to prevent memory explosion (e.g., max 100 frames or 5 seconds)
            max_frames = 150 
            count = 0
            
            for frame in reader:
                if count >= max_frames: break
                # Convert numpy array to PIL Image
                img = Image.fromarray(frame)
                frames.append(img)
                durations.append(duration_per_frame)
                count += 1
            
            reader.close()
            
            if not frames:
                raise Exception("No frames found in video")
                
            return {
                'type': 'animation',
                'frames': frames,
                'durations': durations
            }

        elif filename.endswith('.gif'):
            # GIF processing using Pillow
            img = Image.open(temp_path)
            
            if getattr(img, "is_animated", False):
                frames = []
                durations = []
                for frame in ImageSequence.Iterator(img):
                    frames.append(frame.convert('RGB'))
                    # GIF duration is in milliseconds
                    durations.append(frame.info.get('duration', 100) / 1000.0)
                
                return {
                    'type': 'animation',
                    'frames': frames,
                    'durations': durations
                }
            else:
                return {
                    'type': 'static',
                    'image': img.convert('RGB')
                }
        else:
            # Standard Image
            img = Image.open(temp_path)
            return {
                'type': 'static',
                'image': img.convert('RGB')
            }
            
    except Exception as e:
        print(f"Error processing file: {e}")
        raise e

def process_upload(file_storage):
    """Legacy wrapper for process_content_from_path"""
    filename = file_storage.filename.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp:
        file_storage.save(temp.name)
        temp_path = temp.name
    
    try:
        return process_content_from_path(temp_path, filename)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

# --- Auth Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # First user is admin and approved
        is_first_user = User.query.count() == 0
        user = User(username=username, password=hashed_password, 
                   is_admin=is_first_user, is_approved=is_first_user)
        
        db.session.add(user)
        db.session.commit()

        
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Admin API Routes ---
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    users = User.query.all()
    user_list = []
    for u in users:
        user_list.append({
            'id': u.id,
            'username': u.username,
            'is_admin': u.is_admin,
            'is_approved': u.is_approved
        })
    return jsonify(user_list)

@app.route('/api/admin/approve/<int:user_id>', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    return jsonify({'message': f'User {user.username} approved'})

@app.route('/api/admin/promote/<int:user_id>', methods=['POST'])
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    user.is_approved = True # Admins must be approved
    db.session.commit()
    return jsonify({'message': f'User {user.username} promoted to Admin'})

@app.route('/api/admin/kick/<int:user_id>', methods=['POST'])
@admin_required
def kick_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot kick yourself'}), 400
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'})

# --- Main Routes ---
@app.route('/')
@login_required
def index():
    if not current_user.is_approved:
        return render_template('unapproved.html')
    return render_template('index.html', user=current_user)

@app.route('/api/matrix/<a>', methods=['GET'])
def get_matrix_image(a):
    # This route is accessed by the Raspberry Pi, so we might not want to require login here
    # Or we could use a separate API key for the Pi. For now, let's leave it open or check IP?
    # Assuming Pi is on local network or we don't want to complicate Pi setup yet.
    if a not in ['a', 'b']:
        return jsonify({'error': 'Invalid matrix identifier. Use "a" or "b".'}), 400
    return send_file(controller.get_image_bytes(a), mimetype='image/png')

@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    return jsonify(controller.get_status())

@app.route('/api/clear', methods=['POST'])
@approval_required
def handle_clear():
    controller.clear_matrix()
    return jsonify({'status': 'success', 'message': 'Matrices cleared'})

@app.route('/api/draw', methods=['POST'])
@approval_required
def handle_draw():
    temp_path = None
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
        controller.display_split(image)
        
        # Push to client
        fd, temp_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        image.save(temp_path, format='PNG')
        
        client_ip = get_client_ip()

        if client_ip:
            push_live_content_to_client('split', client_ip, temp_path, 'drawing.png')

        return jsonify({'status': 'success', 'message': 'Drawing displayed'})
    except Exception as e:
        print(f"Error in draw: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

def push_live_content_to_client(mode, client_ip, path_a, filename_a, path_b=None, filename_b=None):
    """Pushes live content to the client for immediate playback."""
    url = f"http://{client_ip}:5000/api/live/upload"
    try:
        files = {}
        if path_a:
            files['file_a'] = (filename_a, open(path_a, 'rb'))
        if path_b:
            files['file_b'] = (filename_b, open(path_b, 'rb'))
            
        data = {'mode': mode}
        print(f"Pushing live content to {url}")
        requests.post(url, files=files, data=data, timeout=5)
        
        # Close files
        for f in files.values():
            f[1].close()
            
    except Exception as e:
        print(f"Error pushing live content: {e}")

@app.route('/api/upload', methods=['POST'])
@approval_required
def handle_upload():
    temp_paths = []
    try:
        mode = request.form.get('mode')
        file_a = request.files.get('file_a')
        file_b = request.files.get('file_b') # Only for 'separate' mode
        
        if not mode:
            return jsonify({'error': 'Mode not specified'}), 400

        # Helper to save temp file
        def save_temp(f):
            if not f: return None, None
            filename = f.filename
            fd, path = tempfile.mkstemp(suffix=os.path.splitext(filename)[1])
            os.close(fd)
            f.save(path)
            temp_paths.append(path)
            return path, filename

        path_a, filename_a = save_temp(file_a)
        path_b, filename_b = save_temp(file_b)

        # Push to client if connected (or use last known IP)
        client_ip = get_client_ip()

        if client_ip:
            # We run this synchronously to ensure files exist, or we could thread it if we manage cleanup carefully.
            # Given the user wants to "post it", blocking briefly is acceptable.
            push_live_content_to_client(mode, client_ip, path_a, filename_a, path_b, filename_b)

        if mode == 'separate':
            if not path_a or not path_b:
                return jsonify({'error': 'Both files required for separate mode'}), 400
            
            content_a = process_content_from_path(path_a, filename_a)
            content_b = process_content_from_path(path_b, filename_b)
            controller.display_on_a(content_a)
            controller.display_on_b(content_b)
            
        else:
            if not path_a:
                return jsonify({'error': 'File required'}), 400
            
            content = process_content_from_path(path_a, filename_a)
            
            if mode == 'matrix_a':
                controller.display_on_a(content)
            elif mode == 'matrix_b':
                controller.display_on_b(content)
            elif mode == 'both':
                controller.display_on_a(content)
                controller.display_on_b(content)
            elif mode == 'split':
                controller.display_split(content)
            else:
                return jsonify({'error': 'Invalid mode'}), 400

        return jsonify({'status': 'success', 'message': f'Uploaded in {mode} mode'})
        
    except Exception as e:
        print(f"Error in upload: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Cleanup temp files
        for path in temp_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

# --- Client API Routes ---

@app.route('/api/telemetry', methods=['POST'])
def receive_telemetry():
    """
    Endpoint for the Raspberry Pi to report its status.
    """
    global latest_telemetry
    try:
        data = request.json
        # Add timestamp
        data['last_seen'] = time.time()
        latest_telemetry = data
        
        # Update database with latest telemetry info
        if 'network' in data and 'ip' in data['network']:
            settings = ClientSettings.get_settings()
            settings.last_ip = data['network']['ip']
            if 'ssid' in data['network']:
                settings.last_ssid = data['network']['ssid']
            if 'type' in data['network']:
                settings.last_network_type = data['network']['type']
            if 'refresh_rate' in data:
                settings.last_refresh_rate = float(data.get('refresh_rate', 0))
            settings.last_seen = data['last_seen']
            db.session.commit()
        
        # We could optionally return the new config here if we wanted to combine calls
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/client-config', methods=['GET'])
def get_client_config():
    """
    Endpoint for the Raspberry Pi to fetch its configuration.
    """
    # Update telemetry/online status from this heartbeat
    try:
        client_ip = request.remote_addr
        now = time.time()
        
        # Update global telemetry
        global latest_telemetry
        if 'network' not in latest_telemetry:
            latest_telemetry['network'] = {}
        
        latest_telemetry['network']['ip'] = client_ip
        latest_telemetry['last_seen'] = now
        latest_telemetry['timestamp'] = now # Ensure age calculation works
        
        # Update database
        settings = ClientSettings.get_settings()
        settings.last_ip = client_ip
        settings.last_seen = now
        db.session.commit()
    except Exception as e:
        print(f"Error updating telemetry from config fetch: {e}")

    settings = ClientSettings.get_settings()
    return jsonify({
        'polling_rate': settings.polling_rate,
        'gpio_slowdown': settings.gpio_slowdown,
        'hardware_pulsing': settings.hardware_pulsing,
        'brightness': settings.brightness,
        'position_1': settings.position_1,
        'position_2': settings.position_2,
        'request_send_rate': settings.request_send_rate,
        'wifi_ssid': settings.wifi_ssid,
        'wifi_password': settings.wifi_password,
        # 'use_sd_card_fallback': settings.use_sd_card_fallback,
        'matrix_rows': settings.matrix_rows,
        'matrix_cols': settings.matrix_cols,
        'matrix_chain': settings.matrix_chain,
        'matrix_parallel': settings.matrix_parallel,
        'matrix_pwm_lsb_nanoseconds': settings.matrix_pwm_lsb_nanoseconds,
        'sd_slide_duration': settings.sd_slide_duration,
        'sd_video_fps': settings.sd_video_fps,
        'sd_playlist_refresh_rate': settings.sd_playlist_refresh_rate
    })

# --- Admin Settings Routes ---

@app.route('/api/admin/settings', methods=['GET'])
@admin_required
def get_admin_settings():
    """
    Endpoint for the Web UI to get current settings.
    """
    settings = ClientSettings.get_settings()
    
    # Calculate telemetry age
    telemetry_age = None
    if 'timestamp' in latest_telemetry:
        telemetry_age = time.time() - latest_telemetry['timestamp']
        
    return jsonify({
        'settings': {
            'polling_rate': settings.polling_rate,
            'gpio_slowdown': settings.gpio_slowdown,
            'hardware_pulsing': settings.hardware_pulsing,
            'brightness': settings.brightness,
            'position_1': settings.position_1,
            'position_2': settings.position_2,
            'request_send_rate': settings.request_send_rate,
            'wifi_ssid': settings.wifi_ssid,
            'wifi_password': settings.wifi_password,
            # 'use_sd_card_fallback': settings.use_sd_card_fallback,
            'matrix_rows': settings.matrix_rows,
            'matrix_cols': settings.matrix_cols,
            'matrix_chain': settings.matrix_chain,
            'matrix_parallel': settings.matrix_parallel,
            'matrix_pwm_lsb_nanoseconds': settings.matrix_pwm_lsb_nanoseconds,
            'sd_slide_duration': settings.sd_slide_duration,
            'sd_video_fps': settings.sd_video_fps,
            'sd_playlist_refresh_rate': settings.sd_playlist_refresh_rate
        },
        'telemetry': latest_telemetry,
        'telemetry_age': telemetry_age
    })

@app.route('/api/admin/settings', methods=['POST'])
@admin_required
def update_admin_settings():
    """
    Endpoint for the Web UI to update settings.
    """
    try:
        data = request.json
        settings = ClientSettings.get_settings()
        
        if 'polling_rate' in data:
            settings.polling_rate = float(data['polling_rate'])
        if 'gpio_slowdown' in data:
            settings.gpio_slowdown = int(data['gpio_slowdown'])
        if 'hardware_pulsing' in data:
            settings.hardware_pulsing = bool(data['hardware_pulsing'])
        if 'brightness' in data:
            settings.brightness = int(data['brightness'])
        if 'position_1' in data:
            settings.position_1 = int(data['position_1'])
        if 'position_2' in data:
            settings.position_2 = int(data['position_2'])
        if 'request_send_rate' in data:
            settings.request_send_rate = float(data['request_send_rate'])
            
        no_wifi_update = data.get('no_wifi_update', False)
        
        if not no_wifi_update:
            if 'wifi_ssid' in data:
                settings.wifi_ssid = data['wifi_ssid']
            if 'wifi_password' in data:
                settings.wifi_password = data['wifi_password']
                
        # if 'use_sd_card_fallback' in data:
        #     settings.use_sd_card_fallback = bool(data['use_sd_card_fallback'])
        
        # New fields
        if 'matrix_rows' in data: settings.matrix_rows = int(data['matrix_rows'])
        if 'matrix_cols' in data: settings.matrix_cols = int(data['matrix_cols'])
        if 'matrix_chain' in data: settings.matrix_chain = int(data['matrix_chain'])
        if 'matrix_parallel' in data: settings.matrix_parallel = int(data['matrix_parallel'])
        if 'matrix_pwm_lsb_nanoseconds' in data: settings.matrix_pwm_lsb_nanoseconds = int(data['matrix_pwm_lsb_nanoseconds'])
        if 'sd_slide_duration' in data: settings.sd_slide_duration = float(data['sd_slide_duration'])
        if 'sd_video_fps' in data: settings.sd_video_fps = float(data['sd_video_fps'])
        if 'sd_playlist_refresh_rate' in data: settings.sd_playlist_refresh_rate = float(data['sd_playlist_refresh_rate'])
            
        db.session.commit()
        
        # Prepare settings dict for push
        settings_dict = {
            'polling_rate': settings.polling_rate,
            'gpio_slowdown': settings.gpio_slowdown,
            'hardware_pulsing': settings.hardware_pulsing,
            'brightness': settings.brightness,
            'position_1': settings.position_1,
            'position_2': settings.position_2,
            'request_send_rate': settings.request_send_rate,
            # 'use_sd_card_fallback': settings.use_sd_card_fallback,
            'matrix_rows': settings.matrix_rows,
            'matrix_cols': settings.matrix_cols,
            'matrix_chain': settings.matrix_chain,
            'matrix_parallel': settings.matrix_parallel,
            'matrix_pwm_lsb_nanoseconds': settings.matrix_pwm_lsb_nanoseconds,
            'sd_slide_duration': settings.sd_slide_duration,
            'sd_video_fps': settings.sd_video_fps,
            'sd_playlist_refresh_rate': settings.sd_playlist_refresh_rate
        }
        
        if not no_wifi_update:
            settings_dict['wifi_ssid'] = settings.wifi_ssid
            settings_dict['wifi_password'] = settings.wifi_password
        
        # Trigger push if client IP is known (check telemetry first, then DB)
        client_ip = get_client_ip()
            
        if client_ip:
            threading.Thread(target=push_settings_to_client, args=(settings_dict, client_ip)).start()
            
        return jsonify({'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# --- SD Card Routes ---
@app.route('/api/sd/files', methods=['GET'])
@login_required
def list_sd_files():
    try:
        # Try to get client files first
        client_ip = get_client_ip()
        
        if client_ip:
            try:
                url = f"http://{client_ip}:5000/api/sd/files"
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    return jsonify({'files': data.get('files', []), 'source': 'client'})
            except Exception as e:
                print(f"Failed to fetch files from client: {e}")

        # Fallback to local files
        files = []
        if os.path.exists(SD_UPLOAD_FOLDER):
            for f in os.listdir(SD_UPLOAD_FOLDER):
                if os.path.isfile(os.path.join(SD_UPLOAD_FOLDER, f)):
                    files.append(f)
        return jsonify({'files': files, 'source': 'local'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sd/upload', methods=['POST'])
@login_required
def upload_sd_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    mode = request.form.get('mode', 'both') # Default to 'both' if not specified
    pos1 = request.form.get('position_1')
    pos2 = request.form.get('position_2')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = file.filename
        filepath = os.path.join(SD_UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Try to push to client if connected (or use last known IP)
        client_ip = get_client_ip()

        if client_ip:
            threading.Thread(target=push_file_to_client, args=(filepath, filename, client_ip, mode, pos1, pos2)).start()
            return jsonify({'message': 'File uploaded and push started'})
        
        return jsonify({'message': 'File uploaded (Client not connected, stored locally)'})

@app.route('/api/sd/files/<filename>', methods=['DELETE'])
@login_required
def delete_sd_file(filename):
    try:
        # Delete locally
        filepath = os.path.join(SD_UPLOAD_FOLDER, filename)
        local_deleted = False
        if os.path.exists(filepath):
            os.remove(filepath)
            local_deleted = True
            
        # Propagate to client
        client_ip = get_client_ip()

        client_msg = ""
        if client_ip:
            url = f"http://{client_ip}:5000/api/sd/files/{filename}"
            try:
                resp = requests.delete(url, timeout=5)
                if resp.status_code == 200:
                    client_msg = " and deleted from client"
                else:
                    client_msg = f" but client returned {resp.status_code}"
            except Exception as e:
                client_msg = f" but failed to contact client: {e}"
        
        if local_deleted:
            return jsonify({'message': f'File deleted locally{client_msg}'})
        elif "deleted from client" in client_msg:
             return jsonify({'message': f'File not found locally, but{client_msg}'})
        else:
            return jsonify({'error': 'File not found locally'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sd/play', methods=['POST'])
@login_required
def play_sd_card():
    try:
        # Try to push to client if connected (or use last known IP)
        client_ip = get_client_ip()

        if client_ip:
            url = f"http://{client_ip}:5000/api/sd/play"
            try:
                requests.post(url, timeout=5)
                return jsonify({'message': 'Playback started'})
            except Exception as e:
                return jsonify({'error': f'Failed to contact client: {e}'}), 500
        
        return jsonify({'error': 'Client not connected'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sd/stop', methods=['POST'])
@login_required
def stop_sd_card():
    try:
        # Try to push to client if connected (or use last known IP)
        client_ip = get_client_ip()

        if client_ip:
            url = f"http://{client_ip}:5000/api/sd/stop"
            try:
                requests.post(url, timeout=5)
                return jsonify({'message': 'Playback stopped'})
            except Exception as e:
                return jsonify({'error': f'Failed to contact client: {e}'}), 500
        
        return jsonify({'error': 'Client not connected'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def push_file_to_client(filepath, filename, client_ip, mode='both', pos1=None, pos2=None):
    """
    Pushes a file to the client's SD card storage.
    """
    url = f"http://{client_ip}:5000/api/sd/upload"
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            data = {'mode': mode}
            if pos1 is not None: data['position_1'] = pos1
            if pos2 is not None: data['position_2'] = pos2
            
            print(f"Pushing file {filename} to {url} with mode {mode}")
            response = requests.post(url, files=files, data=data, timeout=10)
            if response.status_code == 200:
                print(f"Successfully pushed {filename}")
            else:
                print(f"Failed to push {filename}: {response.text}")
    except Exception as e:
        print(f"Error pushing file: {e}")

def push_settings_to_client(settings, client_ip):
    """
    Pushes settings to the client.
    """
    url = f"http://{client_ip}:5000/api/config"
    try:
        print(f"Pushing settings to {url}")
        response = requests.post(url, json=settings, timeout=5)
        if response.status_code == 200:
            print("Successfully pushed settings")
        else:
            print(f"Failed to push settings: {response.text}")
    except Exception as e:
        print(f"Error pushing settings: {e}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
