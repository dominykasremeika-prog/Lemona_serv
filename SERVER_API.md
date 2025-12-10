# Server API Documentation

## Overview
This document describes the API endpoints available on the Lemona Server.

## Authentication
Most endpoints require authentication. The session cookie is used for authentication after logging in via the web interface.

## Endpoints

### 1. Client Configuration
**Endpoint:** `GET /api/client-config`
**Access:** Public (Used by Raspberry Pi)
**Description:** Returns the configuration settings for the client.

**Response:**
```json
{
  "brightness": 50,
  "gpio_slowdown": 4,
  "hardware_pulsing": true,
  "matrix_chain": 2,
  "matrix_cols": 64,
  "matrix_parallel": 1,
  "matrix_pwm_lsb_nanoseconds": 130,
  "matrix_rows": 64,
  "polling_rate": 1.0,
  "position_1": 0,
  "position_2": 0,
  "request_send_rate": 1.0,
  "sd_playlist_refresh_rate": 10.0,
  "sd_slide_duration": 30.0,
  "sd_video_fps": 30.0,
  "wifi_password": "",
  "wifi_ssid": ""
}
```

### 2. Admin Settings
**Endpoint:** `GET /api/admin/settings`
**Access:** Admin Required
**Description:** Returns current settings and telemetry data.

**Endpoint:** `POST /api/admin/settings`
**Access:** Admin Required
**Description:** Updates the server settings and pushes them to the connected client.

**Request Body:**
```json
{
  "brightness": 50,
  "polling_rate": 1.0,
  "gpio_slowdown": 4,
  "matrix_rows": 64,
  "matrix_cols": 64,
  "matrix_chain": 2,
  "matrix_parallel": 1,
  "matrix_pwm_lsb_nanoseconds": 130,
  "sd_slide_duration": 30.0,
  "sd_video_fps": 30.0,
  "sd_playlist_refresh_rate": 10.0,
  "position_1": 0,
  "position_2": 0,
  "request_send_rate": 1.0,
  "wifi_ssid": "MyWiFi",
  "wifi_password": "password",
  "hardware_pulsing": true,
  "use_sd_card_fallback": true
}
```

### 3. SD Card Management
**Endpoint:** `GET /api/sd/files`
**Access:** Login Required
**Description:** Lists files stored on the server for SD card sync.

**Endpoint:** `POST /api/sd/upload`
**Access:** Login Required
**Description:** Uploads a file to the server and pushes it to the client.

**Request:** `multipart/form-data`
- `file`: The file to upload.
- `mode`: (Optional) The display mode for the file (`matrix_a`, `matrix_b`, `both`, `split`). Defaults to `both`.

**Endpoint:** `DELETE /api/sd/files/<filename>`
**Access:** Login Required
**Description:** Deletes a file from the server and sends a request to delete it from the client's SD card.

**Endpoint:** `POST /api/sd/play`
**Access:** Login Required
**Description:** Commands the client to start playing files from the SD card.

**Endpoint:** `POST /api/sd/stop`
**Access:** Login Required
**Description:** Commands the client to stop playing files from the SD card.

### 4. Live Control
**Endpoint:** `POST /api/upload`
**Access:** Approved User Required
**Description:** Uploads content for immediate live playback.

**Request:** `multipart/form-data`
- `mode`: `matrix_a`, `matrix_b`, `both`, `split`, `separate`
- `file_a`: Primary file
- `file_b`: Secondary file (for `separate` mode)

**Endpoint:** `POST /api/draw`
**Access:** Approved User Required
**Description:** Uploads a drawing from the canvas.

**Request Body:**
```json
{
  "image": "data:image/png;base64,..."
}
```

**Endpoint:** `POST /api/clear`
**Access:** Approved User Required
**Description:** Clears the matrix display.

### 5. Telemetry
**Endpoint:** `POST /api/telemetry`
**Access:** Public (Used by Raspberry Pi)
**Description:** Receives status updates from the client.

**Request Body:**
```json
{
  "network": {
    "ip": "192.168.1.100",
    "ssid": "MyWiFi",
    "type": "wifi"
  },
  "refresh_rate": 60.0
}
```
