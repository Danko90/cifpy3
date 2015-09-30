#!/bin/bash

# Operating System tests
OS_LINUX=0
OS_DEBIAN=0
OS_REDHAT=0
OS_MAC=0

# Get the OS Type
function os_type
{
    case `uname` in
        Linux )
            OS_LINUX=1
            which -a yum && { OS_REDHAT=1; return; }
            which -a apt-get && { OS_DEBIAN=1; return; }
            ;;
        Darwin )
            OS_MAC=1
            ;;
        * )
            echo "[ERROR] Unsupported OS: `uname`"
            exit 1
            ;;
    esac
}

os_type

# Install Debian Dependencies
if [[ OS_DEBIAN -gt 0 ]]; then
    sudo apt-get -y install git python3 python3-requests python3-yaml python3-dnspython python3-pip python3-dateutil \
    elasticsearch
    sudo pip3 install pygeoip feedparser tabulate
    cat /etc/default/elasticsearch | sed -e 's/#START_DAEMON/START_DAEMON/' > /etc/default/elasticsearch.new
    mv /etc/default/elasticsearch.new /etc/default/elasticsearch
    /etc/init.d/elasticsearch start
fi


