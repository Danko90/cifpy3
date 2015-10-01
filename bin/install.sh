#!/bin/bash

# Root check
if [[ "`whoami`" != "root" ]]; then
    echo "[ERROR] You must run this install script as root"
    exit 1
fi

# Operating System tests
OS_LINUX=0
OS_DEBIAN=0
OS_UBUNTU=0
OS_REDHAT=0
OS_MAC=0

# Get the OS Type
function os_type
{
    case `uname` in
        Linux )
            echo "[OKAY] Detected Linux Operating System"
            OS_LINUX=1

            if [[ -f /etc/redhat-release ]]; then
                echo "[OKAY] Detected RedHat/CentOS distribution"
                OS_REDHAT=1
            fi

            if [[ -f /etc/debian_version ]]; then
                echo "[OKAY] Detected Debian distribution"
                OS_DEBIAN=1
                OS_UBUNTU=0
            fi

            if [[ -f /etc/lsb-release ]]; then
                echo "[OKAY] Detected Ubuntu distribution"
                OS_UBUNTU=1
                OS_DEBIAN=0
            fi

            ;;
        Darwin )
            echo "[ERROR] Detected Mac Operating System. Currently Unsupported. Support Pending"
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
if [[ OS_DEBIAN -gt 0 ]] || [[ OS_UBUNTU -gt 0 ]]; then

    if [[ OS_DEBIAN -gt 0 ]]; then
        # Test for minimal version
        VERSION=$(cat /etc/debian_version)
        if [[ "${VERSION:0:1}" != "8" ]]; then
            echo "[ERROR] Minimal Debian version of 8 (jessie) required."
            exit 1
        fi
        echo "[INFO] Installing Debian specific dependencies..."
        apt-get -qq -y install elasticsearch
        if [[ $? -ne 0 ]]; then
            echo "[ERROR] Cannot install Debian specific dependencies."
            exit
        fi
        echo "[OKAY] Debian specific dependencies installed"
    fi

    if [[ OS_UBUNTU -gt 0 ]]; then
        . /etc/lsb-release
        if [[ ${DISTRIB_RELEASE:0:2} -lt 14 ]]; then
            echo "[ERROR] Minimal Ubuntu version of 14.04 (trusty) required."
            exit 1
        fi

        echo "[INFO] Installing Ubuntu specific dependencies..."

        # Install Elasticsearch
        apt-get -qq -y install openjdk-7-jre-headless
        if [[ $? -ne 0 ]]; then
            echo "[ERROR] Cannot install Debian specific dependencies."
            exit
        fi

        wget --no-check-certificate -O /tmp/elasticsearch-1.7.2.deb \
            https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-1.7.2.deb && dpkg -i /tmp/elasticsearch-1.7.2.deb
        if [[ $? -ne 0 ]]; then
            echo "[ERROR] Could not install Ubuntu specific elasticsearch."
            exit
        fi
        echo "[OKAY] Ubuntu specific dependencies installed"
    fi


    # Apt Dependencies
    echo -n "Installing Apt Dependencies..."
    apt-get -qq -y install git python3 python3-requests python3-yaml python3-dnspython python3-pip python3-dateutil
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot Apt Install dependencies."
        exit
    fi
    echo "Done"

    # Pip dependencies
    echo -n "Installing Pip3 Dependencies..."
    pip3 -q install pygeoip feedparser tabulate
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot Pip Install dependencies."
        exit
    fi
    echo "Done"

    # Modify elasticsearch to startup automatically
    cat /etc/default/elasticsearch | sed -e 's/#START_DAEMON/START_DAEMON/' > /etc/default/elasticsearch.new
    mv /etc/default/elasticsearch.new /etc/default/elasticsearch

    if [[ OS_DEBIAN -gt 0 ]]; then
        systemctl stop elasticsearch
        systemctl start elasticsearch
    fi
    if [[ OS_UBUNTU -gt 0 ]]; then
        service elasticsearch stop
        service elasticsearch start
    fi

    # Wait for a little bit for elastic search to start up
    ES_STARTED=0
    for i in {1..15}; do
        if [[ $(netstat -nplt | grep -c 9200) -gt 0 ]]; then
            ES_STARTED=1
            break
        fi
        sleep 1
    done
    
    if [[ $ES_STARTED -lt 1 ]]; then
        echo "[ERROR] ElasticSearch should have started by now. Fix elasticsearch then re-run this script"
    fi

    # Create CIF user
    useradd -r -d /opt/cifpy3 -M cif

    # clone cifpy3 to /opt/
    echo "Cloning CIFpy3 to /opt/cifpy3"
    git clone https://github.com/jmdevince/cifpy3.git /opt/cifpy3
    if [[ $? -ne 0 ]]; then
        echo "[ERRROR] Could not clone cifpy3"
        exit
    fi

    chown cif:cif -Rf /opt/cifpy3

    # Copy systemd scripts
    if [[ OS_DEBIAN -gt 0 ]]; then
        cp /opt/cifpy3/scripts/debian/cif-server.systemd /etc/systemd/system/cif-server.service
        cp /opt/cifpy3/scripts/debian/cif-server.default /etc/default/cif-server
    fi
    if [[ OS_UBUNTU -gt 0 ]]; then
        cp /opt/cifpy3/scripts/ubuntu/cif-server.upstart /etc/init/cif-server.conf
        cp /opt/cifpy3/scripts/ubuntu/cif-server.default /etc/default/cif-server
    fi

    # Download GeoIP data
    /opt/cifpy3/bin/cif-utility -g

    # Run the cif initial install
    TOKEN=$(/opt/cifpy3/bin/cif-utility -r)
    
    # Write the token out to ~/.cif
    echo "${TOKEN}" > ~/.cif
    
    # Add CIF to everyone's $PATH (also add it to running shell)
    echo 'PATH="${PATH}:/opt/cifpy3/bin/"' > /etc/profile.d/cif.sh
    . /etc/profile.d/cif.sh
    export PATH="${PATH}"

    # Start it up, need to detect which version
    if [[ OS_DEBIAN -gt 0 ]]; then
        systemctl enable cif-server
        systemctl start cif-server
    fi
    if [[ OS_UBUNTU -gt 0 ]]; then
        service cif-server start
    fi
    # Print information
    echo "[OKAY] CIF has been installed. You can now use the 'cif' command. (You may have to logout/login)"
    echo "[OKAY] Your ADMIN API token is ${TOKEN}. It has also been written to ~/.cif"

fi
