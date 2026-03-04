provider "aws" {
  region = "ap-south-1"
}

# Get latest Amazon Linux 2 AMI automatically
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_security_group" "app_sg" {
  name        = "multi-cloud-app-sg"
  description = "Allow SSH and Flask App Port"

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "MultiCloudSecurityGroup"
  }
}

resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"

  # 🔐 Attach key pair
  key_name = "multicloud-key"

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install docker git -y

              systemctl enable docker
              systemctl start docker

              # wait for docker to fully initialize
              sleep 30

              cd /home/ec2-user
              git clone https://github.com/pradeep435/multi-cloud-devops.git
              cd multi-cloud-devops

              docker build -t multi-cloud-app .
              docker run -d -p 5000:5000 multi-cloud-app
              EOF

  tags = {
    Name = "MultiCloudPrimary"
  }
}

output "public_ip" {
  value = aws_instance.app_server.public_ip
}