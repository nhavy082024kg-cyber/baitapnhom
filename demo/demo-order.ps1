# Tao 1 don tren kiosk, gia lap thanh toan, kiem tra ket qua. Chay sau khi simulator dang chay.
$base = "http://localhost:9999/api/v1"
$serial = "KIOSK-CHANEL-001"
$secret = (Get-Content "$PSScriptRoot\device_secret.txt").Trim()
$dh = @{ "X-Device-Serial" = $serial; "X-Device-Secret" = $secret }
$ct = "application/json"

"--- Menu tren kiosk ---"
(Invoke-RestMethod -Uri "$base/kiosk/catalog" -Headers $dh).data | ConvertTo-Json -Depth 5

$o = (Invoke-RestMethod -Method Post -Uri "$base/kiosk/orders" -Headers $dh -ContentType $ct -Body '{"slot_number":1}').data
"`n--- Don vua tao ---"; $o | ConvertTo-Json -Depth 5
$ref = $o.payment.payment_reference; $code = $o.order.order_code
if (-not $ref) { "Khong thay payment_reference, dung."; return }

"`n--- Gia lap thanh toan ---"
(Invoke-RestMethod -Method Post -Uri "$base/dev/mock-payment" -ContentType $ct -Body (@{ payment_reference = $ref } | ConvertTo-Json)).data | ConvertTo-Json

Start-Sleep -Seconds 8
"`n--- Trang thai don ---"
(Invoke-RestMethod -Uri "$base/kiosk/orders/$code" -Headers $dh).data | ConvertTo-Json -Depth 5
