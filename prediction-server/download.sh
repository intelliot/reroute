#!/bin/bash
set -o nounset  # (aka set -u) abort on undefined variable reference
set -o errexit  # (aka set -e) abort on any command failure
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PS4='$0.$LINENO'  # prompt used by xtrace
set -o xtrace   # (aka set -x) show each command that is executed
#set -o verbose # (aka set -v) show input lines as they are read

[ -d src/transitfeed ] || (
  [ -f transitfeed-1.2.12.tar.gz ] || wget http://googletransitdatafeed.googlecode.com/files/transitfeed-1.2.12.tar.gz
  [ -d transitfeed-1.2.12 ] || tar -xzf transitfeed-1.2.12.tar.gz
  [ -d src/transitfeed ] || cp -r transitfeed-1.2.12/transitfeed src/transitfeed
)
[ -d src/tornado ] || (
  [ -f tornado-2.4.tar.gz ] || wget https://github.com/downloads/facebook/tornado/tornado-2.4.tar.gz
  [ -d tornado-2.4 ] || tar -xzf tornado-2.4.tar.gz
  [ -d src/tornado ] || cp -r tornado-2.4/tornado src/tornado
)
[ -d muni_gtfs ] || (
  [ -f google_transit.zip ] || wget http://www.sfmta.com/transitdata/google_transit.zip
  [ -d muni_gtfs ] || (mkdir muni_gtfs && unzip google_transit.zip -d muni_gtfs)
)
echo 'import MySQLdb' | python || (
  [ -f MySQL-python-1.2.4b4.tar.gz ] || wget 'http://downloads.sourceforge.net/project/mysql-python/mysql-python-test/1.2.4b4/MySQL-python-1.2.4b4.tar.gz'
  [ -d MySQL-python-1.2.4b4 ] || tar -xzf MySQL-python-1.2.4b4.tar.gz
  cd MySQL-python-1.2.4b4
  python setup.py build
  sudo python setup.py install
)

# also:
# sudo apt-get update
# sudo apt-get install mysql-client-core-5.5 mysql-server-5.5
# sudo mysql_install_db --force

# sudo apt-get install libmysqlclient-dev