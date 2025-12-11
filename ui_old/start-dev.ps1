# Script to start Next.js dev server with port management
$port = 3000

# Check if port is in use
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($connections) {
    Write-Host "Port $port is in use. Attempting to free it..."
    foreach ($conn in $connections) {
        $processId = $conn.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Killing process: $($process.ProcessName) (PID: $processId)"
            Stop-Process -Id $processId -Force
        }
    }
    Start-Sleep -Seconds 2
}

# Start dev server
Write-Host "Starting Next.js dev server on port $port..."
npm run dev
