# Test all API endpoints
$base = "http://localhost:8000/api"
$token = $null

function Invoke-Api {
    param($Method, $Url, $Body = $null, $UseAuth = $false)
    $headers = @{ "Content-Type" = "application/json" }
    if ($UseAuth -and $token) { $headers["Authorization"] = "Bearer $token" }
    $params = @{ Method = $Method; Uri = $Url; Headers = $headers }
    if ($Body) { $params["Body"] = ($Body | ConvertTo-Json) }
    try {
        $r = Invoke-RestMethod @params
        return $r
    } catch {
        return $_.Exception.Response.StatusCode.value__
    }
}

$testEmail = "test" + (Get-Random -Maximum 99999) + "@example.com"
Write-Host "`n=== 1. Register ($testEmail) ===" -ForegroundColor Cyan
$reg = Invoke-Api -Method POST -Url "$base/auth/register/" -Body @{
    email = $testEmail
    password = "TestPass123!"
    first_name = "Test"
    last_name = "User"
}
$reg | ConvertTo-Json -Depth 3

Write-Host "`n=== 2. Login ===" -ForegroundColor Cyan
$login = Invoke-Api -Method POST -Url "$base/auth/login/" -Body @{
    email = $testEmail
    password = "TestPass123!"
}
if ($login -is [int]) {
    Write-Host "Login failed: $login" -ForegroundColor Red
} else {
    $token = $login.access
    if ($token) { Write-Host "Token obtained" } else { Write-Host "No token" }
}

Write-Host "`n=== 3. Me ===" -ForegroundColor Cyan
Invoke-Api -Method GET -Url "$base/auth/me/" -UseAuth $true | ConvertTo-Json

Write-Host "`n=== 4. Categories (list) ===" -ForegroundColor Cyan
$cats = Invoke-Api -Method GET -Url "$base/categories/"
$cats | ConvertTo-Json -Depth 2

Write-Host "`n=== 5. Create Category (admin - may 404) ===" -ForegroundColor Cyan
# Skip - needs admin

Write-Host "`n=== 6. Auctions (list) ===" -ForegroundColor Cyan
$auctions = Invoke-Api -Method GET -Url "$base/auctions/"
$auctions | ConvertTo-Json -Depth 2

Write-Host "`n=== 7. Create Auction ===" -ForegroundColor Cyan
$auc = Invoke-Api -Method POST -Url "$base/auctions/" -Body @{
    title = "Test Painting"
    description = "A beautiful painting"
    starting_price = "100.00"
    image_urls = @()
} -UseAuth $true
$auc | ConvertTo-Json -Depth 3
$auctionId = $auc.id

Write-Host "`n=== 8. Auction Detail ===" -ForegroundColor Cyan
Invoke-Api -Method GET -Url "$base/auctions/$auctionId/" -UseAuth $true | ConvertTo-Json -Depth 3

Write-Host "`n=== 9. Start Auction (with duration) ===" -ForegroundColor Cyan
Invoke-Api -Method POST -Url "$base/auctions/$auctionId/start/" -Body @{duration_days=1; duration_hours=2; duration_minutes=30} -UseAuth $true | ConvertTo-Json -Depth 2

Write-Host "`n=== 10. Place Bid ===" -ForegroundColor Cyan
$bid = Invoke-Api -Method POST -Url "$base/auctions/$auctionId/bid/" -Body @{ amount = "150.00" } -UseAuth $true
$bid | ConvertTo-Json -Depth 2

Write-Host "`n=== 11. Add to Watchlist ===" -ForegroundColor Cyan
Invoke-Api -Method POST -Url "$base/auctions/$auctionId/add_to_watchlist/" -UseAuth $true | ConvertTo-Json

Write-Host "`n=== 12. My Watchlist ===" -ForegroundColor Cyan
Invoke-Api -Method GET -Url "$base/auth/me/watchlist/" -UseAuth $true | ConvertTo-Json -Depth 3

Write-Host "`n=== 13. My Bids ===" -ForegroundColor Cyan
Invoke-Api -Method GET -Url "$base/auth/me/bids/" -UseAuth $true | ConvertTo-Json -Depth 2

Write-Host "`n=== 14. My Auctions ===" -ForegroundColor Cyan
Invoke-Api -Method GET -Url "$base/auth/me/auctions/" -UseAuth $true | ConvertTo-Json -Depth 2

Write-Host "`n=== 15. Refresh Token ===" -ForegroundColor Cyan
$refresh = Invoke-Api -Method POST -Url "$base/auth/refresh/" -Body @{ refresh = $login.refresh }
$token = $refresh.access
Write-Host "New token obtained"

Write-Host "`n=== 16. Remove from Watchlist ===" -ForegroundColor Cyan
Invoke-Api -Method POST -Url "$base/auctions/$auctionId/remove_from_watchlist/" -UseAuth $true | ConvertTo-Json

Write-Host "`n=== Done ===" -ForegroundColor Green
