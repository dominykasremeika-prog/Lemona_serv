# Server API Documentation

This document describes the new API endpoints implemented on the server to support client configuration and telemetry.

## Client Endpoints (For Raspberry Pi)

### 1. Report Telemetry
**Endpoint:** `POST /api/telemetry`
**Description:** Used by the client to report its current status and metrics to the server.

**Request Body:**
```json
{
  "polling_rate": 1.0,
  "gpio_slowdown": 4,
  "network": {
    "type": "WiFi",
    "ssid": "MyWiFiNetwork",
    "ip": "192.168.1.105"
  },
  "refresh_rate": 60,
  "hardware_pulsing": true,
  "brightness": 50,
  "position_1": 0,
  "position_2": 0,
  "request_send_rate": 1.0
}
```

**Response:**
- `200 OK`: `{"status": "success"}`

---

### 2. Fetch Configuration
**Endpoint:** `GET /api/client-config`
**Description:** Used by the client to fetch the desired configuration settings from the server. The client should poll this endpoint periodically or after sending telemetry to check for updates.

**Response Body:**
```json
{
  "polling_rate": 1.0,
  "gpio_slowdown": 4,
  "hardware_pulsing": true,
  "brightness": 50,
  "position_1": 0,
  "position_2": 0,
  "request_send_rate": 1.0,
  "wifi_ssid": "MyNetwork",
  "wifi_password": "secretpassword"
}
```

## Admin Endpoints (For Web Interface)

### 3. Get Settings & Telemetry
**Endpoint:** `GET /api/admin/settings`
**Description:** Retrieves the current desired settings and the latest telemetry data received from the client.
**Auth Required:** Yes (Admin)

**Response Body:**
```json
{
  "settings": {
    "polling_rate": 1.0,
    "gpio_slowdown": 4,
    "hardware_pulsing": true,
    "brightness": 50,
    "position_1": 0,
    "position_2": 0,
    "request_send_rate": 1.0,
    "wifi_ssid": "MyNetwork",
    "wifi_password": "secretpassword"
  },
  "telemetry": { ... },
  "telemetry_age": 2.5
}
```

---

### 4. Update Settings
**Endpoint:** `POST /api/admin/settings`
**Description:** Updates the desired configuration settings, including WiFi credentials for the client.
**Auth Required:** Yes (Admin)

**Request Body:**
```json
{
  "polling_rate": 2.0,
  "brightness": 80,
  "wifi_ssid": "NewNetwork",
  "wifi_password": "NewPassword"
  // ... any other setting fields
}
```

**Response:**
- `200 OK`: `{"message": "Settings updated successfully"}`
