# LED Matrix Server API Documentation

This documentation describes the API endpoints available for controlling and retrieving data from the LED Matrix Server. This is particularly useful for integrating with a Raspberry Pi or other hardware controllers.

## Base URL

Assuming the server is running on `http://<server-ip>:5000`.

## Endpoints

### 1. Get Matrix Image

Retrieves the current image being displayed on a specific matrix. This is the primary endpoint for the Raspberry Pi to poll.

*   **URL**: `/api/matrix/<matrix_id>`
*   **Method**: `GET`
*   **URL Params**:
    *   `matrix_id`: `a` for the left matrix, `b` for the right matrix.
*   **Response**: Returns a PNG image file.
*   **Example (Python/Requests)**:

    ```python
    import requests
    from PIL import Image
    from io import BytesIO

    # Fetch image for Matrix A
    response = requests.get('http://<server-ip>:5000/api/matrix/a')
    
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        # Now you can display 'img' on your hardware matrix
        # e.g., matrix.SetImage(img)
    ```

### 2. Upload Image (Control)

Uploads an image or sets the display mode. This is used by the Web UI but can be used programmatically.

*   **URL**: `/api/upload`
*   **Method**: `POST`
*   **Form Data**:
    *   `mode`: One of `matrix_a`, `matrix_b`, `both`, `split`, `separate`.
    *   `file_a`: The image file for Matrix A (or the main image).
    *   `file_b`: The image file for Matrix B (only required for `separate` mode).
*   **Response**: JSON object with status.

### 3. Draw (Control)

Sends a base64 encoded image from the drawing canvas.

*   **URL**: `/api/draw`
*   **Method**: `POST`
*   **JSON Body**:
    *   `image`: Base64 encoded string of the image (e.g., `data:image/png;base64,...`).

## Raspberry Pi Integration Example

Here is a simple script you can run on your Raspberry Pi to continuously update the matrices from the server.

```python
import time
import requests
from io import BytesIO
from PIL import Image
# Import your matrix library, e.g.:
# from rgbmatrix import RGBMatrix, RGBMatrixOptions

def fetch_and_display(matrix_url, led_matrix_instance):
    try:
        response = requests.get(matrix_url, timeout=1)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img = img.convert('RGB')
            # led_matrix_instance.SetImage(img)
            print(f"Updated from {matrix_url}")
    except Exception as e:
        print(f"Error fetching {matrix_url}: {e}")

def main():
    # Setup your matrix hardware here...
    
    SERVER_IP = "192.168.1.100" # Change to your PC's IP
    
    while True:
        # Update Matrix A
        fetch_and_display(f"http://{SERVER_IP}:5000/api/matrix/a", matrix_a_instance)
        
        # Update Matrix B
        fetch_and_display(f"http://{SERVER_IP}:5000/api/matrix/b", matrix_b_instance)
        
        time.sleep(0.1) # Adjust refresh rate

if __name__ == "__main__":
    main()
```
