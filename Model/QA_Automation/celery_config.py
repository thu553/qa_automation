from celery import Celery
import os

# Cấu hình Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
app = Celery(
    'qa_automation',
    broker=redis_url,
    backend=redis_url
)

# Cấu hình thêm
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
)

# Tự động phát hiện tasks
import tasks