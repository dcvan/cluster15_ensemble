#!/bin/bash
function testSSH() {
        local user=${1}
        local host=${2}
        local timeout=${3}
        
        SSH_OPTS="-q -o PreferredAuthentications=publickey -o HostbasedAuthentication=no -o PasswordAuthentication=no -o StrictHostKeyChecking=no"
        
        ssh -q -q $SSH_OPTS -o "BatchMode=yes" -o "ConnectTimeout ${timeout}"  ${user}@${host} "echo 2>&1" && return 0 || return 1
}

# host setup
while [ ! "$(ifconfig eth1|grep 'inet addr'|cut -d':' -f2|awk '{print $1}'|cut -d'.' -f4)" ];do
    sleep 10
done
ip_end=$(ifconfig eth1|grep 'inet addr'|cut -d':' -f2|awk '{print $1}'|cut -d'.' -f4)
name=$(($ip_end-100))
MY_HOSTNAME="condor-w$name"
hostname $MY_HOSTNAME

MASTER=172.16.1.1
cat >/etc/hosts <<EOF
$MASTER   master.expnet   master   salt
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
EOF

for i in {100..200}; do
   name=$(($i-100))
   echo 172.16.1.$i  condor-w$name\.expnet condor-w$name >> /etc/hosts
done

# condor setup
cat >  /etc/condor/config.d/90-worker << EOF
DAEMON_LIST = MASTER, STARTD, SCHEDD
CONDOR_HOST = master.expnet
ALLOW_WRITE = *
HOSTALLOW_READ = *
HOSTALLOW_WRITE = *
EOF

UNPINGABLE=true
for ((i=0;i<60;i+=1));
do
      echo "testing ping, try: $i " >> /tmp/bootscript.out
      PING=`ping -c 3 master > /dev/null 2>&1`
      if [ "$?" = "0" ]; then
           UNPINGABLE=false
           break
       fi
       sleep 10
done
mkdir -m 775 /var/log/condor
chown condor:condor /var/log/condor
service condor restart

# NFS setup
mkdir -p /mnt/scratch
chown -R pegasus-user:pegasus-user /mnt/scratch
yum -y install nfs-utils nfs-utils-lib
cat >> /etc/fstab << EOF
$MASTER:/mnt/scratch       /mnt/scratch    nfs     vers=3,proto=tcp,hard,nolock,intr,timeo=600,retrans=2,wsize=32768,rsize=32768   0       0
EOF
mount -a

# workflow setup
tar zxf /home/pegasus-user/genomics/references.tgz -C /home/pegasus-user/genomics
chown -R pegasus-user:pegasus-user /home/pegasus-user/genomics
