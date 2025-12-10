# Lemona Server API Documentation

This document details the API endpoints available in the Lemona Server (`main.py`). These endpoints are used by the web interface and the client device (Raspberry Pi) to communicate, transfer files, and manage settings.

## Authentication

Most endpoints require authentication.
- **Web UI Endpoints**: Require a user session (login via `/login`).
- **Client Endpoints**: Some are open for the device to poll, others are protected.
- **Admin Endpoints**: Require the user to have `is_admin=True`.

---

## 1. Public / Client Endpoints

These endpoints are primarily used by the Raspberry Pi client or for initial access.

### `GET /api/matrix/<a>`
Retrieves the current image frame for a specific matrix.
- **Parameters**: `a` (path parameter) - either `'a'` or `'b'`.
- **Returns**: PNG image file.
- **Usage**: The Raspberry Pi polls this endpoint to get the live image to display.

### `POST /api/telemetry`
Receives status updates from the Raspberry Pi.
- **Body (JSON)**:
  ```json
  {
    "network": {
      "ip": "192.168.1.105",
      "ssid": "MyWiFi",
      "type": "wifi"
    },
    "refresh_rate": 60.0
  }
  ```
- **Returns**: `{"status": "success"}`
- **Usage**: The Pi sends a heartbeat to this endpoint to report its IP and status.

### `GET /api/client-config`
Allows the Raspberry Pi to fetch its configuration settings.
- **Returns**: JSON object containing all client settings (polling rate, brightness, matrix hardware config, etc.).
- **Usage**: The Pi calls this on startup or periodically to sync settings.

---

## 2. User / Control Endpoints

These endpoints require a logged-in user with an approved account.

### `GET /api/status`
Returns the connection status of the matrices.
- **Returns**: `{"a": true/false, "b": true/false}`
- **Usage**: Used by the web UI to show the "Raspberry Pi" connection indicator.

### `POST /api/clear`
Clears the display (sets it to black).
- **Returns**: `{"status": "success", "message": "Matrices cleared"}`

### `POST /api/draw`
Uploads a drawing from the canvas.
- **Body (JSON)**: `{"image": "base64_encoded_image_string"}`
- **Returns**: `{"status": "success", "message": "Drawing displayed"}`
- **Side Effect**: Pushes the drawing immediately to the client if connected.

### `POST /api/upload`
Uploads image or video files to be displayed immediately.
- **Form Data**:
  - `mode`: `matrix_a`, `matrix_b`, `both`, `split`, or `separate`.
  - `file_a`: File for Matrix A (or main file).
  - `file_b`: File for Matrix B (only for `separate` mode).
- **Returns**: JSON status message.
- **Side Effect**: Pushes the content to the client for immediate playback.

---

## 3. SD Card Management Endpoints

Endpoints for managing files stored on the Raspberry Pi's SD card.

### `GET /api/sd/files`
Lists files stored on the SD card.
- **Returns**: `{"files": ["file1.mp4", "image.png"], "source": "client" or "local"}`
- **Behavior**: Tries to fetch the list from the connected Pi. If unreachable, falls back to the server's local cache.

### `POST /api/sd/upload`
Uploads a file to be stored on the SD card.
- **Form Data**:
  - `file`: The file to upload.
  - `mode`: Display mode (`matrix_a`, `both`, etc.).
  - `position_1`: Rotation/Position setting for Matrix 1.
  - `position_2`: Position setting for Matrix 2.
- **Returns**: JSON status message.
- **Behavior**: Uploads to server, then pushes to the client.

### `DELETE /api/sd/files/<filename>`
Deletes a file from the SD card.
- **Parameters**: `filename` (path parameter).
- **Returns**: JSON status message.
- **Behavior**: Deletes locally and sends a delete request to the client.

### `POST /api/sd/play`
Starts playback of the SD card playlist on the client.
- **Returns**: JSON status message.

### `POST /api/sd/stop`
Stops SD card playback on the client.
- **Returns**: JSON status message.

---

## 4. Admin Endpoints

These endpoints require `admin_required` (User must be Admin).

### `GET /api/admin/users`
Lists all registered users.
- **Returns**: JSON array of user objects.

### `POST /api/admin/approve/<user_id>`
Approves a newly registered user.

### `POST /api/admin/promote/<user_id>`
Promotes a user to Admin.

### `POST /api/admin/kick/<user_id>`
Deletes a user account.

### `GET /api/admin/settings`
Retrieves the global server/client settings.
- **Returns**: JSON object with `settings` (config) and `telemetry` (live data).

### `POST /api/admin/settings`
Updates the global settings.
- **Body (JSON)**: Any subset of settings fields (e.g., `brightness`, `polling_rate`, `wifi_ssid`, `no_wifi_update`).
- **Returns**: JSON success message.
- **Side Effect**: Pushes the new configuration to the client immediately.

---

## 5. Authentication Routes

Standard web routes for user management.

- `GET/POST /register`: Create a new account.
- `GET/POST /login`: Log in.
- `GET /logout`: Log out.
