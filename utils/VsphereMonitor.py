# 使用 pyvmomi 获取主机状态
from pyVim.connect import SmartConnect
from pyVmomi import vim

def get_host_status(host, user, pwd):
    si = SmartConnect(host=host, user=user, pwd=pwd, disableSslCertValidation=True)
    content = si.RetrieveContent()

    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True
    )

    hosts_data = []
    for host in container.view:
        # 获取硬件规格
        hardware = host.summary.hardware
        # 计算总CPU容量（MHz）
        total_cpu_mhz = hardware.cpuMhz * hardware.numCpuCores
        # 计算CPU利用率百分比
        cpu_usage_percent = (host.summary.quickStats.overallCpuUsage / total_cpu_mhz) * 100

        # 计算内存使用百分比
        total_mem_mb = hardware.memorySize // (1024 * 1024)  # 字节转MB
        mem_usage_percent = (host.summary.quickStats.overallMemoryUsage / total_mem_mb) * 100

        # print(f"主机 {host.name}:")
        # print(f"  CPU使用: {cpu_usage_percent:.2f}%")
        # print(f"  内存使用量: {host.summary.quickStats.overallMemoryUsage} MB")
        # print(f"  内存使用率: {mem_usage_percent:.2f}%")
        # print(f"  电源状态: {host.runtime.powerState}")
        # print("\n")

        # 获取 GPU 信息
        # print("GPU 状态:")
        gpu_info = get_gpu_info(host)
        if not gpu_info:
            print("  未检测到 GPU 设备")
        # else:
        #     for gpu in gpu_info:
        #         print(f"  设备名称: {gpu['name']}")
        #         print(f"    设备 ID: {gpu['deviceid']}")
        #         print(f"    供应商: {gpu['vendor']}")
        #         print(f"    显存总量: {gpu['memory']} MB")
        #         print(f"    显存使用: {gpu['memory_usage']} MB" if gpu['memory_usage'] is not None else "    显存使用: 数据不可用")
        #         print(f"    温度: {gpu['temperature']}°C" if gpu['temperature'] is not None else "    温度: 数据不可用")
        # print("\n")

        host_data = {
            'host_name': host.name,
            'power_state': host.runtime.powerState,
            'cpu_usage': f"{cpu_usage_percent:.2f}%",
            'memory_percent': f"{mem_usage_percent:.2f}%",
            'memory_usage': host.summary.quickStats.overallMemoryUsage,
            'gpus': gpu_info
        }
        hosts_data.append(host_data)

    si.content.sessionManager.Logout()
    return hosts_data


# 获取虚拟机状态
def get_vm_status(host, user, pwd):
    si = SmartConnect(host=host, user=user, pwd=pwd, disableSslCertValidation=True)
    content = si.RetrieveContent()
    vms = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    
    vms_data = []
    for vm in vms.view:
        # 计算CPU使用率百分比
        cpu_usage_percent = 0.0
        if (vm.runtime.host and 
            hasattr(vm.summary.quickStats, 'overallCpuUsage') and
            vm.summary.quickStats.overallCpuUsage is not None):
            
            # 获取主机CPU频率（MHz）
            host_cpu_mhz = vm.runtime.host.hardware.cpuInfo.hz / 1000000
            
            # 获取虚拟机配置的vCPU数量
            num_vcpu = vm.config.hardware.numCPU
            
            # 计算总可用CPU资源（MHz）
            total_vcpu_mhz = num_vcpu * host_cpu_mhz
            
            # 计算使用率百分比
            if total_vcpu_mhz > 0:
                cpu_usage_percent = (vm.summary.quickStats.overallCpuUsage / total_vcpu_mhz) * 100

        # print(f"虚拟机名称： {vm.name}")
        # print(f"  所属主机: {vm.runtime.host.name}")
        # print(f"  状态: {vm.runtime.powerState}")
        # print(f"  IP地址: {vm.guest.ipAddress}")
        # print(f"  CPU使用率: {cpu_usage_percent:.2f}%")
        # 获取磁盘IO信息
        disks = []
        for disk in vm.guest.disk:
            # print(f"  磁盘（可用空间/总容量） {disk.diskPath}: {disk.freeSpace/1024**3:.1f}GB/{disk.capacity/1024**3:.1f}GB")
            disks.append({
                'path': disk.diskPath,
                'free_space': disk.freeSpace / (1024 ** 3),  # 转换为GB
                'total_space': disk.capacity / (1024 ** 3)  # 转换为GB
            })

        # 获取IP地址（处理可能为空的情况）
        ip_address = vm.guest.ipAddress if hasattr(vm.guest, 'ipAddress') else "N/A"

        vm_data = {
                'name': vm.name,
                'host': vm.runtime.host.name if vm.runtime.host else "N/A",
                'power_state': str(vm.runtime.powerState),
                'ip_address': ip_address,
                'cpu_usage': f"{cpu_usage_percent:.2f}%",
                'disks': disks
            }
        vms_data.append(vm_data)

        # print("\n")
    
    si.content.sessionManager.Logout()
    return vms_data

def get_gpu_info(host_system):
    """获取主机的 GPU 信息"""
    gpu_list = []
    
    # 获取主机硬件信息
    hardware = host_system.hardware
    
    # 遍历所有 PCI 设备
    for pci_device in hardware.pciDevice:
        # 检查是否是 GPU 设备
        if is_gpu_device(pci_device):
            gpu_data = {
                'name': pci_device.deviceName,
                'deviceid': pci_device.id,
                'vendor': get_vendor_name(pci_device.vendorId),
                'memory': None,
                'memory_usage': None,
                'temperature': None
            }
            
            # 尝试获取更详细的 GPU 信息
            try:
                # 获取 GPU 内存信息
                for device in hardware.graphicsInfo:
                    if device.pciId == pci_device.id:
                        gpu_data['memory'] = device.memorySizeInKB // 1024  # KB 转 MB
                        gpu_data['memory_usage'] = device.memoryUsageInKB // 1024 if device.memoryUsageInKB else None
                        break
                
                # 获取 GPU 温度（需要 ESXi 7.0+ 和兼容硬件）
                for sensor in hardware.sensorInfo:
                    if sensor.sensorType == 'temperature' and 'gpu' in sensor.name.lower():
                        gpu_data['temperature'] = sensor.currentReading
                        break
                        
            except Exception as e:
                print(f"    警告: 无法获取详细 GPU 数据 - {str(e)}")
            
            gpu_list.append(gpu_data)
    
    return gpu_list

def is_gpu_device(pci_device):
    """检查 PCI 设备是否是 GPU"""
    # 常见 GPU 供应商 ID
    gpu_vendors = {
        0x10DE: 'NVIDIA', 
        0x1002: 'AMD',
        0x8086: 'Intel',     # Intel Arc
        0x1DB7: 'Matrox'     # Matrox GPU
    }
    
    # 检查设备类别是否为显示控制器 (0x03)
    if pci_device.classId == '0x030000':
        return True

    # 检查已知的 GPU 供应商
    if str(hex(pci_device.vendorId)).upper() in gpu_vendors:
        return True
    
    # 检查设备名称中是否包含 GPU 关键词
    gpu_keywords = ['gpu', 'graphics', 'vga', 'nvidia', 'amd', 'radeon', 'geforce', 'quadro', 'tesla', 'grid', 'v100', 'a100', 'titan']
    if any(keyword in pci_device.deviceName.lower() for keyword in gpu_keywords):
        return True
    
    return False

def get_vendor_name(vendor_id):
    """将供应商 ID 转换为可读名称"""
    vendor_map = {
        0X10DE: 'NVIDIA',
        0X1002: 'AMD',
        0X8086: 'Intel',
        0X1DB7: 'Matrox',
        0X102B: 'Matrox',
        0X1A03: 'ASPEED'  # BMC 集成显卡
    }
    return vendor_map.get(vendor_id, f"未知供应商 ({vendor_id})")

if __name__ == "__main__":

    host = "10.18.103.12"
    user = "administrator@vsphere.local"
    pwd = "SSvv@12345"
    
    get_host_status(host, user, pwd)
    get_vm_status(host, user, pwd)