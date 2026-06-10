#ifndef PHLOAT_COMMON_H
#define PHLOAT_COMMON_H

#include <Arduino.h>
#include <esp_now.h>
#include <Preferences.h>

#define PHLOAT_UPLOAD_HEADER "X-pHloat-Token"
#define PHLOAT_MIN_AP_PASSWORD_LEN 12
#define PHLOAT_WEAK_PASSWORD "phloat123"

#pragma pack(push, 1)
struct SensorData {
  char magic[4];           // "PH01"
  char deviceName[32];
  float pH;
  float temperature;
  uint32_t readingNumber;
  uint64_t timestamp;
  uint8_t senderMac[6];
};
#pragma pack(pop)

static const char PHLOAT_SENSOR_MAGIC[4] = {'P', 'H', '0', '1'};

inline void phloat_init_sensor_data(SensorData &data) {
  memcpy(data.magic, PHLOAT_SENSOR_MAGIC, 4);
  memset(data.deviceName, 0, sizeof(data.deviceName));
  data.pH = 0.0f;
  data.temperature = 0.0f;
  data.readingNumber = 0;
  data.timestamp = 0;
  memset(data.senderMac, 0, sizeof(data.senderMac));
}

inline bool phloat_valid_sensor_packet(const uint8_t *payload, int len) {
  if (len != (int)sizeof(SensorData)) return false;
  return memcmp(payload, PHLOAT_SENSOR_MAGIC, 4) == 0;
}

inline void phloat_sanitize_device_name(const char *in, char *out, size_t outSize) {
  if (!in || !out || outSize == 0) return;
  size_t j = 0;
  for (size_t i = 0; in[i] != '\0' && j + 1 < outSize; i++) {
    char c = in[i];
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
        (c >= '0' && c <= '9') || c == '-' || c == '_') {
      out[j++] = c;
    }
  }
  out[j] = '\0';
  if (j == 0) {
    strlcpy(out, "Sensor", outSize);
  }
}

inline bool phloat_is_weak_password(const char *password) {
  if (!password) return true;
  if (strlen(password) < PHLOAT_MIN_AP_PASSWORD_LEN) return true;
  return strcmp(password, PHLOAT_WEAK_PASSWORD) == 0;
}

inline void phloat_generate_hex_token(char *out, size_t outLen) {
  if (!out || outLen < 17) return;
  const char *hex = "0123456789abcdef";
  for (size_t i = 0; i + 1 < outLen && i < 32; i++) {
    out[i] = hex[esp_random() % 16];
  }
  out[min(outLen - 1, (size_t)32)] = '\0';
}

inline bool phloat_apply_pmk(const char *pmkHex) {
  if (!pmkHex || strlen(pmkHex) != 32) return false;
  uint8_t pmkBytes[16];
  for (int i = 0; i < 16; i++) {
    char pair[3] = {pmkHex[i * 2], pmkHex[i * 2 + 1], '\0'};
    char *end = nullptr;
    unsigned long v = strtoul(pair, &end, 16);
    if (end == pair || v > 255) return false;
    pmkBytes[i] = (uint8_t)v;
  }
  return esp_now_set_pmk(pmkBytes) == ESP_OK;
}

inline void phloat_mac_to_string(const uint8_t *mac, char *out, size_t outLen) {
  snprintf(out, outLen, "%02X:%02X:%02X:%02X:%02X:%02X",
           mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

inline bool phloat_parse_mac(const char *macStr, uint8_t *outMac) {
  if (!macStr || !outMac) return false;
  int values[6];
  if (sscanf(macStr, "%x:%x:%x:%x:%x:%x",
             &values[0], &values[1], &values[2],
             &values[3], &values[4], &values[5]) != 6) {
    return false;
  }
  for (int i = 0; i < 6; i++) {
    if (values[i] < 0 || values[i] > 255) return false;
    outMac[i] = (uint8_t)values[i];
  }
  return true;
}

inline bool phloat_mac_allowed(Preferences &prefs, const uint8_t *mac, bool autoLearn) {
  char macStr[18];
  phloat_mac_to_string(mac, macStr, sizeof(macStr));

  prefs.begin("phloat-sec", false);
  String allowlist = prefs.getString("sensorMacs", "");
  if (allowlist.length() == 0) {
    if (autoLearn) {
      prefs.putString("sensorMacs", macStr);
      prefs.end();
      Serial.printf("Auto-registered sensor MAC: %s\n", macStr);
      return true;
    }
    prefs.end();
    Serial.println("Rejected ESP-NOW packet: no sensor MAC allowlist configured");
    return false;
  }

  bool allowed = allowlist.indexOf(macStr) >= 0;
  if (!allowed && autoLearn) {
    allowlist += ",";
    allowlist += macStr;
    prefs.putString("sensorMacs", allowlist);
    allowed = true;
    Serial.printf("Auto-registered sensor MAC: %s\n", macStr);
  }
  prefs.end();
  return allowed;
}

#endif
