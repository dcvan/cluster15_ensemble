#!/usr/bin/env bash

# host setup
cat >/etc/hosts <<EOF
172.16.1.1  master.expnet   master   salt
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
EOF

hostname master

for i in {100..200}; do
   name=$(($i - 100))
   echo 172.16.1.$i  condor-w$name condor-w$name\.expnet >> /etc/hosts
done

# condor setup
cat >  /etc/condor/config.d/90-master << EOF
DAEMON_LIST = COLLECTOR, MASTER, NEGOTIATOR, SCHEDD
CONDOR_HOST = master.expnet
ALLOW_WRITE = *
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *
EOF
mkdir -m 775 /var/log/condor
chown condor:condor /var/log/condor
service condor restart

# NFS server setup
mkdir -p /mnt/scratch
chown -R pegasus-user:pegasus-user /mnt/scratch

yum -y install nfs-utils nfs-utils-lib
cat >> /etc/exports << EOF
/mnt/scratch *(rw,sync,no_root_squash,no_subtree_check)
EOF
exportfs -a
/etc/init.d/rpcbind start
/etc/init.d/nfs start

# workflow setup 
tar zxf /home/pegasus-user/genomics/references.tgz -C /home/pegasus-user/genomics
chown -R pegasus-user:pegasus-user /home/pegasus-user/genomics
sed -i 's/transfer="false"/transfer="true"/g' /home/pegasus-user/genomics/wf_exon_irods/dax.xml
cat > /home/pegasus-user/genomics/wf_exon_irods/sites.xml <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-4.0.xsd" version="4.0">
    <site  handle="local" arch="x86_64" os="LINUX">
        <directory type="shared-scratch" path="/mnt/scratch">
            <file-server operation="all" url="file:///mnt/scratch"/>
        </directory>
        <directory type="local-storage" path="/mnt/scratch/output">
            <file-server operation="all" url="file:///mnt/scratch/output"/>
        </directory>
        <profile namespace="env" key="PATH" >/home/pegasus-user/iRODS/clients/icommands/bin:/bin:/usr/bin</profile>
        <profile namespace="env" key="PEGASUS_HOME" >/usr</profile>
        <profile namespace="env" key="SSH_PRIVATE_KEY" >/home/pegasus-user/creds/wf_key</profile>
        <profile namespace="env" key="irodsEnvFile" >/home/pegasus-user/.irods/.irodsEnv</profile>
    </site>
    <site  handle="condor_pool" arch="x86_64" os="LINUX">
        <directory type="shared-scratch" path="/mnt/scratch">
            <file-server operation="all" url="file:///mnt/scratch"/>
        </directory>
        <profile namespace="pegasus" key="style" >condor</profile>
        <profile namespace="condor" key="universe" >vanilla</profile>
        <profile namespace="env" key="PATH" >/home/pegasus-user/iRODS/clients/icommands/bin:/bin:/usr/bin</profile>
        <profile namespace="env" key="PEGASUS_HOME" >/usr</profile>
    </site>
</sitecatalog>
EOF

# monitor setup
yum -y install python-pip python-devel git
pip install pika tornado psutil
git clone https://github.com/dcvan/cluster15_ensemble.git
