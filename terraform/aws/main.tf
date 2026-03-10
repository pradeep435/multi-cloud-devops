provider "aws" {
  region = "ap-south-1"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_security_group" "app_sg" {
  name        = "streamcloud-sg"
  description = "Allow app ports"

  ingress { from_port=22   to_port=22   protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  ingress { from_port=5000 to_port=5000 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  ingress { from_port=9090 to_port=9090 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  ingress { from_port=3000 to_port=3000 protocol="tcp" cidr_blocks=["0.0.0.0/0"] }
  egress  { from_port=0    to_port=0    protocol="-1"  cidr_blocks=["0.0.0.0/0"] }

  tags = { Name = "StreamCloudSG" }
}

resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  key_name               = "multicloud-key"
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker git
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ec2-user
    sleep 15

    cd /home/ec2-user
    git clone https://github.com/pradeep435/multi-cloud-devops.git
    cd multi-cloud-devops

    cat > /home/ec2-user/prometheus.yml <<PROM
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'streamcloud'
    static_configs:
      - targets: ['172.17.0.1:5000']
    metrics_path: '/metrics'
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
PROM

    docker build -t streamcloud-app .
    docker run -d --name flask-app --restart=always \
      -p 5000:5000 -e CLOUD_PROVIDER=AWS streamcloud-app

    docker run -d --name prometheus --restart=always \
      -p 9090:9090 \
      -v /home/ec2-user/prometheus.yml:/etc/prometheus/prometheus.yml \
      prom/prometheus

    docker run -d --name grafana --restart=always \
      -p 3000:3000 \
      -e GF_SECURITY_ADMIN_PASSWORD=admin \
      grafana/grafana
  EOF

  tags = {
    Name        = "StreamCloud-Primary"
    Environment = "AWS-Primary"
    Project     = "MultiCloudDevOps"
  }
}

output "public_ip"      { value = aws_instance.app_server.public_ip }
output "app_url"        { value = "http://${aws_instance.app_server.public_ip}:5000" }
output "prometheus_url" { value = "http://${aws_instance.app_server.public_ip}:9090" }
output "grafana_url"    { value = "http://${aws_instance.app_server.public_ip}:3000" }
