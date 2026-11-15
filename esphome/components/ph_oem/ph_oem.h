// ph_oem.h: an ESPHome driver for the Atlas Scientific pH OEM circuit.
//
// WHAT THE CHIP IS
//   The pH OEM is a small module that does the hard analog work of reading a glass pH probe
//   and hands back a finished pH number. The microcontroller talks to it over I2C, a two-wire
//   bus (data + clock) on which every chip has an address. This chip's address is 0x65.
//
// HOW YOU TALK TO IT
//   The chip looks like a short list of numbered storage slots called "registers". You control
//   it by writing a number into a register, and read results by reading a register.
//   Multi-byte numbers are stored most significant byte first, and scaled to avoid decimals:
//   a pH of 4.312 is stored as the whole number 4312 (pH x 1000).
//   Register numbers are from the pH OEM datasheet V4.7, pages 17-24.
//
// HOW ESPHOME USES THIS FILE
//   ESPHome builds firmware from a YAML file. sensor.py (next to this file) tells ESPHome how
//   the YAML options map onto the C++ class below. ESPHome then calls:
//       setup()   once, at power-up
//       update()  each time a reading is wanted
#pragma once

#include <cmath>
#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include "esphome/components/i2c/i2c.h"
#include "esphome/components/sensor/sensor.h"

namespace esphome {
namespace ph_oem {

// The label that appears in front of this driver's log messages.
static const char *const TAG = "ph_oem";

// The registers this driver uses.
enum : uint8_t {
  REG_LED = 0x05,          // 1 = blink the on-board LED at each reading, 0 = LED off
  REG_ACTIVE = 0x06,       // 1 = take a reading every 420 ms, 0 = hibernate (stop reading)
  REG_NEW_READING = 0x07,  // the chip sets this to 1 when a new reading is ready; we set it back to 0
  REG_CAL_VALUE = 0x08,    // 4 bytes: the pH of the calibration buffer, x 1000
  REG_CAL_REQUEST = 0x0C,  // write 1 = clear calibration, 2 = low point, 3 = mid point, 4 = high point
  REG_CAL_CONFIRM = 0x0D,  // which points are calibrated: bit 0 = low, bit 1 = mid, bit 2 = high
  REG_TEMP_COMP = 0x0E,    // 4 bytes: the liquid's temperature in Celsius, x 100
  REG_PH = 0x16,           // 4 bytes: the pH reading, x 1000
};

// The class inherits three sets of abilities from ESPHome:
//   sensor::Sensor     it can publish a number (the pH)
//   PollingComponent   it is asked for a reading via update()
//   i2c::I2CDevice     it can read and write registers on the I2C bus
class PHOEMSensor : public sensor::Sensor, public PollingComponent, public i2c::I2CDevice {
 public:
  // Called from sensor.py: which sensor supplies the beer temperature (the Tilt).
  void set_temperature_sensor(sensor::Sensor *s) { this->temperature_ = s; }

  // Runs once at power-up.
  // On the pHloat board the chip is only powered while the ESP32 is awake, so it starts
  // from cold every time: LED off (saves a little battery), then start taking readings.
  // If the chip does not answer, mark this component failed so the log says why.
  void setup() override {
    if (!this->write_byte(REG_LED, 0) || !this->write_byte(REG_ACTIVE, 1)) {
      ESP_LOGE(TAG, "No answer from the pH OEM. Is PH_PWR high?");
      this->mark_failed();
    }
  }

  // Prints this component's settings in the start-up log.
  void dump_config() override {
    LOG_SENSOR("", "Atlas pH OEM", this);
    LOG_I2C_DEVICE(this);
  }

  // Take one reading.
  // Why temperature matters: a pH probe's output voltage changes with temperature, so the
  // chip needs to know how warm the beer is to convert voltage to pH correctly. This is
  // called "temperature compensation".
  void update() override {
    // Step 1: tell the chip the beer temperature, if we have a sensible one (0-100 C).
    if (this->temperature_ != nullptr && this->temperature_->has_state()) {
      float t = this->temperature_->state;
      if (t > 0.0f && t < 100.0f)
        this->write_u32_(REG_TEMP_COMP, (uint32_t) lroundf(t * 100.0f));
    }
    // Step 2: clear the "new reading" flag, so the next time it reads 1 we know the reading
    // was taken AFTER the temperature above arrived.
    this->write_byte(REG_NEW_READING, 0);
    // Step 3: come back in 900 ms (two of the chip's 420 ms reading periods) and collect it.
    // set_timeout runs the code later without blocking the rest of the firmware meanwhile.
    this->set_timeout("read", 900, [this]() {
      uint8_t fresh = 0, b[4];
      if (!this->read_bytes(REG_NEW_READING, &fresh, 1) || fresh != 1 || !this->read_bytes(REG_PH, b, 4)) {
        ESP_LOGW(TAG, "No fresh reading from the pH OEM");
        return;
      }
      // Join the four bytes into one 32-bit number (first byte is the most significant),
      // then divide by 1000 to get back to pH.
      int32_t raw = (int32_t) (((uint32_t) b[0] << 24) | ((uint32_t) b[1] << 16) | ((uint32_t) b[2] << 8) | b[3]);
      this->publish_state(raw / 1000.0f);
    });
  }

  // Calibrate one point. Put the probe in a buffer solution of known pH, wait for the reading
  // to settle, then call this with that pH.
  //   point: 2 = low (pH 4), 3 = mid (pH 7), 4 = high (pH 10).
  // The first point calibrated must be the mid point (datasheet p21).
  // The chip remembers its calibration when the power is removed.
  void calibrate(uint8_t point, float buffer_ph) {
    this->write_u32_(REG_CAL_VALUE, (uint32_t) lroundf(buffer_ph * 1000.0f));   // "the buffer is pH X"
    this->write_byte(REG_CAL_REQUEST, point);                                   // "calibrate this point now"
    ESP_LOGI(TAG, "Calibration request %u at pH %.2f", point, buffer_ph);
  }

  // Forget every calibration point.
  void clear_calibration() { this->write_byte(REG_CAL_REQUEST, 1); }

  // Which points are calibrated, as one number 0-7:
  //   0 = none, 2 = mid only, 3 = mid + low, 6 = mid + high, 7 = all three.
  // Returns NAN ("not a number") if the chip does not answer.
  float calibration_status() {
    uint8_t v;
    return this->read_bytes(REG_CAL_CONFIRM, &v, 1) ? (float) (v & 0x07) : NAN;
  }

 protected:
  // Write a 32-bit number into four consecutive registers, most significant byte first.
  // "v >> 24" shifts the number right by 24 bits, leaving its top byte, and so on down.
  void write_u32_(uint8_t reg, uint32_t v) {
    uint8_t b[4] = {(uint8_t) (v >> 24), (uint8_t) (v >> 16), (uint8_t) (v >> 8), (uint8_t) v};
    this->write_bytes(reg, b, 4);
  }

  sensor::Sensor *temperature_{nullptr};   // the beer temperature source, or nullptr if none was given
};

}  // namespace ph_oem
}  // namespace esphome
