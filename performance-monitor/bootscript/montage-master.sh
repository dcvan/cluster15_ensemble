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
service condor stop
cat > /etc/condor/condor_config.local << EOF
SLOT_TYPE_1 = cpus=100%, ram=100%, swap=25%, disk=75%
NUM_SLOTS_TYPE_1 = 1
EOF

cat >>  /etc/condor/config.d/10-common.conf << EOF
UID_DOMAIN = expnet
TRUST_UID_DOMAIN = True
SOFT_UID_DOMAIN = True
EOF

cat >  /etc/condor/config.d/90-master << EOF
DAEMON_LIST = COLLECTOR, MASTER, NEGOTIATOR, SCHEDD
CONDOR_HOST = master.expnet
ALLOW_WRITE = *
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *
EOF
 
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

sed -i 's/local/condorpool/g' /home/pegasus-user/20131031/montage/workflow/cache.list
cat >> /home/pegasus-user/20131031/montage/pegasusrc << EOF
pegasus.transfer.link = true
pegasus.transfer.bypass.input.staging = true
pegasus.data.configuration=nonsharedfs
EOF

cat > /home/pegasus-user/20131031/montage/submit <<EOF
#!/bin/bash

set -e

MONTAGE_HOME=\$(pwd)
TOP_DIR=\$(pwd)
HOSTNAME=\$(/bin/hostname -f)
DATA_CONFIG="condorio" 
STAGING_SITE="local"
PROTOCOL="file"

# unique directory for this run
RUN_DIR=\$TOP_DIR

cd \$RUN_DIR
cp \$TOP_DIR/workflow/dag.xml .
for BINARY in \$(cd $MONTAGE_HOME/bin && ls); do
    name=$BINARY:3.3
    if [ "\${BINARY}" = "mFitplane" ] || [ "\$BINARY" = "mDiff" ]; then
	name=\$BINARY
    fi
cat >>tc <<END
tr \$name {
    site condorpool {
        pfn "\$MONTAGE_HOME/bin/\$BINARY"
        arch "x86_64"
        os "linux"
        type "STAGEABLE"
        profile pegasus "clusters.num" "5"
        profile env "MONTAGE_BIN" "."
    }
}
END
  
done
cat > sites.xml <<END
<?xml version="1.0" encoding="UTF-8"?>
<sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-3.0.xsd" version="3.0">
    <site handle="local" arch="x86_64" os="LINUX">
        <grid  type="gt2" contact="localhost/jobmanager-fork" scheduler="Fork" jobtype="auxillary"/>
        <head-fs>
            <scratch>
                <shared>
                    <file-server protocol="file" url="file://" mount-point="/mnt/scratch"/>
                    <internal-mount-point mount-point="/mnt/scratch"/>
                </shared>
            </scratch>
            <storage>
                <shared>
                    <file-server protocol="file" url="file://" mount-point="/mnt/outputs"/>
                    <internal-mount-point mount-point="/mnt/outputs"/>
                </shared>
            </storage>
        </head-fs>
        <profile namespace="env" key="MONTAGE_HOME" >\$MONTAGE_HOME</profile>
        <profile namespace="env" key="PEGASUS_HOME" >/usr</profile>
        <profile namespace="env" key="SSH_PRIVATE_KEY" >\$HOME/creds/wf_key</profile>
    </site>
    <site handle="condorpool" arch="x86_64" os="LINUX">
        <head-fs>
	    <scratch>
                <shared>
                    <file-server protocol="file" url="file://" mount-point="/mnt/scratch"/>
                    <internal-mount-point mount-point="/mnt/scratch"/>
                </shared>
            </scratch>
            <storage />
        </head-fs>
        <profile namespace="pegasus" key="style">condor</profile>
        <profile namespace="condor" key="universe">vanilla</profile>
        <profile namespace="condor" key="requirements" >(Target.Arch == "X86_64")</profile>
        <profile namespace="env" key="PEGASUS_BIN_DIR" >/usr/bin</profile>
    </site>
</sitecatalog>
END

cp \$TOP_DIR/workflow/cache.list .

perl -pi.bak -e "s{\@\@REPLACE_HERE\@\@}{\$TOP_DIR}g" cache.list

pegasus-plan \
    --conf pegasusrc \
    --sites condorpool \
    --staging-site condorpool \
    --output-site local \
    --dax dag.xml \
    --cluster horizontal \
    --submit

EOF
