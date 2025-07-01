RED="\e[31m"
GREEN="\e[32m"
ENDCOLOR="\e[0m"




grub_check() {

if [[ ! -d /boot/grub ]]; then
echo
echo -e ''${RED}'YOU NEED TO INSTALL GRUB BOOTLOADER '${ENDCOLOR}':'
echo
echo -e ''${GREEN}'sudo grub-install --efi-directory=/boot --bootloader-id=GRUB '${ENDCOLOR}''
echo
echo -e ''${RED}'THEN CREATE GRUB CONFIG '${ENDCOLOR}:''
echo
echo -e ''${GREEN}'sudo grub-mkconfig -o /boot/grub/grub.cfg '${ENDCOLOR}''
echo
fi
}

grub_check
