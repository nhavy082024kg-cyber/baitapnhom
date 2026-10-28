#include <Arduino.h>
#include <EEPROM.h>

const int SLOT_PINS[5]   = {23, 19, 18, 5, 17}; // Van 1:Chanel, 2:YSL, 3:Dior, 4:Gucci, 5:Hermes
const int PUMP_PIN       = 16;                 // Bom ap luc 12V
const int PIN_DOOR_SENS  = 34;                 // Cam bien cua (NO/NC)
const int PIN_LEAK_SENS  = 35;                 // Cam bien ro ri nuoc hoa
const int PIN_ESTOP_SENS = 32;                 // Doc tin hieu E-Stop
const int PIN_IR_SPRAY   = 33;                 // Cam bien quang phat hien dong xit 

int spray_duration_ms[5] = {120, 120, 120, 120, 120};

struct TestResult {
  bool slot_ok[5];
  bool door_sensor_ok;
  bool leak_sensor_ok;
  bool estop_ok;
  bool ir_sensor_ok;
};

TestResult currentTest;

void printMenu();

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000);

  Serial.println("\n==================================================");
  Serial.println("  SCENTSTATION: Kiem thu ra soat thiet bi he thong ");
  Serial.println("  Thuong hieu: Chanel | YSL | Dior | Gucci | Hermes");
  Serial.println("==================================================\n");

  // Config Outputs
  for (int i = 0; i < 5; i++) {
    pinMode(SLOT_PINS[i], OUTPUT);
    digitalWrite(SLOT_PINS[i], LOW); // Tat van
  }
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW); // Tat bom  

  // Config Inputs
  pinMode(PIN_DOOR_SENS, INPUT_PULLUP);
  pinMode(PIN_LEAK_SENS, INPUT_PULLUP);
  pinMode(PIN_ESTOP_SENS, INPUT_PULLUP);
  pinMode(PIN_IR_SPRAY, INPUT_PULLUP);

  Serial.println("[OK] Khoi tao GPIO thanh cong.");
  printMenu();
}


// 1. Kiem thu cam bien an toan 
void testSafetySensors() {
  Serial.println("\n--- [TEST 1] KIá»‚M THá»¬ Cáº¢M BIáº¾N AN TOĂ€N ---");
  
  bool doorState = digitalRead(PIN_DOOR_SENS);
  bool leakState = digitalRead(PIN_LEAK_SENS);
  bool estopState = digitalRead(PIN_ESTOP_SENS);

  Serial.printf("1. Cam bien cua: %s\n", doorState == LOW ? "DONG (PASS)" : "MO (ALERT)");
  Serial.printf("2. Cam bien ro ri: %s\n", leakState == HIGH ? "AN TOAN (PASS)" : "RO RI (ALERT)");
  Serial.printf("3. Nut E-Stop: %s\n", estopState == HIGH ? "BINH THUONG (PASS)" : "DA NHAN (STOP)");

  currentTest.door_sensor_ok = (doorState == LOW);
  currentTest.leak_sensor_ok = (leakState == HIGH);
  currentTest.estop_ok = (estopState == HIGH);
}

// 2. Kiem thu Phun thu nghiem 1 Slot (Dry / Wet Run)
bool testSingleSlot(int slotIndex, const char* brandName, int durationMs) {
  Serial.printf("\n--- [TEST 2] KIá»‚M THá»¬ SLOT %d [%s] ---\n", slotIndex + 1, brandName);

  // Kiem tra lien dong an toan truoc khi kich hoat 
  if (digitalRead(PIN_DOOR_SENS) == HIGH || digitalRead(PIN_ESTOP_SENS) == LOW) {
    Serial.println("[LOI] An toan khong dat! Cua dang mo hoac E-Stop dang bat. HUY PHUN.");
    return false;
  }

  Serial.println("-> Bat bom ap luc...");
  digitalWrite(PUMP_PIN, HIGH);
  delay(200); // Chá» Ä‘á»§ Ă¡p suáº¥t

  Serial.printf("-> Mo Van Slot %d (%s) trong %d ms...\n", slotIndex + 1, brandName, durationMs);
  unsigned long startTime = millis();
  digitalWrite(SLOT_PINS[slotIndex], HIGH);
  
  bool irDetected = false;
  while (millis() - startTime < (unsigned long)durationMs) {
    if (digitalRead(PIN_IR_SPRAY) == LOW) { // 
      irDetected = true;
    }
  }

  digitalWrite(SLOT_PINS[slotIndex], LOW);
  digitalWrite(PUMP_PIN, LOW);
  Serial.println("-> Da ngat van va bom.");

  if (irDetected) {
    Serial.println("-> Cam bien IR: Phat hien dong PHUN [PASS]");
  } else {
    Serial.println("-> Cam bien IR: Khong thay dong PHUN [WARN/FAIL]");
  }

  return true;
}

// 3. Kiem thu tu dong 5 slot noi tiep (Sequence Test)
void runFullSequenceTest() {
  const char* brands[5] = {"Chanel", "YSL", "Dior", "Gucci", "Hermes"};
  Serial.println("\n==================================================");
  Serial.println("  KICK-OFF Kiem thu toan bo 5 slot thuong hieu ");
  Serial.println("==================================================");

  for (int i = 0; i < 5; i++) {
    bool res = testSingleSlot(i, brands[i], spray_duration_ms[i]);
    currentTest.slot_ok[i] = res;
    delay(1000); // khoang nghi giua cac slot
  }
}

// 4. in bao cao kiem thu & tieu chi nghiem thu 
void printAcceptanceReport() {
  const char* brands[5] = {"Chanel", "YSL", "Dior", "Gucci", "Hermes"};
  Serial.println("\n==================================================");
  Serial.println("      Bao cao ra soat tieu chi nghiem THU          ");
  Serial.println("==================================================");
  
  testSafetySensors();

  Serial.println("\nTrang thai 5 SLOT thuong hieu:");
  for (int i = 0; i < 5; i++) {
    Serial.printf(" - Slot %d [%-7s]: %s\n", i + 1, brands[i], currentTest.slot_ok[i] ? "DAT (PASSED)" : "KHONG DAT (FAILED)");
  }

  bool overallPass = currentTest.door_sensor_ok && currentTest.estop_ok && currentTest.leak_sensor_ok;
  for(int i = 0; i < 5; i++) overallPass &= currentTest.slot_ok[i];

  Serial.println("--------------------------------------------------");
  Serial.printf("Ket luan tong the‚: [%s]\n", overallPass ? "Nghiem THU dat (PASS)" : "Can sua loi (REJECT)");
  Serial.println("==================================================\n");
}

void printMenu() {
  Serial.println("\nChon lenh kiem thu¬ (Go so tu ban phiem Serial):");
  Serial.println(" 1. Kiem thu cam bien an toan (Cua, E-Stop, Ro ri)");
  Serial.println(" 2. Phun thu­ Slot 1 (Chanel Bleau)");
  Serial.println(" 3. Phun thu­ Slot 2 (YSL Y EDP)");
  Serial.println(" 4. Phun thu­ Slot 3 (Dior Sauvage)");
  Serial.println(" 5. Phun thu­ Slot 4 (Gucci Flora)");
  Serial.println(" 6. Phun thu­ Slot 5 (Hermes Terre)");
  Serial.println(" 7. CHay toan bo PROCESS (Chay noi tiep 5 Slot)");
  Serial.println(" 8. Xuat bao cao nghiem thu tong the");
}

// ============================================================================
// LUon chinh (LOOP)
// ============================================================================
void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    switch (cmd) {
      case '1': testSafetySensors(); break;
      case '2': currentTest.slot_ok[0] = testSingleSlot(0, "Chanel", spray_duration_ms[0]); break;
      case '3': currentTest.slot_ok[1] = testSingleSlot(1, "YSL", spray_duration_ms[1]); break;
      case '4': currentTest.slot_ok[2] = testSingleSlot(2, "Dior", spray_duration_ms[2]); break;
      case '5': currentTest.slot_ok[3] = testSingleSlot(3, "Gucci", spray_duration_ms[3]); break;
      case '6': currentTest.slot_ok[4] = testSingleSlot(4, "Hermes", spray_duration_ms[4]); break;
      case '7': runFullSequenceTest(); break;
      case '8': printAcceptanceReport(); break;
      default: break;
    }
    delay(500);
    printMenu();
  }
}
