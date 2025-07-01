@echo off
cls
echo.

netsh int ip reset
netsh winsock reset
ipconfig /release
ipconfig /renew
ipconfig /flushdns

echo.
pause