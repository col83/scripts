## windows
only if u have USB adapter
not e.g Intel Wifi Card or something. because on windows, monitor mode pain in the ass
but you can still decrypt hashes on Windows. the procedure will be described later

## preparations

on windows if u not have a captured file, u need to capture it with followings methods

## wireshark (recommend v4.4.8 or above)

download - https://npcap.com/#download (install with all checkboxes)
download - https://www.wireshark.org/download.html
install portable or "full" version (recommended) (also if u use "full" version, u need to restart pc after install)


go to wireshark directory
open cmd in current directory (if windows)

tshark -D (for list available interfaces)

-F *type* (pcap or pcapng) -w "*dir*/*name*.*type*"
example - tshark -i 3 -I -F pcapng -P -w "%USERPROFILE%\Desktop\.pcapng"




## linux

## hashcat

sudo su
cd ~/
pacman -S --needed bzip2 openssl ncurses libffi readline sqlite

# if nvidia - https://developer.nvidia.com/cuda-downloads

# list devices
hashcat.exe -I

## decryption
hashcat.exe -m 22000 *hashfile* *pass.dict* --status --status-timer=3 --backend-ignore-hip -o "./*BSSID*.txt" --potfile-path="./*BSSID*.potfile" -d *device id*

or with --skip *10000000* (number of skipped combinations)

--hwmon-disable flag for off temperature info

--show (if out file not exist & u forgot result)
