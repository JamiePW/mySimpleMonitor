from django.shortcuts import render
from datetime import datetime
from utils import VsphereMonitor, PrinterMonitor
from django.http import JsonResponse
from django.conf import settings

from .models import MonitorStatus

# 配置信息 - 从 settings.py 中获取，避免硬编码，便于维护和安全
# 注意：确保在 settings.py 中定义了 VSPHERE_CONFIG, PRINTER_CONFIG_1, PRINTER_CONFIG_2
VSPHERE_CONFIG = settings.VSPHERE_CONFIG

PRINTER_CONFIG_1 = settings.PRINTER_CONFIG_1

PRINTER_CONFIG_2 = settings.PRINTER_CONFIG_2

def dashboard(request):
    # 获取服务器数据
    hosts = VsphereMonitor.get_host_status(
        VSPHERE_CONFIG["host"], 
        VSPHERE_CONFIG["user"], 
        VSPHERE_CONFIG["pwd"]
    )
    
    vms = VsphereMonitor.get_vm_status(
        VSPHERE_CONFIG["host"], 
        VSPHERE_CONFIG["user"], 
        VSPHERE_CONFIG["pwd"]
    )
    
    # 获取打印机数据
    printer1 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        PRINTER_CONFIG_1["ip"],
        PRINTER_CONFIG_1["community"]
    ).monitor()

    printer2 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        PRINTER_CONFIG_2["ip"],
        PRINTER_CONFIG_2["community"]
    ).monitor()
    
    context = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hosts": hosts,
        "vms": vms,
        "printer1": printer1,
        "printer2": printer2
    }
    return render(request, 'monitor_app/dashboard.html', context)

# 与上一个函数基本相同，但返回 JSON 数据
def dashboard_data(request):
    # 获取服务器数据
    hosts = VsphereMonitor.get_host_status(
        VSPHERE_CONFIG["host"], 
        VSPHERE_CONFIG["user"], 
        VSPHERE_CONFIG["pwd"]
    )
    
    vms = VsphereMonitor.get_vm_status(
        VSPHERE_CONFIG["host"], 
        VSPHERE_CONFIG["user"], 
        VSPHERE_CONFIG["pwd"]
    )
    
    # 获取打印机数据
    printer1 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        PRINTER_CONFIG_1["ip"],
        PRINTER_CONFIG_1["community"]
    ).monitor()

    printer2 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        PRINTER_CONFIG_2["ip"],
        PRINTER_CONFIG_2["community"]
    ).monitor()
    
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hosts": hosts,
        "vms": vms,
        "printer1": printer1,
        "printer2": printer2
    }
    
    return JsonResponse(data)

# def home(request):
#     # 获取必要数据生成摘要
#     hosts = VsphereMonitor.get_host_status(
#         VSPHERE_CONFIG["host"], 
#         VSPHERE_CONFIG["user"], 
#         VSPHERE_CONFIG["pwd"]
#     )
    
#     vms = VsphereMonitor.get_vm_status(
#         VSPHERE_CONFIG["host"], 
#         VSPHERE_CONFIG["user"], 
#         VSPHERE_CONFIG["pwd"]
#     )
    
#     printer1 = PrinterMonitor.RicohIMC3000PrinterMonitor(
#         PRINTER_CONFIG_1["ip"],
#         PRINTER_CONFIG_1["community"]
#     ).monitor()

#     printer2 = PrinterMonitor.RicohIMC3000PrinterMonitor(
#         PRINTER_CONFIG_2["ip"],
#         PRINTER_CONFIG_2["community"]
#     ).monitor()

#     # 生成状态摘要
#     status_summary = {
#         "hosts": {
#             "total": len(hosts),
#             # 如果主机关机 或 CPU 使用率超过 80% 或内存使用率超过 90%，则视为有问题
#             "issues": sum(1 for host in hosts if (
#                 host["power_state"] != "poweredOn"
#                 or float(host["cpu_usage"].strip('%')) > 80.0
#                 or float(host["memory_percent"].strip('%')) > 90.0
#             ))
#         },
#         "vms": {
#             "total": len(vms),
#             # 如果虚拟机开机 且 CPU 使用率超过 80%，则视为有问题
#             "issues": sum(1 for vm in vms if (
#                 vm["power_state"] == "poweredOn"
#                 and float(vm["cpu_usage"].strip('%')) > 80.0
#             ))
#         },
#         "printers": {
#             "total": 2,
#             # 如果打印机有错误或任何颜色墨粉低于20%，则视为有问题
#             "issues": sum(1 for p in [printer1, printer2] if "error" in p or any(int(p.get(color, "0").strip('%')) < 20 for color in ["black_toner", "cyan_toner", "magenta_toner", "yellow_toner"]))
#         }
#     }
    
#     context = {
#         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         "status_summary": status_summary
#     }
#     return render(request, 'monitor_app/home.html', context)


def home(request):
    # 从数据库获取状态摘要
    host_statuses = MonitorStatus.objects.filter(object_type='host')
    vm_statuses = MonitorStatus.objects.filter(object_type='vm')
    printer_statuses = MonitorStatus.objects.filter(object_type='printer')
    
    status_summary = {
        "hosts": {
            "total": host_statuses.count(),
            "issues": host_statuses.filter(is_normal=False).count()
        },
        "vms": {
            "total": vm_statuses.count(),
            "issues": vm_statuses.filter(is_normal=False).count()
        },
        "printers": {
            "total": printer_statuses.count(),
            "issues": printer_statuses.filter(is_normal=False).count()
        }
    }
    
    context = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status_summary": status_summary
    }
    return render(request, 'monitor_app/home.html', context)