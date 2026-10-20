# Off-Box Sovereign Ledger Backup Sync
# Pulls the latest atomic SQLite backup + pool state from doomsday-seed-node (GCP)
# to local storage and mirrors to secondary network storage if mounted.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LocalBackupDir = Join-Path $ProjectRoot "backups\latest"
$ArchiveDir = Join-Path $ProjectRoot "backups\archive"
$Gcloud = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

New-Item -ItemType Directory -Force -Path $LocalBackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $ArchiveDir | Out-Null

Write-Host "[1/3] Triggering atomic hot-backup on doomsday-seed-node..." -ForegroundColor Cyan
& $Gcloud compute ssh doomsday-seed-node --zone=us-central1-a --command="~/doomsday/venv/bin/python3 ~/doomsday/scripts/backup_node.py"

Write-Host "[2/3] Downloading latest ledger & pool state off-box to local PC..." -ForegroundColor Cyan
& $Gcloud compute scp --recurse "doomsday-seed-node:~/doomsday/backups/latest/*" "$LocalBackupDir" --zone=us-central1-a

# Also save a timestamped local copy of doomsday.db
$ts = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
Copy-Item -Path (Join-Path $LocalBackupDir "doomsday.db") -Destination (Join-Path $ArchiveDir "doomsday-$ts.db") -Force

if (Test-Path "Y:\doomsday") {
    Write-Host "[3/3] Mirroring off-box backup to secondary storage (Y:\doomsday\backups)..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path "Y:\doomsday\backups\latest" | Out-Null
    Copy-Item -Path "$LocalBackupDir\*" -Destination "Y:\doomsday\backups\latest\" -Force
}

Write-Host "[OK] Off-box backup complete! Saved to $LocalBackupDir and Y:\doomsday\backups\latest" -ForegroundColor Green
Get-Content (Join-Path $LocalBackupDir "manifest.txt")
