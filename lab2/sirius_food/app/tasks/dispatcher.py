"""Adapter that dispatches order side effects to Celery."""
from app.core.config import settings
from app.tasks.orders import generate_order_pdf, send_order_email, send_order_sms


class CeleryOrderTaskDispatcher:
    def dispatch_order_created(
        self,
        order_id: int,
        email: str,
        phone: str,
    ) -> None:
        tasks = (
            (generate_order_pdf, (order_id,)),
            (send_order_email, (order_id, email)),
            (send_order_sms, (order_id, phone)),
        )
        for task, args in tasks:
            if settings.CELERY_TASKS_SYNC:
                task.run(*args)
            else:
                task.delay(*args)
