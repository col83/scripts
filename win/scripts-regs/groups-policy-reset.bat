rd /s /q "%WinDir%\System32\GroupPolicyUsers"
rd /s /q "%WinDir%\System32\GroupPolicy"
gpupdate /force
shutdown -r -t 1