#!/bin/bash
set -o nounset  # (aka set -u) abort on undefined variable reference
set -o errexit  # (aka set -e) abort on any command failure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PS4='$0.$LINENO'  # prompt used by xtrace
set -o xtrace   # (aka set -x) show each command that is executed
#set -o verbose # (aka set -v) show input lines as they are read

function a() {
mysql -u root -e "create user 'muni'@'localhost';"
mysql -u root -e "create database muni;"
mysql -u root -e "grant all privileges on muni.* to 'muni'@'localhost';"
}
function b() {
mysql -u muni muni -e "create table subscriptions (user varchar(50), route_id int, stop_id int, start_time_min int, stop_time_min int);"
mysql -u muni muni -e "create table announcements_by_stop (route_id int, stop_id int, start_time_min int, stop_time_min int, announcement varchar(1024));"
}

mysql -u muni muni -e "drop table subscriptions"
mysql -u muni muni -e "drop table announcements_by_stop"
mysql -u muni muni -e "create table subscriptions (user varchar(50), route_id int, stop_id int, start_time_min int, stop_time_min int);"
