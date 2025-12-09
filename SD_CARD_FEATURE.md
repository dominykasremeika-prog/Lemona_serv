# SD Card Feature Documentation

This document describes the new features related to SD card file management and fallback behavior for the Raspberry Pi client.

## Overview

The system now supports uploading files (images/videos) to the server, which are then pushed to the Raspberry Pi's SD card. A new configuration setting allows the Raspberry Pi to "fallback" to displaying these files when it has no active content to show (e.g., when the screen is cleared or black).

## Admin UI Changes

### SD Card Tab
A new "SD Card" tab has been added to the Admin interface.
- **Upload**: Allows admins to select and upload files.
- **File List**: Displays files currently stored on the server (and synced to the client).
- **Delete**: Allows removing files.

### Settings Tab
- **Enable SD Card Fallback**: A new checkbox in the Client Configuration section. When checked, the client should play content from its local SD card when idle.
- **Position 1 (Orientation)**: The orientation setting for Matrix 1 is now a rotation button that increments by 90 degrees (0 -> 90 -> 180 -> 270 -> 0).

## API Endpoints

### 1. List SD Files
**Endpoint:** `GET /api/sd/files`
**Access:** Login Required
**Description:** Returns a list of files stored in the server's SD upload directory.

**Response:**
```json
{
  "files": ["image1.png", "video.mp4"]
}
```

### 2. Upload SD File
**Endpoint:** `POST /api/sd/upload`
**Access:** Login Required
**Description:** Uploads a file to the server. The server saves it locally and attempts to push it to the connected client.

**Request:** `multipart/form-data` with field `file`.

**Response:**
```json
{
  "message": "File uploaded and push started"
}
```

### 3. Delete SD File
**Endpoint:** `DELETE /api/sd/files/<filename>`
**Access:** Login Required
**Description:** Deletes a file from the server.

**Response:**
```json
{
  "message": "File deleted"
}
```

### 4. Client Push Endpoint (On Raspberry Pi)
**Endpoint:** `POST /api/sd/upload` (on Client Port 5000)
**Description:** The server uses this endpoint to push uploaded files to the client.

## Configuration Updates

The `ClientSettings` model and `/api/admin/settings` endpoints have been updated to include:
- `use_sd_card_fallback` (boolean): Controls whether the client uses SD card content when idle.
