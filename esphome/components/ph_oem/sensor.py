"""ESPHome "glue" for the pH OEM driver.

ESPHome turns a YAML file into C++ firmware. For a custom part like this one, ESPHome needs to
be told two things, and this file tells it both:

  1. CONFIG_SCHEMA: which options are allowed under `- platform: ph_oem` in the YAML.
  2. to_code():     which C++ to generate from those options.

The C++ class itself is in ph_oem.h, next to this file. In the YAML it is used like this:

    sensor:
      - platform: ph_oem
        id: ph
        name: pH
        temperature_sensor: tilt_temp     # optional: where the beer temperature comes from
"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import i2c, sensor

# This driver only works if the YAML also sets up an I2C bus.
DEPENDENCIES = ["i2c"]

CONF_TEMPERATURE_SENSOR = "temperature_sensor"

# Tell ESPHome's code generator about the C++ class: its namespace, its name, and the ESPHome
# classes it is built on (these must match the class line in ph_oem.h).
ph_oem_ns = cg.esphome_ns.namespace("ph_oem")
PHOEMSensor = ph_oem_ns.class_(
    "PHOEMSensor", sensor.Sensor, cg.PollingComponent, i2c.I2CDevice
)

# The allowed YAML options, built by combining ready-made pieces:
CONFIG_SCHEMA = (
    # the standard sensor options (name, id, filters...) with sensible defaults for pH
    sensor.sensor_schema(
        PHOEMSensor,
        accuracy_decimals=2,
        device_class="ph",              # lets Home Assistant know this number is a pH
        state_class="measurement",
        icon="mdi:ph",
    )
    # our one extra option: the id of another sensor that supplies the temperature
    .extend({cv.Optional(CONF_TEMPERATURE_SENSOR): cv.use_id(sensor.Sensor)})
    # "never" = don't read on a timer; the YAML asks for a reading when it wants one
    .extend(cv.polling_component_schema("never"))
    # the I2C address option, defaulting to the chip's factory address 0x65
    .extend(i2c.i2c_device_schema(0x65))
)


async def to_code(config):
    """Generate the C++ that creates and wires up one PHOEMSensor."""
    var = await sensor.new_sensor(config)           # create the object and register it as a sensor
    await cg.register_component(var, config)        # so ESPHome calls its setup() and update()
    await i2c.register_i2c_device(var, config)      # connect it to the I2C bus at its address
    if CONF_TEMPERATURE_SENSOR in config:
        # Hand the temperature sensor to the driver (calls set_temperature_sensor in ph_oem.h).
        cg.add(
            var.set_temperature_sensor(
                await cg.get_variable(config[CONF_TEMPERATURE_SENSOR])
            )
        )
