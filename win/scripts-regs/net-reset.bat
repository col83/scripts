netsh int ip reset
netsh winsock reset
ipconfig /release
ipconfig /renew
ipconfig /flushdns

shutdown -r -t 1