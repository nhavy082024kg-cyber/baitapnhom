#include <Arduino.h>
#include "HX711.h"

namespace Pinout
{
    constexpr uint8_t HX711_DOUT = 16;
    constexpr uint8_t HX711_SCK = 4;
    constexpr uint8_t SOLENOID_VALVE = 23;
    constexpr uint8_t LEAK_SENSOR = 36;
    constexpr uint8_t DOOR_SENSOR = 18;
}

namespace Config
{
    constexpr float TARGET_WEIGHT_G = 0.080f;
    constexpr float CALIB_FACTOR = 420.5f;
    constexpr int LEAK_THRESHOLD = 1500;
    constexpr uint32_t MAX_PULSE_MS = 1000;
}

enum class SystemState
{
    NORMAL,
    MAINTENANCE,
    ERROR_LEAK,
    ERROR_DOOR
};

class SensorManager
{
private:
    HX711 scale;

public:
    void begin()
    {
        pinMode(Pinout::LEAK_SENSOR, INPUT);
        pinMode(Pinout::DOOR_SENSOR, INPUT_PULLUP);

        scale.begin(
            Pinout::HX711_DOUT,
            Pinout::HX711_SCK
        );

        scale.set_scale(Config::CALIB_FACTOR);
        scale.tare();
    }

    float getWeight()
    {
        return scale.is_ready()
               ? scale.get_units(5)
               : -1.0f;
    }

    SystemState checkSafety(bool isMaintenance)
    {
        if (
            analogRead(Pinout::LEAK_SENSOR)
            > Config::LEAK_THRESHOLD
        )
        {
            return SystemState::ERROR_LEAK;
        }

        if (
            digitalRead(Pinout::DOOR_SENSOR) == HIGH
            && !isMaintenance
        )
        {
            return SystemState::ERROR_DOOR;
        }

        return SystemState::NORMAL;
    }
};
