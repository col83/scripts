#!/bin/bash

DATE_ENV=(date +%D)

cd /
echo
mkdir /backup

echo
read -p 'Backup kernel file (y/n): ' KERNEL_BACKUP

if [ ${KERNEL_BACKUP} = y ]; then
    cp /boot/vmlinuz-linux /backup/
    cp /boot/initramfs-linux.img /backup/
fi

echo
read -p 'Backup pacman database (y/n): ' PACMAN_DATABASE_BACKUP

if [ ${PACMAN_DATABASE_BACKUP} = y ]; then
    pacman -Syy; pacman -Fyy
    tar -cjvf /backup/db.tar /var/lib/pacman/
fi
