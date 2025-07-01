@echo off

title dns view

echo.

set DEST=%USERPROFILE%\Desktop
set outfile=%DEST%\dns-addr.txt

echo. >> %outfile%

.\coreutils.exe date | .\coreutils.exe cut -b 12- | .\coreutils.exe cut -b -9 | .\coreutils.exe tee >> %outfile%

exit | nslookup | findstr -C:Address | .\coreutils.exe cut -b 11- | .\coreutils.exe tee >> %outfile%
exit | nslookup | findstr -C:Address | .\coreutils.exe cut -b 11-

echo.
pause