FROM ubuntu:trusty

# Install packages
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get -y install supervisor git python openvpn iptables
# Add image configuration and scripts

ADD supervisord/supervisord-openvpn.conf /etc/supervisor/conf.d/supervisord-openvpn.conf
ADD VPN /VPN
ADD auth.txt /auth.txt
ADD scripts/start_vpn.sh /start_vpn.sh
RUN chmod 775 /start_vpn.sh

ADD scripts/proxy.py /proxy.py
ADD supervisord/supervisord-proxy.conf /etc/supervisor/conf.d/supervisord-proxy.conf

EXPOSE 8080
CMD ["supervisord","-n"]
