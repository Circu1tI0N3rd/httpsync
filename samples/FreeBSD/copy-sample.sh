#!/bin/sh

if id "httpsync" >/dev/null 2>&1; then
    pw group add httpsync -g 1000
    pw user add httpsync -u 1000 -d /var/db/httpsync -m -g httpsync
fi
install -v -d /usr/local/etc/nginx
install -v -m 644 usr/local/etc/nginx/nginx.conf /usr/local/etc/nginx
install -v -m 644 usr/local/etc/aria2.conf       /usr/local/etc
[ -d /var/db/httpsync ] || mkdir -p /var/db/httpsync; chown -R httpsync:httpsync /var/db/httpsync
install -v -m 644 httpsync.ini /var/db/httpsync

echo 'aria2_enable="YES"'     >> /etc/rc.conf
echo 'aria2_user="httpsync"'  >> /etc/rc.conf
echo 'aria2_group="httpsync"' >> /etc/rc.conf
echo 'nginx_enable="YES"'     >> /etc/rc.conf

echo 'Please change the paths in nginx.conf, aria2.conf and httpsync.ini appropriately.'
echo 'Paths of config files:'
echo ' - /usr/local/etc/nginx/nginx.conf'
echo ' - /usr/local/etc/aria2.conf'
echo ' - /var/db/httpsync/httpsync.ini'
echo 'Remember to change destination ownership to "httpsync" or aria2 errors out on file downloads.'
exit 0
