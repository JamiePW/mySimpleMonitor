from django.db import models

class MonitorStatus(models.Model):
    object_type = models.CharField(max_length=20)  # 'host', 'vm', 'printer'
    object_id = models.CharField(max_length=100)   # 唯一标识符（服务器名、虚拟机名、打印机IP）
    is_normal = models.BooleanField(default=True)  # 当前是否正常
    last_status = models.BooleanField(default=True)  # 上一次检查的状态
    last_changed = models.DateTimeField(auto_now=True)  # 状态最后变化时间
    details = models.JSONField(default=dict)  # 存储详细状态信息
    
    class Meta:
        unique_together = ('object_type', 'object_id')