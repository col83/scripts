#!/bin/bash

echo; echo
cfdisk

umount -R /mnt 2>/dev/null


clear
echo
lsblk
echo

echo -n 'Select ROOT partition (/dev/): '
read ROOT_PART
echo
echo -n 'Select BOOT partition (/dev/): '
read BOOT_PART


echo
read  -p 'Erase drive data (y/n): ' FORMAT_DRIVE
if [[ ${FORMAT_DRIVE} = y ]]; then
    mkfs.fat -n boot -F 32 /dev/${BOOT_PART} &>/dev/null
    mkfs.ext4 -L root -F -F /dev/${ROOT_PART} 1>/dev/null
fi


mount -L root /mnt
mount --mkdir -L boot /mnt/boot


clear
echo
lsblk
echo
