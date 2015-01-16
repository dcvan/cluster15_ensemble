#!/usr/bin/env bash

condor_log="/var/log/condor"
pegasus_home="/home/pegasus-user"
geno_home="$pegasus_home/genomics"
reference_tar="$geno_home/references.tgz"

echo -n 'Rename the VM ... '
cat > /etc/hosts <<EOF
$(ifconfig eth0|grep 'inet addr'|awk -F':' '{print $2}'|awk '{print $1}')  master.expnet   master   salt
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
EOF
hostname master
echo 'Done'

echo -n 'Modify condor configuration ... '
echo "" > /etc/condor/condor_config.local
cat > /etc/condor/config.d/90-worker <<EOF
DAEMON_LIST = MASTER, STARTD, NEGOTIATOR, SCHEDD, COLLECTOR
CONDOR_HOST = master.expnet
ALLOW_WRITE = *
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *
EOF

cat > /etc/condor/config.d/20-security <<EOF
SEC_PASSWORD_FILE = /etc/condor/pool.password
SEC_DAEMON_AUTHENTICATION = REQUIRED
SEC_DAEMON_INTEGRITY = REQUIRED
SEC_DAEMON_AUTHENTICATION_METHODS = PASSWORD
SEC_NEGOTIATOR_AUTHENTICATION = REQUIRED
SEC_NEGOTIATOR_INTEGRITY = REQUIRED
SEC_NEGOTIATOR_AUTHENTICATION_METHODS = PASSWORD
SEC_CLIENT_AUTHENTICATION_METHODS = FS, PASSWORD

ALLOW_ADMINISTRATOR = $(FULL_HOSTNAME), $(CONDOR_HOST), master.expnet
ALLOW_OWNER = $(ALLOW_ADMINISTRATOR)
ALLOW_READ = *
ALLOW_WRITE = *

ALLOW_DAEMON = $(ALLOW_WRITE)
ALLOW_ADVERTISE_STARTD = $(ALLOW_WRITE)
ALLOW_NEGOTIATOR = $(COLLECTOR_HOST)
ALLOW_NEGOTIATOR_SCHEDD = $(COLLECTOR_HOST)
ALLOW_WRITE_COLLECTOR = $(ALLOW_WRITE)
ALLOW_WRITE_STARTD    = $(ALLOW_WRITE)
ALLOW_READ_COLLECTOR  = $(ALLOW_READ)
ALLOW_READ_STARTD     = $(ALLOW_READ)
ALLOW_CLIENT = *
EOF
echo 'Done'

echo -n 'Change transfer option in DAX ... '
sed -i 's/transfer="false"/transfer="true"/g' $geno_home/wf_exon_irods/dax.xml
echo 'Done'
echo -n 'Create condor log directory ... '
mkdir -m 775 $condor_log
chown condor:condor $condor_log
echo 'Done'

echo -n 'Untar reference ... '
tar zxf $reference_tar -C $geno_home
echo 'Done'

service condor restart
# install dependencies
yum -y install git python-pip python-devel
pip install pika psutil tornado

git clone https://github.com/dcvan/cluster15_ensemble.git ~
