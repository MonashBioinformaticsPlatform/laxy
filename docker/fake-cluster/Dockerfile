FROM ubuntu:20.04

# Build like:
#   docker build -t fake-cluster:latest docker/fake-cluster
# Start like:
#   docker run -p 2222:22 -v /tmp/laxy:/scratch/laxy fake-cluster:latest
# Then:
#   chmod 600 docker/fake-cluster/id_rsa
#   ssh -o StrictHostKeyChecking=no -o StrictHostKeyChecking=no \
#       -i docker/fake-cluster/id_rsa -p 2222 root@localhost
#   sbatch --wrap="echo bla && sleep 10 && echo foo"
#   squeue
#

EXPOSE 22/tcp
VOLUME /scratch

RUN apt-get -y update && \
    apt-get -y install vim curl htop openssh-server slurm-wlm munge slurm-wlm-doc git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN bash -c 'echo -e "\nPort 2222\nPermitRootLogin prohibit-password\n" >>/etc/ssh/sshd_config'
ADD slurm.conf /etc/slurm-llnl/slurm.conf
ADD id_rsa.pub /root/.ssh/authorized_keys

RUN mkdir -p /var/log/slurm /var/run/slurmd /var/lib/slurmd && \
    chmod a+rw /var/run/slurmd /var/log/slurm /var/lib/slurmd

RUN mkdir -p /scratch/laxy

ADD sik.config /scratch/laxy/sik.config
ADD sik.yeast.config /scratch/laxy/sik.yeast.config
RUN bash -c 'echo -e "export LC_ALL=C.UTF-8\nexport LANG=C.UTF-8" > /etc/profile.d/00-set-locale.sh'

# CMD service slurmctld start && service slurmd start && tail -F /var/log/slurm/slurmctld.log
CMD /etc/init.d/ssh start && /etc/init.d/munge start && \
    /usr/sbin/slurmctld -Dvvv & /usr/sbin/slurmd -Dvvv & sleep 1 && echo "Waiting ..." && sleep 10 && \
    (scontrol update NodeName=localhost STATE=UNDRAIN || true) && tail -F /var/log/slurm/slurmd.log
