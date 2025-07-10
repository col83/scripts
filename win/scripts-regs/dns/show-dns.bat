@echo off
cls
title dns view

set DEST=%USERPROFILE%\Desktop
set OUTFILE=%DEST%\dns-addr.txt

echo. >> %outfile%

.\coreutils.exe date | .\coreutils.exe cut -b 12- | .\coreutils.exe cut -b -9 | .\coreutils.exe tee >> %outfile%

exit | nslookup | findstr -C:Address | .\coreutils.exe cut -b 11- | .\coreutils.exe tee >> %OUTFILE%

echo.
exit | nslookup | findstr -C:Address | .\coreutils.exe cut -b 11-

echo.
pause