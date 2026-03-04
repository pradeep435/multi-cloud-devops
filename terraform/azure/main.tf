provider "azurerm" {
  features {}
}

# -----------------------------
# Resource Group
# -----------------------------
resource "azurerm_resource_group" "rg" {
  name     = "multi-cloud-rg"
  location = "East US"
}

# -----------------------------
# Virtual Network
# -----------------------------
resource "azurerm_virtual_network" "vnet" {
  name                = "multi-cloud-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# -----------------------------
# Subnet
# -----------------------------
resource "azurerm_subnet" "subnet" {
  name                 = "multi-cloud-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# -----------------------------
# Network Security Group
# -----------------------------
resource "azurerm_network_security_group" "nsg" {
  name                = "multi-cloud-nsg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# -----------------------------
# Allow Flask Port
# -----------------------------
resource "azurerm_network_security_rule" "flask_port" {
  name                        = "allow-flask"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "5000"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.rg.name
  network_security_group_name = azurerm_network_security_group.nsg.name
}

# -----------------------------
# Public IP
# -----------------------------
resource "azurerm_public_ip" "public_ip" {
  name                = "multi-cloud-public-ip"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Dynamic"
}

# -----------------------------
# Network Interface
# -----------------------------
resource "azurerm_network_interface" "nic" {
  name                = "multi-cloud-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.public_ip.id
  }
}

# -----------------------------
# Attach NSG to NIC
# -----------------------------
resource "azurerm_network_interface_security_group_association" "nsg_assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# -----------------------------
# Azure Virtual Machine
# -----------------------------
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "multi-cloud-azure-vm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = "Standard_B1s"
  admin_username      = "azureuser"

  network_interface_ids = [
    azurerm_network_interface.nic.id
  ]

  admin_password = "Password1234!"
  disable_password_authentication = false

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

  # -----------------------------
  # Docker + App Setup
  # -----------------------------
  custom_data = base64encode(<<EOF
#!/bin/bash

apt update -y
apt install docker.io git -y
systemctl start docker
systemctl enable docker

git clone https://github.com/pradeep435/multi-cloud-devops.git

cd multi-cloud-devops

docker build -t multi-cloud-app .

docker run -d -p 5000:5000 --restart=always multi-cloud-app

docker run -d -p 9090:9090 prom/prometheus

docker run -d -p 3000:3000 grafana/grafana

EOF
  )
}
