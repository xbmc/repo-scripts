#! /bin/sh

echo 0 > /sys/class/rtc/rtc0/wakealarm
echo $1 > /sys/class/rtc/rtc0/wakealarm

case "$2" in
    1)
        shutdown -h now "TVHManager shutdown the system"
    ;;
esac
sleep 1
exit 0
