# monitor_app/tasks.py
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import MonitorStatus
from utils import VsphereMonitor, PrinterMonitor
from datetime import timedelta
from datetime import datetime

logger = logging.getLogger(__name__)

def check_and_notify():
    print("后台监控任务正在运行……")

    """检查所有监控对象的状态并发送通知"""
    # 检查物理服务器
    check_hosts()
    
    # 检查虚拟机
    check_vms()
    
    # 检查打印机
    check_printers()

def check_hosts():
    """检查物理服务器状态"""
    hosts = VsphereMonitor.get_host_status(
        settings.VSPHERE_CONFIG["host"], 
        settings.VSPHERE_CONFIG["user"], 
        settings.VSPHERE_CONFIG["pwd"]
    )
    
    for host in hosts:
        # 检查是否异常
        is_normal = True
        issues = []
        
        if host["power_state"] != "poweredOn":
            is_normal = False
            issues.append(f"电源状态异常: {host['power_state']}")
        
        try:
            cpu_usage = float(host["cpu_usage"].rstrip('%'))
            if cpu_usage > 80:
                is_normal = False
                issues.append(f"CPU使用率过高: {cpu_usage}%")
        except (ValueError, TypeError):
            pass
        
        try:
            mem_percent = float(host["memory_percent"].rstrip('%'))
            if mem_percent > 90:
                is_normal = False
                issues.append(f"内存使用率过高: {mem_percent}%")
        except (ValueError, TypeError):
            pass
        
        # 更新或创建状态记录
        update_status(
            object_type='host',
            object_id=host['host_name'],
            is_normal=is_normal,
            details={
                'name': host['host_name'],
                'power_state': host['power_state'],
                'cpu_usage': host['cpu_usage'],
                'memory_usage': host['memory_usage'],
                'memory_percent': host['memory_percent'],
                'issues': issues
            }
        )

def check_vms():
    """检查虚拟机状态"""
    vms = VsphereMonitor.get_vm_status(
        settings.VSPHERE_CONFIG["host"], 
        settings.VSPHERE_CONFIG["user"], 
        settings.VSPHERE_CONFIG["pwd"]
    )
    
    for vm in vms:
        # 检查是否异常
        is_normal = True
        issues = []
        
        # 只检查开机状态的虚拟机
        if vm["power_state"] == "poweredOn":
            try:
                cpu_usage = float(vm["cpu_usage"].rstrip('%'))
                if cpu_usage > 80:
                    is_normal = False
                    issues.append(f"CPU使用率过高: {cpu_usage}%")
            except (ValueError, TypeError):
                pass
        
        # 更新或创建状态记录
        update_status(
            object_type='vm',
            object_id=vm['name'],
            is_normal=is_normal,
            details={
                'name': vm['name'],
                'host': vm['host'],
                'power_state': vm['power_state'],
                'ip_address': vm['ip_address'],
                'cpu_usage': vm['cpu_usage'],
                'disks': vm.get('disks', []),
                'issues': issues
            }
        )

def check_printers():
    """检查打印机状态"""
    printer1 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        settings.PRINTER_CONFIG_1["ip"],
        settings.PRINTER_CONFIG_1["community"]
    ).monitor()

    printer2 = PrinterMonitor.RicohIMC3000PrinterMonitor(
        settings.PRINTER_CONFIG_2["ip"],
        settings.PRINTER_CONFIG_2["community"]
    ).monitor()
    
    for printer, config in [(printer1, settings.PRINTER_CONFIG_1), 
                           (printer2, settings.PRINTER_CONFIG_2)]:
        # 检查是否异常
        is_normal = True
        issues = []
        
        if "error" in printer:
            is_normal = False
            issues.append(f"错误: {printer['error']}")
        else:
            for color in ["black_toner", "cyan_toner", "magenta_toner", "yellow_toner"]:
                try:
                    toner_level = int(printer.get(color, "0").strip('%'))
                    # print(f"打印机{config['ip']}的{color}墨粉水平值为{toner_level}%")
                    if toner_level < 20:
                        is_normal = False
                        issues.append(f"{color.replace('_', ' ').title()}不足: {toner_level}%")
                except (ValueError, TypeError):
                    pass
        
        # 更新或创建状态记录
        update_status(
            object_type='printer',
            object_id=config["ip"],
            is_normal=is_normal,
            details={
                'ip': config["ip"],
                'status': printer.get('status', '未知'),
                'total_pages': printer.get('total_pages', '未知'),
                'black_toner': printer.get('black_toner', '未知'),
                'cyan_toner': printer.get('cyan_toner', '未知'),
                'magenta_toner': printer.get('magenta_toner', '未知'),
                'yellow_toner': printer.get('yellow_toner', '未知'),
                'issues': issues
            }
        )

def update_status(object_type, object_id, is_normal, details):
    """更新监控状态并发送通知"""
    try:
        # 获取或创建状态记录
        status, created = MonitorStatus.objects.get_or_create(
            object_type=object_type,
            object_id=object_id,
            defaults={
                'is_normal': is_normal,
                'last_status': is_normal,
                'details': details
            }
        )
        
        if not created:
            # 检查状态是否变化
            if status.is_normal != is_normal:
                status_changed = True
            else:
                status_changed = False

            # 更新状态
            status.last_status = status.is_normal
            status.is_normal = is_normal
            status.details = details
            
            # 如果状态变化，更新时间戳
            if status_changed:
                status.last_changed = timezone.now()
            
            status.save()
            
            # 发送通知（如果是状态变化）
            if status_changed:
                print(f"已经检测到关于{object_type} {object_id}的状态变化，正在发送邮件...")
                send_notification(object_type, object_id, is_normal, details)
    except Exception as e:
        logger.error(f"更新监控状态失败: {object_type}/{object_id} - {str(e)}")

def send_notification(object_type, object_id, is_normal, details):
    """发送状态变化通知邮件"""
    try:
        # 构建邮件主题和内容
        status_text = "恢复正常" if is_normal else "出现异常"
        subject = f"[监控系统] {object_type} {object_id} {status_text}"
        
        message = f"{object_type.upper()} 状态变化通知\n\n"
        message += f"对象: {object_id}\n"
        message += f"状态: {status_text}\n"
        message += f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 添加详细信息
        if details.get('name'):
            message += f"名称: {details['name']}\n"
        
        if details.get('issues'):
            message += "问题详情:\n"
            for issue in details['issues']:
                message += f"  - {issue}\n"
        else:
            message += "所有指标正常\n"
        
        # 发送邮件
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            settings.ALERT_RECIPIENTS,
            fail_silently=False,
        )
        
        logger.info(f"已发送通知: {subject}")
    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")