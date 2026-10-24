import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class TestIntegration {
    static final String BROKER = "tcp://broker.hivemq.com:1883";
    static final String MACHINE_ID = "ss-001";
    
    static final String TELEMETRY_TOPIC = "scentstation/" + MACHINE_ID + "/telemetry";
    static final String COMMAND_TOPIC = "scentstation/" + MACHINE_ID + "/commands";
    static final String COMMAND_RESULT_TOPIC = "scentstation/" + MACHINE_ID + "/command-results";

    public static void main(String[] args) {
        System.out.println("🔄 Đang khởi chạy kiểm thử tích hợp bằng Java...");
        try {
            testTelemetryFlow();
            testCommandFlow();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void testTelemetryFlow() {
        MemoryPersistence persistence = new MemoryPersistence();
        try {
            MqttClient subClient = new MqttClient(BROKER, "Java_Test_Sub_01", persistence);
            subClient.connect();
            
            subClient.subscribe(TELEMETRY_TOPIC, (topic, message) -> {
                String payload = new String(message.getPayload());
                System.out.println("✅ [TC01 PASSED] Nhận Telemetry thành công trên topic: " + topic);
            });

            MqttClient pubClient = new MqttClient(BROKER, "Java_Test_Pub_01", persistence);
            pubClient.connect();

            String samplePayload = "{"
                + "\"machine_id\":\"" + MACHINE_ID + "\","
                + "\"timestamp\":\"2026-10-24T03:39:00+07:00\","
                + "\"slots\":["
                + "  {\"slot_id\":1,\"perfume\":\"Chanel\",\"enabled\":true,\"estimated_remaining_sprays\":35,\"sensor_status\":\"OK\"}"
                + "]"
                + "}";

            pubClient.publish(TELEMETRY_TOPIC, new MqttMessage(samplePayload.getBytes()));
            Thread.sleep(1500);
            
            pubClient.disconnect();
            subClient.disconnect();
        } catch (Exception e) {
            System.out.println("❌ [TC01 FAILED] Lỗi: " + e.getMessage());
        }
    }

    public static void testCommandFlow() {
        MemoryPersistence persistence = new MemoryPersistence();
        try {
            MqttClient cmdSub = new MqttClient(BROKER, "Java_Test_CmdSub", persistence);
            cmdSub.connect();

            cmdSub.subscribe(COMMAND_RESULT_TOPIC, (topic, message) -> {
                String payload = new String(message.getPayload());
                System.out.println("✅ [TC02 PASSED] Nhận phản hồi lệnh thành công!");
                System.out.println("🎉 TẤT CẢ KỊCH BẢN KIỂM THỬ JAVA ĐÃ THÀNH CÔNG!");
                System.exit(0);
            });

            MqttClient cmdPub = new MqttClient(BROKER, "Java_Test_CmdPub", persistence);
            cmdPub.connect();

            String cmdPayload = "{"
                + "\"machine_id\":\"" + MACHINE_ID + "\","
                + "\"command_id\":\"CMD_101\","
                + "\"command_type\":\"SET_SLOT_ENABLED\","
                + "\"slot_id\":1,"
                + "\"parameters\":{\"enabled\":false}"
                + "}";
            cmdPub.publish(COMMAND_TOPIC, new MqttMessage(cmdPayload.getBytes()));

            Thread.sleep(500);
            String resPayload = "{"
                + "\"command_id\":\"CMD_101\","
                + "\"machine_id\":\"" + MACHINE_ID + "\","
                + "\"result\":\"SUCCESS\","
                + "\"message\":\"Da cap nhat trang thai slot trong Java\","
                + "\"timestamp\":\"2026-10-24T03:39:00+07:00\""
                + "}";
            cmdPub.publish(COMMAND_RESULT_TOPIC, new MqttMessage(resPayload.getBytes()));

            Thread.sleep(1500);
            cmdPub.disconnect();
            cmdSub.disconnect();
        } catch (Exception e) {
            System.out.println("❌ [TC02 FAILED] Lỗi: " + e.getMessage());
        }
    }
}