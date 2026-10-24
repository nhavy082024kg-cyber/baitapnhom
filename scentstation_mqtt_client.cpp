#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// Thông tin Wi-Fi và MQTT Broker (Demo public broker)
const char* WIFI_SSID = "Your_WiFi_Name";
const char* WIFI_PASSWORD = "Your_WiFi_Password";
const char* BROKER_URL = "broker.hivemq.com";
const int BROKER_PORT = 1883;

const String MACHINE_ID = "SS-001";
const String BASE_TOPIC = "scentstation/" + MACHINE_ID;
const String CLIENT_ID = "ss-cpp-demo-01";

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// Cấu trúc dữ liệu 5 Slot nước hoa (Chanel, YSL, Dior, Gucci, Hermes)
struct Slot {
  int slot_id;
  String perfume;
  bool enabled;
  int remaining_sprays;
  String sensor_status;
};

Slot slots[5] = {
  {1, "Chanel", true, 35, "OK"},
  {2, "YSL", true, 28, "OK"},
  {3, "Dior", true, 30, "OK"},
  {4, "Gucci", true, 42, "OK"},
  {5, "Hermes", true, 31, "OK"}
};

unsigned long lastTelemetryTime = 0;
const long telemetryInterval = 10000; // Gửi telemetry mỗi 10 giây

void connectWiFi() {
  Serial.print("[WIFI] Dang ket noi toi ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WIFI] Da ket noi WiFi thanh cong!");
}

// Xử lý khi nhận được lệnh từ MQTT Broker (Topic: .../commands)
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.printf("\n[RECEIVED] Topic: %s\n", topic);
  
  // Chuyển payload thành String
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  // Parse JSON
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.println("[ERROR] Payload khong phai JSON hop le!");
    return;
  }

  String incomingMachineId = doc["machine_id"];
  String commandId = doc["command_id"] | "unknown";
  String commandType = doc["command_type"];
  
  String result = "REJECTED";
  String resMessage = "Sai machine_id hoac command khong hop le";

  if (incomingMachineId == MACHINE_ID) {
    if (commandType == "SET_SLOT_ENABLED") {
      int slotId = doc["slot_id"];
      bool enabled = doc["parameters"]["enabled"];

      for (int i = 0; i < 5; i++) {
        if (slots[i].slot_id == slotId) {
          slots[i].enabled = enabled;
          result = "SUCCESS";
          resMessage = "Da cap nhat trang thai slot trong C++";
          break;
        }
      }
    }
  }

  // Phản hồi kết quả lệnh (Topic: .../command-results)
  StaticJsonDocument<256> resDoc;
  resDoc["command_id"] = commandId;
  resDoc["machine_id"] = MACHINE_ID;
  resDoc["result"] = result;
  resDoc["message"] = resMessage;
  resDoc["timestamp"] = "2026-10-24T03:39:00+07:00";

  char buffer[256];
  serializeJson(resDoc, buffer);
  mqttClient.publish((BASE_TOPIC + "/command-results").c_str(), buffer, true);
  Serial.println("[PUBLISH] Da gui command-results phan hồi.");
}

void reconnect() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Dang ket noi toi broker...");
    
    // Thiết lập LWT (Last Will Testament) báo OFFLINE khi mất kết nối đột ngột
    String willTopic = BASE_TOPIC + "/status";
    String willPayload = "{\"machine_id\":\"" + MACHINE_ID + "\",\"status\":\"OFFLINE\",\"timestamp\":\"2026-10-24\"}";

    if (mqttClient.connect(CLIENT_ID.c_str(), willTopic.c_str(), 1, true, willPayload.c_str())) {
      Serial.println("THANH CONG!");
      
      // Đăng ký nhận lệnh
      mqttClient.subscribe((BASE_TOPIC + "/commands").c_str());
      mqttClient.subscribe((BASE_TOPIC + "/alerts").c_str());

      // Gửi trạng thái ONLINE (Retained = true)
      StaticJsonDocument<200> statusDoc;
      statusDoc["machine_id"] = MACHINE_ID;
      statusDoc["status"] = "ONLINE";
      statusDoc["mode"] = "NORMAL";
      statusDoc["firmware_version"] = "esp32-cpp-1.0.0";
      
      char buffer[256];
      serializeJson(statusDoc, buffer);
      mqttClient.publish(willTopic.c_str(), buffer, true);

    } else {
      Serial.printf("That bai, rc=%d. Thu lai sau 5 giay...\n", mqttClient.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  connectWiFi();

  mqttClient.setServer(BROKER_URL, BROKER_PORT);
  mqttClient.setCallback(callback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnect();
  }
  mqttClient.loop();

  // Gửi Telemetry định kỳ mỗi 10 giây
  unsigned long currentMillis = millis();
  if (currentMillis - lastTelemetryTime >= telemetryInterval) {
    lastTelemetryTime = currentMillis;

    StaticJsonDocument<1024> telDoc;
    telDoc["machine_id"] = MACHINE_ID;
    telDoc["timestamp"] = "2026-10-24T03:39:00+07:00";

    JsonArray slotsArr = telDoc.createNestedArray("slots");
    for (int i = 0; i < 5; i++) {
      JsonObject slotObj = slotsArr.createNestedObject();
      slotObj["slot_id"] = slots[i].slot_id;
      slotObj["perfume"] = slots[i].perfume;
      slotObj["enabled"] = slots[i].enabled;
      slotObj["estimated_remaining_sprays"] = slots[i].remaining_sprays;
      slotObj["sensor_status"] = slots[i].sensor_status;
    }

    char buffer[1024];
    serializeJson(telDoc, buffer);
    
    String telemetryTopic = BASE_TOPIC + "/telemetry";
    mqttClient.publish(telemetryTopic.c_str(), buffer);
    Serial.println("[PUBLISH] Da gui Telemetry dinh ky cho 5 slot nuoc hoa.");
  }
}
