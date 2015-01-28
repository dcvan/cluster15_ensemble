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
      cat &gt;  /etc/condor/config.d/90-master &lt;&lt; EOF
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
      cat &gt;&gt; /etc/exports &lt;&lt; EOF
      /mnt/scratch *(rw,sync,no_root_squash,no_subtree_check)
      EOF
      exportfs -a
      /etc/init.d/rpcbind start
      /etc/init.d/nfs start

      # workflow setup 
      tar zxf /home/pegasus-user/genomics/references.tgz -C /home/pegasus-user/genomics
      chown -R pegasus-user:pegasus-user /home/pegasus-user/genomics
      sed -i 's/transfer="false"/transfer="true"/g' /home/pegasus-user/genomics/wf_exon_irods/dax.xml
      cat &gt; /home/pegasus-user/genomics/wf_exon_irods/sites.xml &lt;&lt;EOF
      &lt;?xml version="1.0" encoding="UTF-8"?&gt;
      &lt;sitecatalog xmlns="http://pegasus.isi.edu/schema/sitecatalog" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pegasus.isi.edu/schema/sitecatalog http://pegasus.isi.edu/schema/sc-4.0.xsd" version="4.0"&gt;
          &lt;site  handle="local" arch="x86_64" os="LINUX"&gt;
                  &lt;directory type="shared-scratch" path="/mnt/scratch"&gt;
                              &lt;file-server operation="all" url="file:///mnt/scratch"/&gt;
                                      &lt;/directory&gt;
                                              &lt;directory type="local-storage" path="/mnt/scratch/output"&gt;
                                                          &lt;file-server operation="all" url="file:///mnt/scratch/output"/&gt;
                                                                  &lt;/directory&gt;
                                                                          &lt;profile namespace="env" key="PATH" &gt;/home/pegasus-user/iRODS/clients/icommands/bin:/bin:/usr/bin&lt;/profile&gt;
                                                                                  &lt;profile namespace="env" key="PEGASUS_HOME" &gt;/usr&lt;/profile&gt;
                                                                                          &lt;profile namespace="env" key="SSH_PRIVATE_KEY" &gt;/home/pegasus-user/creds/wf_key&lt;/profile&gt;
                                                                                                  &lt;profile namespace="env" key="irodsEnvFile" &gt;/home/pegasus-user/.irods/.irodsEnv&lt;/profile&gt;
                                                                                                      &lt;/site&gt;
                                                                                                          &lt;site  handle="condor_pool" arch="x86_64" os="LINUX"&gt;
                                                                                                                  &lt;directory type="shared-scratch" path="/mnt/scratch"&gt;
                                                                                                                              &lt;file-server operation="all" url="file:///mnt/scratch"/&gt;
                                                                                                                                      &lt;/directory&gt;
                                                                                                                                              &lt;profile namespace="pegasus" key="style" &gt;condor&lt;/profile&gt;
                                                                                                                                                      &lt;profile namespace="condor" key="universe" &gt;vanilla&lt;/profile&gt;
                                                                                                                                                              &lt;profile namespace="env" key="PATH" &gt;/home/pegasus-user/iRODS/clients/icommands/bin:/bin:/usr/bin&lt;/profile&gt;
                                                                                                                                                                      &lt;profile namespace="env" key="PEGASUS_HOME" &gt;/usr&lt;/profile&gt;
                                                                                                                                                                          &lt;/site&gt;
                                                                                                                                                                          &lt;/sitecatalog&gt;
                                                                                                                                                                          EOF

                                                                                                                                                                          # monitor setup
                                                                                                                                                                          yum -y install python-pip python-devel git
                                                                                                                                                                          pip install pika tornado psutil argparse
                                                                                                                                                                          git clone https://github.com/dcvan/cluster15_ensemble.git ~/cluster

                                                                                                                                                                          # start monitor 
                                                                                                                                                                          python /root/cluster/performance-monitor/producer/check_pegasus.py -i {{param['exp_id']}} -m -d /home/pegasus-user/genomics/wf_exon_irods/pegasus-user/pegasus/exonalignwf -r {{param['run_num']}} &amp; 

                                                                                                                                                                          while [ "$(condor_status -total | grep -E 'Total[ \t ]+[0-9]'|awk '{print $2}')" != "{{param['worker_num']}}"  ];do
                                                                                                                                                                                sleep 5
                                                                                                                                                                            done 

                                                                                                                                                                            # start workflow
                                                                                                                                                                            sleep 10
                                                                                                                                                                            for (( i = 0; i &lt; {{param['run_num']}}; i ++  ))
                                                                                                                                                                            do
                                                                                                                                                                                    su pegasus-user -c 'cd /home/pegasus-user/genomics/wf_exon_irods; bash genplan.sh'
                                                                                                                                                                                        sleep 2
                                                                                                                                                                                    done