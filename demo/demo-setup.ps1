# Dung du lieu demo cho brand Chanel: 3 nuoc hoa, 1 may, 4 slot, chai, lap chai.
$base = "http://localhost:9999/api/v1"
function Api($method, $path, $body, $token) {
  $p = @{ Method = $method; Uri = "$base$path"; ContentType = "application/json; charset=utf-8" }
  if ($token) { $p.Headers = @{ Authorization = "Bearer $token" } }
  if ($body)  { $p.Body = [System.Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Depth 5)) }
  (Invoke-RestMethod @p).data
}
$login = Api Post "/auth/login" @{ email = "admin@chanel.example"; password = "Brand@12345" }

if (-not $login) {
    throw "Login failed: API returned empty login data."
}

$t = $login.access_token

if (-not $t) {
    throw "Login succeeded but access_token is missing. Check login response structure."
}

"Dang nhap Brand Admin Chanel: OK (token received)"

$defs = @(
  @{ sku="CH-NO5";  name="No.5";        price="50000"; top="Aldehyde, cam"; mid="Hoa hong, nhai"; base="Xa huong, go dan huong" },
  @{ sku="CH-COCO"; name="Coco Mademoiselle"; price="50000"; top="Cam bergamot"; mid="Hoa hong"; base="Vani" },
  @{ sku="CH-BLEU"; name="Bleu de Chanel";    price="70000"; top="Chanh, bac ha"; mid="Gung"; base="Tuyet tung" }
)
$products = @()
foreach ($d in $defs) {
  try {
    $p = Api Post "/products" @{ sku=$d.sku; name=$d.name; default_price_per_spray=$d.price;
          top_notes=$d.top; middle_notes=$d.mid; base_notes=$d.base;
          usage_instructions="Dat co tay vao khay xit." } $t
    $products += $p; "San pham: $($p.name) (id $($p.id))"
  } catch { "LOI san pham $($d.sku): $($_.ErrorDetails.Message)" }
}
if ($products.Count -eq 0) { "Khong tao duoc san pham (co the da tao truoc do). Dung lai."; return }

$serial = "KIOSK-CHANEL-001"
$m = Api Post "/machines" @{ serial_number=$serial; name="Chanel - Vincom Dong Khoi"; slot_count=4 } $t
$machineId = $m.machine.id; $secret = $m.device_secret
"May: $serial (id $machineId)"

$detail = Api Get "/machines/$machineId" $null $t
$slots = @($detail.slots | Sort-Object slot_number)

for ($i = 0; $i -lt $products.Count; $i++) {
  $prod = $products[$i]; $slot = $slots[$i]
  Api Put "/slots/$($slot.id)" @{ product_id=$prod.id; price=[decimal]$defs[$i].price; enabled=$true } $t | Out-Null
  $batch = Api Post "/inventory/batches" @{ product_id=$prod.id; batch_number="LOT-$($i+1)-2026"; quantity=1;
            received_date=(Get-Date -Format "yyyy-MM-dd"); expiration_date="2030-12-31" } $t
  $bottle = Api Post "/inventory/bottles" @{ batch_id=$batch.id; unique_code="BTL-CH-$($i+1)-001"; capacity_ml=50; initial_weight_g=180 } $t
  Api Post "/inventory/slots/$($slot.id)/install-bottle" @{ bottle_id=$bottle.id; weight_before=180; weight_after=180 } $t | Out-Null
  "Slot $($slot.slot_number): $($prod.name) + chai $($bottle.unique_code)"
}

"`n=== LUU LAI ==="
"serial : $serial"
"secret : $secret"
"`nBuoc tiep: mo cua so PowerShell thu 3 va chay:"
"python simulator/device_simulator.py --serial $serial --secret $secret"
$secret | Out-File -Encoding ascii "$PSScriptRoot\device_secret.txt"
