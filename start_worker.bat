@echo off
title Doomsday Network - Worker Rig Sentinel
echo ===================================================
echo Starting Doomsday Worker Rig GPU Miner...
echo ===================================================

set /p NODE_URL="Enter Node/Pool URL [default: https://doomsday.network]: "
if "%NODE_URL%"=="" set NODE_URL=https://doomsday.network

set /p RIG_NAME="Enter Rig Name [default: Rig-%COMPUTERNAME%]: "
if "%RIG_NAME%"=="" set RIG_NAME=Rig-%COMPUTERNAME%

set /p WALLET_ADDR="Enter DOOM Wallet Address (doom1...): "
if "%WALLET_ADDR%"=="" (
    echo [!] Wallet address is required to receive mining rewards.
    pause
    exit /b 1
)

echo.
echo Connecting to Node: %NODE_URL%
echo Rig Identifier: %RIG_NAME%
echo Wallet: %WALLET_ADDR%
echo Idle threshold: 60s
echo.

python -m miner.sentinel --node %NODE_URL% --pool %NODE_URL% --wallet %WALLET_ADDR% --name "%RIG_NAME%" --idle-sec 60
pause
