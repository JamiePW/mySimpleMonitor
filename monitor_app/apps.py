from django.apps import AppConfig

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings


class MonitorAppConfig(AppConfig):
    # default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor_app'

    def ready(self):
        if settings.SCHEDULER_AUTOSTART:
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                self.run_monitor_task,
                'interval',
                minutes=1,  # 每1分钟检查一次系统状态
                id='monitor_task',
                replace_existing=True
            )
            scheduler.start()
    
    def run_monitor_task(self):
        from .tasks import check_and_notify
        check_and_notify()
