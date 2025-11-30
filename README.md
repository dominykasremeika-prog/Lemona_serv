# LED Matrix Control Web Interface

This project provides a web interface to control two 64x64 LED matrices.

## Features

- **Draw Tab**: Draw directly on a 128x64 canvas (representing two 64x64 matrices side-by-side).
  - Tools: Brush, Bucket Fill, Color Picker, Brush Size.
- **Upload Tab**: Upload Images or GIFs.
  - **Modes**:
    - **Matrix A**: Display on the first matrix.
    - **Matrix B**: Display on the second matrix.
    - **Both**: Clone the image to both matrices.
    - **Split**: Span the image across both matrices (128x64).
    - **Separate**: Upload two different files, one for each matrix.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Run the server:
    ```bash
    python main.py
    ```

3.  Open your browser and go to `http://localhost:5000`.

## Hardware Integration

The `MatrixController` class in `main.py` is currently a mock. To control real hardware:

1.  Import your LED matrix library (e.g., `rgbmatrix` for Raspberry Pi).
2.  Update the `MatrixController` methods (`display_on_a`, `display_on_b`, etc.) to send the `PIL.Image` data to your hardware.
