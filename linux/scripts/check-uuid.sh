#!/bin/bash

clear
echo
lsblk
echo
read -p 'Select drive (/dev/): ' DRIVE
clear
echo
lsblk
echo
blkid -o export /dev/${DRIVE} | cat | grep PARTUUID | cut -b 10-
echo
