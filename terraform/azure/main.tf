terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "multi-cloud-rg"
  location = "East US 2"
}

resource "azurerm_virtual_network" "vnet" {
  name                = "multi-cloud-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "multi-cloud-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "multi-cloud-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Flask"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Prometheus"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "9090"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "Grafana"
    priority                   = 130
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_public_ip" "pip" {
  name                = "multi-cloud-pip"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "nic" {
  name                = "multi-cloud-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                            = "multi-cloud-azure-vm"
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = azurerm_resource_group.rg.location
  size                            = "Standard_B2s"
  admin_username                  = "azureuser"
  admin_password                  = "Password1234!"
  disable_password_authentication = false
  network_interface_ids           = [azurerm_network_interface.nic.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  custom_data = base64encode(<<-EOF
    #!/bin/bash
    set -e
    exec > /var/log/startup.log 2>&1

    echo "=== Starting StreamCloud Setup ==="

    apt-get update -y
    apt-get install -y docker.io git curl
    systemctl start docker
    systemctl enable docker

    sleep 20
    echo "=== Docker is ready ==="

    cd /home/azureuser
    git clone https://github.com/pradeep435/multi-cloud-devops.git
    cd multi-cloud-devops

    cat > /home/azureuser/prometheus.yml <<PROM
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

    echo "=== Building StreamCloud Docker image ==="
    docker build -t streamcloud-app .

    echo "=== Starting StreamCloud ==="
    docker run -d \
      --name streamcloud \
      --restart=always \
      -p 5000:5000 \
      -e CLOUD_PROVIDER=AZURE \
      streamcloud-app

    echo "=== Starting Prometheus ==="
    docker run -d \
      --name prometheus \
      --restart=always \
      -p 9090:9090 \
      -v /home/azureuser/prometheus.yml:/etc/prometheus/prometheus.yml \
      prom/prometheus

    echo "=== Starting Grafana with Prometheus auto-provisioned ==="
    mkdir -p /home/azureuser/grafana-provisioning/datasources

    cat > /home/azureuser/grafana-provisioning/datasources/prometheus.yml <<GRAFANA
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://172.17.0.1:9090
        isDefault: true
        editable: true
    GRAFANA

    docker run -d \
      --name grafana \
      --restart=always \
      -p 3000:3000 \
      -e GF_SECURITY_ADMIN_PASSWORD=admin \
      -v /home/azureuser/grafana-provisioning:/etc/grafana/provisioning \
      grafana/grafana

    sleep 30
    echo "=== All containers started ==="
    docker ps
    echo "=== StreamCloud Setup Complete! ==="
  EOF
  )

  tags = {
    Name        = "StreamCloud-Standby"
    Project     = "MultiCloudDevOps"
    Environment = "Standby"
    Cloud       = "Azure"
  }
}

output "azure_vm_public_ip" { value = azurerm_public_ip.pip.ip_address }
output "app_url"            { value = "http://${azurerm_public_ip.pip.ip_address}:5000" }
output "prometheus_url"     { value = "http://${azurerm_public_ip.pip.ip_address}:9090" }
output "grafana_url"        { value = "http://${azurerm_public_ip.pip.ip_address}:3000" }
