#!/usr/bin/sh
sudo sendmail -t < reboot.mail &
while true
do
  isAlive=`ps -ef | grep "bme280xively.py" | grep -v grep | wc -l`
  if [ $isAlive -gt 0 ]; then
    echo "bme280xively.py is alive."
  else
    echo "bme280xively.py is dead."
    sudo python bme280xively.py &
    sudo sendmail -t < restart.mail &
  fi
  sleep 60
done