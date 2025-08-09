
SET CURL_BIN=./bin/curl
SET CURL_PARAMS=-fJL -#

SET WGET_BIN=./bin/wget
SET WGET_PARAMS=

SET 7z_BIN=./bin/7za


SET WORKDIR=%USERPROFILE%\Desktop
IF NOT EXIST "%WORKDIR%\mount" (MD "%WORKDIR%\mount")

SET DEST=%WORKDIR%\mount

MD "%DEST%\Games"

MD "%DEST%\SOFT"

SET SOFT=%DEST%\SOFT



:start

REM SYSTEM
IF NOT EXIST "%SOFT%\SYSTEM" (MD "%SOFT%\00-SYSTEM")

curl -fJL -#  -o "%SOFT%\00-SYSTEM\win_activate.cmd" "https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/refs/heads/master/MAS/All-In-One-Version-KL/MAS_AIO.cmd"

echo taskkill /F /IM explorer.exe > "%SOFT%\00-SYSTEM\explorer-restart.bat"
echo start explorer.exe >> "%SOFT%\00-SYSTEM\explorer-restart.bat"

IF NOT EXIST "%SOFT%\00-SYSTEM\7z" (MD "%SOFT%\00-SYSTEM\7z")
curl -fJL -#  -o "%SOFT%\00-SYSTEM\7z\7z-setup.exe" "https://7-zip.org/a/7z2501-x64.exe"
curl -fJL -#  -o "%SOFT%\00-SYSTEM\7z\7z-extra.7z" "https://7-zip.org/a/7z2501-extra.7z"

curl -fJL -# -o "%SOFT%\00-SYSTEM\npp.exe" "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.8.3/npp.8.8.3.Installer.x64.exe"



REM SYSTEM_UTILS
IF NOT EXIST "%SOFT%\01-SYSTEM-UTILS" (MD "%SOFT%\01-SYSTEM-UTILS")

curl -fJL -# -o "%SOFT%\01-SYSTEM-UTILS\curl-latest.zip" "https://curl.se/windows/latest.cgi?p=win64-mingw.zip"

curl -fJL -# -o "%SOFT%\01-SYSTEM-UTILS\wget.exe" "https://eternallybored.org/misc/wget/1.21.4/64/wget.exe"


REM MEDIA
IF NOT EXIST "%SOFT%\02-MEDIA" (MD "%SOFT%\02-MEDIA")

curl -fJL -#  -o "%SOFT%\02-MEDIA\MPC-HC.exe" "https://github.com/clsid2/mpc-hc/releases/download/2.5.1/MPC-HC.2.5.1.x64.exe"

IF NOT EXIST "%SOFT%\02-MEDIA\OBS Studio" (MD "%SOFT%\02-MEDIA\OBS Studio")
curl -fJL -#  -o "%SOFT%\02-MEDIA\OBS Studio\OBS Studio.zip" "https://github.com/obsproject/obs-studio/releases/download/31.1.2/OBS-Studio-31.1.2-Windows-x64.zip"


REM NETWORK
IF NOT EXIST "%SOFT%\03-NETWORK" (MD "%SOFT%\03-NETWORK")

echo [InternetShortcut] > "%SOFT%\03-NETWORK\qbittorrent-download.url"
echo URL=https://sourceforge.net/projects/qbittorrent/files/latest/download >> "%SOFT%\03-NETWORK\qbittorrent-download.url"


REM SOCIAL
IF NOT EXIST "%SOFT%\04-SOCIAL" (MD "%SOFT%\04-SOCIAL")

curl -fJL -# -o "%SOFT%\04-SOCIAL\Telegram.zip" "https://github.com/telegramdesktop/tdesktop/releases/download/v6.0.2/tportable-x64.6.0.2.zip"


REM BUILDS
IF NOT EXIST "%SOFT%\07-BUILDS" (MD "%SOFT%\07-BUILDS")
IF NOT EXIST "%SOFT%\07-BUILDS\NTLite" (MD "%SOFT%\07-BUILDS\NTLite")

curl -fJL -#  -o "%SOFT%\07-BUILDS\NTLite\NTLite.exe" "https://downloads.ntlite.com/files/NTLite_setup_x64.exe"


REM DEVEL
IF NOT EXIST "%SOFT%\99-DEVEL" (MD "%SOFT%\99-DEVEL")

IF NOT EXIST "%SOFT%\99-DEVEL\Github" (MD "%SOFT%\99-DEVEL\Github")
curl -fJL -#  -o "%SOFT%\99-DEVEL\Github\Github Desktop.msi" "https://central.github.com/deployments/desktop/desktop/latest/win32?format=msi"
curl -fJL -#  -o "%SOFT%\99-DEVEL\Github\gh-cli.msi" "https://github.com/cli/cli/releases/download/v2.76.2/gh_2.76.2_windows_amd64.msi"


pause