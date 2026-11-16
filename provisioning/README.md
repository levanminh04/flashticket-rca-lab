# provisioning (chưa làm)

Script dựng một máy trống: cài Docker, chrony, tạo thư mục `/opt/rca-lab`, `/etc/rca-lab`, `/srv/rca-lab`.
Phần riêng của từng cloud (tường lửa, iptables trên Oracle, Security Group trên AWS) đặt ở `cloud/oracle/`,
`cloud/aws/`.
