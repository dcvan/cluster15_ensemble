#!/usr/bin/env bash

# host setup
cat &gt;/etc/hosts &lt;&lt;EOF
172.16.1.1  master.expnet   master   salt
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
EOF

hostname master

for i in {100..200}; do
   name=$(($i - 100))
   echo 172.16.1.$i  condor-w$name condor-w$name\.expnet &gt;&gt; /etc/hosts
done

# condor setup
service condor stop
cat &gt; /etc/condor/condor_config.local &lt;&lt; EOF
SLOT_TYPE_1 = cpus=100%, ram=100%, swap=25%, disk=75%
NUM_SLOTS_TYPE_1 = 1
EOF

cat &gt;&gt;  /etc/condor/config.d/10-common.conf &lt;&lt; EOF
UID_DOMAIN = expnet
TRUST_UID_DOMAIN = True
SOFT_UID_DOMAIN = True
EOF

cat &gt;  /etc/condor/config.d/90-master &lt;&lt; EOF
DAEMON_LIST = COLLECTOR, MASTER, NEGOTIATOR, SCHEDD
CONDOR_HOST = master.expnet
ALLOW_WRITE = *
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *
EOF
 
service condor restart

mkdir -p /mnt/scratch
chown -R pegasus-user:pegasus-user /mnt/scratch

{% if param['storage_type'] == 'nfs' %}
# NFS server setup
yum -y install nfs-utils nfs-utils-lib
cat &gt;&gt; /etc/exports &lt;&lt; EOF
/mnt/scratch *(rw,sync,no_root_squash,no_subtree_check)
EOF
exportfs -a
/etc/init.d/rpcbind start
/etc/init.d/nfs start
{% endif %}

# workflow setup

sed -i 's/local/condorpool/g' /home/pegasus-user/20131031/montage/workflow/cache.list
cat &gt;&gt; /home/pegasus-user/20131031/montage/pegasusrc &lt;&lt; EOF
pegasus.transfer.link = true
pegasus.transfer.bypass.input.staging = true
pegasus.data.configuration=nonsharedfs
EOF

cat &gt; /home/pegasus-user/20131031/montage/submit &lt;&lt;EOF
#!/bin/bash

set -e

MONTAGE_HOME=\$(pwd)
TOP_DIR=\$(pwd)
DATA_DIR='/mnt/scratch'
HOSTNAME=\$(/bin/hostname -f)
DATA_CONFIG="condorio" 
STAGING_SITE="local"
PROTOCOL="file"

# unique directory for this run
RUN_DIR=\$TOP_DIR

cd \$RUN_DIR
cp \$TOP_DIR/workflow/dag.xml .
for BINARY in \$(cd \$MONTAGE_HOME/bin &amp;&amp; ls); do
    name=\$BINARY:3.3
    if [ "\${BINARY}" = "mFitplane" ] || [ "\$BINARY" = "mDiff" ]; then
	name=\$BINARY
    fi
cat &gt;&gt;tc &lt;&lt;END
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
cat &gt; sites.xml &lt;&lt;END
&lt;?xml version="1.0" encoding="UTF-8"?&gt;
&lt;sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-3.0.xsd" version="3.0"&gt;
    &lt;site handle="local" arch="x86_64" os="LINUX"&gt;
        &lt;grid  type="gt2" contact="localhost/jobmanager-fork" scheduler="Fork" jobtype="auxillary"/&gt;
        &lt;head-fs&gt;
            &lt;scratch&gt;
                &lt;shared&gt;
                    &lt;file-server protocol="file" url="file://" mount-point="/mnt/scratch"/&gt;
                    &lt;internal-mount-point mount-point="/mnt/scratch"/&gt;
                &lt;/shared&gt;
            &lt;/scratch&gt;
            &lt;storage&gt;
                &lt;shared&gt;
                    &lt;file-server protocol="file" url="file://" mount-point="/mnt/scratch/outputs"/&gt;
                    &lt;internal-mount-point mount-point="/mnt/scratch/outputs"/&gt;
                &lt;/shared&gt;
            &lt;/storage&gt;
        &lt;/head-fs&gt;
        &lt;profile namespace="env" key="MONTAGE_HOME" &gt;\$MONTAGE_HOME&lt;/profile&gt;
        &lt;profile namespace="env" key="PEGASUS_HOME" &gt;/usr&lt;/profile&gt;
        &lt;profile namespace="env" key="SSH_PRIVATE_KEY" &gt;\$HOME/creds/wf_key&lt;/profile&gt;
    &lt;/site&gt;
    &lt;site handle="condorpool" arch="x86_64" os="LINUX"&gt;
        &lt;head-fs&gt;
	    &lt;scratch&gt;
                &lt;shared&gt;
                    &lt;file-server protocol="file" url="file://" mount-point="/mnt/scratch"/&gt;
                    &lt;internal-mount-point mount-point="/mnt/scratch"/&gt;
                &lt;/shared&gt;
            &lt;/scratch&gt;
            &lt;storage /&gt;
        &lt;/head-fs&gt;
        &lt;profile namespace="pegasus" key="style"&gt;condor&lt;/profile&gt;
        &lt;profile namespace="condor" key="universe"&gt;vanilla&lt;/profile&gt;
        &lt;profile namespace="condor" key="requirements" &gt;(Target.Arch == "X86_64")&lt;/profile&gt;
        &lt;profile namespace="env" key="PEGASUS_BIN_DIR" &gt;/usr/bin&lt;/profile&gt;
    &lt;/site&gt;
&lt;/sitecatalog&gt;
END

cp \$TOP_DIR/workflow/cache.list .

perl -pi.bak -e "s{\@\@REPLACE_HERE\@\@}{\$DATA_DIR}g" cache.list

pegasus-plan \
    --conf pegasusrc \
    --sites condorpool \
    --staging-site condorpool \
    --output-site local \
    --dax dag.xml \
    --cluster horizontal \
    --submit

EOF

# monitor setup
yum -y install python-pip python-devel git
pip install pika tornado psutil argparse
git clone https://github.com/dcvan/cluster15_ensemble.git ~/cluster

# start monitor
python /root/cluster/performance-monitor/producer/check_pegasus.py -i {{param['exp_id']}} -m -d /home/pegasus-user/20131031/montage/pegasus-user/pegasus/montage -r {{param['run_num']}} &amp;

while [ "$(condor_status -total | grep -E 'Total[ \t]+[0-9]'|awk '{print $2}')" != "{{param['worker_num']}}" ];do
	sleep 5
done 

# start workflow
sleep 10
for (( i = 0; i &lt; {{param['run_num']}}; i ++ ))
do
	su pegasus-user -c 'cd /home/pegasus-user/20131031/montage/; bash submit'
	sleep 2
done
