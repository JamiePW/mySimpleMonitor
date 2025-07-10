from easysnmp import Session

import time
from datetime import datetime

class RicohIMC3000PrinterMonitor:
    def __init__(self, ip, community='public'):
        self.session = Session(
            hostname=ip,
            community=community,
            version=2  # SNMP v2c
        )
    
    def get_metric(self, oid):
        """获取SNMP指标值"""
        try:
            result = self.session.get(oid)
            return result.value
        except Exception as e:
            print(f"Error fetching {oid}: {str(e)}")
            return "N/A"

    def check_status(self):
        """解析打印机状态码"""
        status_codes = {
            '1': '其他状态',
            '2': '未知',
            '3': '空闲',
            '4': '打印中',
            '5': '预热',
            '6': '停止打印'
        }
        status = self.get_metric('1.3.6.1.2.1.25.3.5.1.1.1')
        return status_codes.get(status, f"未知状态({status})")

    def monitor(self):
        """执行监控并返回结果"""

        metrics = {
            "status": self.check_status(),
            "total_pages": self.get_metric('1.3.6.1.2.1.43.10.2.1.4.1.1'),
            "black_toner": self.get_metric('1.3.6.1.2.1.43.11.1.1.9.1.1'),
            "cyan_toner": self.get_metric('1.3.6.1.2.1.43.11.1.1.9.1.3'),
            "magenta_toner": self.get_metric('1.3.6.1.2.1.43.11.1.1.9.1.2'),
            "yellow_toner": self.get_metric('1.3.6.1.2.1.43.11.1.1.9.1.4'),
            "paper_status": "正常" if self.get_metric('1.3.6.1.2.1.43.8.2.1.10.1.1') == '4' else "异常"
        }
        return metrics

if __name__ == "__main__":
    # 配置打印机信息
    printer_ip = "10.18.102.96"
    printer_ip = "10.17.96.1"
    community_str = "public"
    monitor = RicohIMC3000PrinterMonitor(printer_ip, community_str)

    try:
        while True:
            # 执行监控
            status_report = monitor.monitor()
            
            # 打印监控结果
            print("\n" + "="*100)
            print(f" Ricoh IMC3000 监控报告 ({printer_ip}) {datetime.now()}".center(100))
            print("="*100)
            for metric, value in status_report.items():
                print(f"{metric}: {value}")
            print("="*100)

            break
            time.sleep(5)  
    except KeyboardInterrupt:
        print("\n监控已停止")