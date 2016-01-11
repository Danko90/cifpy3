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
OS_FREEBSD=0

# Get the OS Type
function os_type
{
    case `uname` in
        Linux )
            echo "[OKAY] Detected Linux Operating System"
            OS_LINUX=1

            if [[ -f /etc/redhat-release ]]; then
                echo "[OKAY] Detected CentOS distribution"
                OS_REDHAT=1
                OS_CENTOS=0
            fi

            if [[ -f /etc/centos-release ]]; then
                echo "[OKAY] Detected CentOS distribution"
                OS_REDHAT=0
                OS_CENTOS=1
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
        FreeBSD )
            echo "[OKAY] FreeBSD Detected"
            OS_FREEBSD=1
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

if [[ OS_FREEBSD -gt 0 ]]; then

    VERSION=$(uname -r | awk -F"." ' { print $1 } ')
    if [[ ${VERSION} -lt 10 ]]; then
        echo "[ERROR] Minimal Version of FreeBSD 10 required."
        exit 1
    fi

    echo "[INFO] Installing FreeBSD PKG dependencies..."
    pkg install -y python34 wget git elasticsearch
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot FreeBSD PKG dependencies."
        exit 1
    fi
    ln -s /usr/local/bin/python3.4 /usr/local/bin/python3
    echo "[OKAY] FreeBSD PKG Installed"

    echo "[INFO] Installing Python PIP for FreeBSD"
    wget --no-check-certificate -O /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py
    python3 /tmp/get-pip.py
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Could not install Python PIP for FreeBSD"
        exit 1
    fi
    echo "[OKAY] Installed Python PIP for FreeBSD"


    echo -n "[INFO] Installing Pip3 dependencies..."
    scl enable rh-python34 -- pip3 -q install pygeoip feedparser tabulate pyyaml requests dnspython3 python-dateutil schedule beautifulsoup4 setproctitle
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot Pip Install dependencies."
        exit
    fi
    echo "[OKAY] Installed Pip3 dependencies"

    echo "[INFO] Modifying fstab and mounting /dev/fd and /proc for elasticsearch"
    echo "fdesc	/dev/fd	fdescfs	rw	0	0" >> /etc/fstab
    echo "proc	/proc	procfs	rw	0	0" >> /etc/fstab
    mount /proc && mount /dev/fd
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Could not mount /dev/fd or /proc for elasticsearch."
        exit
    fi
    echo "[OKAY] Modified FSTAB and mounted /dev/fd and /proc for elasticsearch"

    echo "[INFO] Finishing Elasticsearch installation"
    echo 'elasticsearch_enable="YES"' >> /etc/rc.conf
    service elasticsearch start

    # Wait for a little bit for elastic search to start up
    ES_STARTED=0
    for i in {1..15}; do
        if [[ $(netstat -an | egrep 'Proto|LISTEN' | grep -c 9200) -gt 0 ]]; then
            ES_STARTED=1
            break
        fi
        sleep 1
    done

    if [[ $ES_STARTED -lt 1 ]]; then
        echo "[ERROR] ElasticSearch should have started by now. Fix elasticsearch then re-run this script"
        exit 1
    fi

    echo cif::::::/usr/local/cifpy3/:/bin/bash: | adduser -w no -f -

    # clone cifpy3 to /opt/
    echo "Cloning CIFpy3 to /usr/local/cifpy3"
    git clone https://github.com/Danko90/cifpy3.git /usr/local/cifpy3
    if [[ $? -ne 0 ]]; then
        echo "[ERRROR] Could not clone cifpy3"
        exit
    fi

    chown -Rf cif:cif /usr/local/cifpy3

    # Copy systemd scripts
    cp /usr/local/cifpy3/scripts/freebsd/cif-server.rc /usr/local/etc/rc.d/cif-server
    chmod +x /usr/local/etc/rc.d/cif-server

    echo 'cifserver_enable="YES"' >> /etc/rc.local
    echo 'cifserver_flags=""' >> /etc/rc.local

    # Download GeoIP data
    /usr/local/cifpy3/bin/cif-utility -g

    # Run the cif initial install
    TOKEN=$(/usr/local/cifpy3/bin/cif-utility -r)

    # Write the token out to ~/.cif
    echo "${TOKEN}" > ~/.cif

    # Add CIF to everyone's $PATH (also add it to running shell)
    echo 'PATH="${PATH}:/usr/local/cifpy3/bin/"' >> /etc/profile
    echo 'PATH="${PATH}:/usr/local/cifpy3/bin/"' >> ~/.profile
    echo 'export PATH' >> ~/.profile
    echo 'setenv PATH /usr/local/cifpy3/bin/:$PATH' >> /etc/csh.cshrc
    echo 'setenv PATH /usr/local/cifpy3/bin/:$PATH' >> ~/.cshrc

    # Start it up
    service start cif-server

    # Print information
    echo "[OKAY] CIF has been installed. You can now use the 'cif' command. (You may have to logout/login)"
    echo "[OKAY] Your ADMIN API token is ${TOKEN}. It has also been written to ~/.cif"

fi

if [[ OS_CENTOS -gt 0 ]] || [[ OS_REDHAT -gt 0 ]]; then

    if [[ OS_CENTOS -gt 0 ]]; then
        VERSION=$(cat /etc/centos-release | awk -F" " ' { print $4 } ' | awk -F"." ' { print $1 } ')
        if [[ ${VERSION} -lt 7 ]]; then
            echo "[ERROR] Minimal Version of CentOS 7 required."
            exit 1
        fi
    fi

    if [[ OS_REDHAT -gt 0 ]]; then
        VERSION=$(cat /etc/redhat-release | awk -F" " ' { print $7 } ' | awk -F"." ' { print $1 } ')
        if [[ ${VERSION} -lt 7 ]]; then
            echo "[ERROR] Minimal Version of RedHat 7 required."
            exit 1
        fi
        subscription-manager repos --enable rhel-7-server-optional-rpms
    fi

    echo "[INFO] Installing CentOS dependencies..."
    yum -q -y install scl-utils wget java-1.8.0-openjdk-headless net-tools git
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot install CentOS dependencies."
        exit
    fi
    echo "[OKAY] CentOS dependencies Installed"

    echo "[INFO] Installing Python34 from SoftwareCollections..."
    wget --no-check-certificate -O /tmp/rhscl-rh-python34-epel-7-x86_64.noarch.rpm https://www.softwarecollections.org/en/scls/rhscl/rh-python34/epel-7-x86_64/download/rhscl-rh-python34-epel-7-x86_64.noarch.rpm
    rpm -i /tmp/rhscl-rh-python34-epel-7-x86_64.noarch.rpm
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot install Python34 repository."
        exit
    fi
    rm -f /tmp/rhscl-rh-python34-epel-7-x86_64.noarch.rpm
    yum -q -y install rh-python34
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot install Python34 packages."
        exit
    fi
    echo "[OKAY] Installed Python34"

    echo -n "[INFO] Installing Pip3 dependencies..."
    scl enable rh-python34 -- pip3 -q install pygeoip feedparser tabulate pyyaml requests dnspython3 python-dateutil schedule beautifulsoup4 setproctitle
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot Pip Install dependencies."
        exit
    fi
    echo "[OKAY] Installed Pip3 dependencies"

    echo -n "[INFO] Installing Elasticsearch..."
    wget -O /tmp/elasticsearch-1.7.2.noarch.rpm https://download.elastic.co/elasticsearch/elasticsearch/elasticsearch-1.7.2.noarch.rpm
    rpm -i /tmp/elasticsearch-1.7.2.noarch.rpm
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot install Elasticsearch package."
        exit
    fi
    systemctl daemon-reload
    systemctl enable elasticsearch.service
    systemctl start elasticsearch.service

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
        exit 1
    fi

    # Create CIF user
    useradd -r -d /usr/local/cifpy3 -M cif

    # clone cifpy3 to /opt/
    echo "Cloning CIFpy3 to /usr/local/cifpy3"
    git clone https://github.com/Danko90/cifpy3.git /usr/local/cifpy3
    if [[ $? -ne 0 ]]; then
        echo "[ERRROR] Could not clone cifpy3"
        exit
    fi

    chown cif:cif -Rf /usr/local/cifpy3

    # Copy systemd scripts
    cp /usr/local/cifpy3/scripts/centos/cif-server.systemd /usr/lib/systemd/system/cif-server.service
    cp /usr/local/cifpy3/scripts/centos/cif-server.sysconfig /etc/sysconfig/cif-server

    # Download GeoIP data
    scl enable rh-python34 -- /usr/local/cifpy3/bin/cif-utility -g

    # Run the cif initial install
    TOKEN=$(scl enable rh-python34 -- /usr/local/cifpy3/bin/cif-utility -r)

    # Write the token out to ~/.cif
    echo "${TOKEN}" > ~/.cif

    # Add CIF to everyone's $PATH (also add it to running shell)
    echo "alias cif='scl enable rh-python34 -- /usr/local/cifpy3/bin/cif'" > /etc/profile.d/cif.sh
    echo "alias cif-utility='scl enable rh-python34 -- /usr/local/cifpy3/bin/cif-utility'" >> /etc/profile.d/cif.sh

    # Start it up, need to detect which version
    systemctl enable cif-server.service
    systemctl start cif-server.service

    # Print information
    echo "[OKAY] CIF has been installed. You can now use the 'cif' command. (You may have to logout/login)"
    echo "[OKAY] Your ADMIN API token is ${TOKEN}. It has also been written to ~/.cif"


fi

# Install Debian Dependencies
if [[ OS_DEBIAN -gt 0 ]] || [[ OS_UBUNTU -gt 0 ]]; then

    if [[ OS_DEBIAN -gt 0 ]]; then
        # Test for minimal version
        VERSION=$(cat /etc/debian_version)
        if [[ ${VERSION:0:1} -lt 8 ]]; then
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
    apt-get -qq -y install git python3 python3-requests python3-yaml python3-dnspython python3-pip python3-dateutil python3-bs4
    if [[ $? -ne 0 ]]; then
        echo "[ERROR] Cannot Apt Install dependencies."
        exit
    fi
    echo "Done"

    # Pip dependencies
    echo -n "Installing Pip3 Dependencies..."
    pip3 -q install pygeoip feedparser tabulate schedule setproctitle
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
        exit 1
    fi

    # Create CIF user
    useradd -r -d /usr/local/cifpy3 -M cif

    # clone cifpy3 to /opt/
    echo "Cloning CIFpy3 to /usr/local/cifpy3"
    git clone https://github.com/Danko90/cifpy3.git /usr/local/cifpy3
    if [[ $? -ne 0 ]]; then
        echo "[ERRROR] Could not clone cifpy3"
        exit
    fi

    chown cif:cif -Rf /usr/local/cifpy3

    # Copy systemd scripts
    if [[ OS_DEBIAN -gt 0 ]]; then
        cp /usr/local/cifpy3/scripts/debian/cif-server.systemd /etc/systemd/system/cif-server.service
        cp /usr/local/cifpy3/scripts/debian/cif-server.default /etc/default/cif-server
    fi
    if [[ OS_UBUNTU -gt 0 ]]; then
        cp /usr/local/cifpy3/scripts/ubuntu/cif-server.upstart /etc/init/cif-server.conf
        cp /usr/local/cifpy3/scripts/ubuntu/cif-server.default /etc/default/cif-server
    fi

    # Download GeoIP data
    /usr/local/cifpy3/bin/cif-utility -g

    # Run the cif initial install
    TOKEN=$(/usr/local/cifpy3/bin/cif-utility -r)
    
    # Write the token out to ~/.cif
    echo "${TOKEN}" > ~/.cif
    
    # Add CIF to everyone's $PATH (also add it to running shell)
    echo 'PATH="${PATH}:/usr/local/cifpy3/bin/"' > /etc/profile.d/cif.sh
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
