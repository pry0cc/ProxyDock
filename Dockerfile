FROM alpine

# Install packages
RUN apk add --no-cache supervisor python openvpn

# Add image configuration and scripts
ADD supervisord/* /etc/supervisor.d/
ADD VPN /VPN
ADD auth.txt /

ADD scripts/* /
RUN chmod 775 /start_vpn.sh
EXPOSE 1080
CMD ["supervisord","-n"]
