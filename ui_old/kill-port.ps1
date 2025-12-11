# Script to kill process on port 3000
$port = 3000
$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($connections) {
    foreach ($conn in $connections) {
        $processId = $conn.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Killing process: $($process.ProcessName) (PID: $processId) on port $port"
            Stop-Process -Id $processId -Force
        }
    }
    Write-Host "Port $port is now free"
} else {
    Write-Host "Port $port is not in use"
}
