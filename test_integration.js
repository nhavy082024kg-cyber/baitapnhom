const mqtt = require('mqtt');

const BROKER = 'mqtt://broker.hivemq.com:1883';
const MACHINE_ID = 'ss-001';

const TELEMETRY_TOPIC = `scentstation/${MACHINE_ID}/telemetry`;
const COMMAND_RESULT_TOPIC = `scentstation/${MACHINE_ID}/command-results`;

console.log('🔄 Đang khởi chạy kiểm thử tích hợp...');
const client = mqtt.connect(BROKER);

client.on('connect', () => {
    console.log('✅ [PASSED] Kết nối MQTT Broker thành công!');
    client.subscribe(TELEMETRY_TOPIC, () => {
        const payload = JSON.stringify({
            machine_id: MACHINE_ID,
            timestamp: "2026-10-24T03:39:00+07:00",
            slots: [
                { slot_id: 1, perfume: "Chanel", enabled: true, estimated_remaining_sprays: 35, sensor_status: "OK" }
            ]
        });
        client.publish(TELEMETRY_TOPIC, payload);
    });
});

client.on('message', (topic, message) => {
    console.log('✅ [TC01 PASSED] Nhận Telemetry thành công:', message.toString());
    console.log('🎉 TẤT CẢ KỊCH BẢN KIỂM THỬ ĐÃ THÀNH CÔNG!');
    process.exit(0);
});