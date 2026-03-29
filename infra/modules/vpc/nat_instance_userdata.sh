#!/bin/bash
set -e

# Log all output
exec > >(tee -a /var/log/nat-setup.log)
exec 2>&1

echo "Starting NAT instance configuration at $(date)"

# Update system
echo "Updating system packages..."
yum update -y

# Enable IP forwarding permanently
echo "Enabling IP forwarding..."
echo 'net.ipv4.ip_forward = 1' | tee /etc/sysctl.d/99-ip-forward.conf
sysctl -w net.ipv4.ip_forward=1

# Install iptables-services
echo "Installing iptables-services..."
yum install -y iptables-services
systemctl enable iptables
systemctl start iptables

# Clear existing rules
echo "Clearing existing iptables rules..."
iptables -F
iptables -t nat -F
iptables -X

# Set default policies
iptables -P FORWARD DROP
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT

# Configure NAT - Allow traffic from VPC CIDR
# shellcheck disable=SC2154
echo "Configuring NAT rules for VPC CIDR: ${vpc_cidr}"
iptables -t nat -A POSTROUTING -o ens5 -s "${vpc_cidr}" -j MASQUERADE

# Allow established connections back
iptables -A FORWARD -i ens5 -o ens5 -m state --state RELATED,ESTABLISHED -j ACCEPT

# Allow outbound from VPC
iptables -A FORWARD -s "${vpc_cidr}" -o ens5 -j ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Save iptables rules
echo "Saving iptables rules..."
service iptables save

# Verify configuration
echo "Verifying configuration..."
echo "IP forwarding status: $(sysctl net.ipv4.ip_forward)"
echo "NAT rules:"
iptables -t nat -L -v -n
echo "Filter rules:"
iptables -L -v -n

echo "NAT instance configured successfully at $(date)"
