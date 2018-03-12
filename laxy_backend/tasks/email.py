# from __future__ import absolute_import, print_function
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from celery.utils.log import get_task_logger
from celery import shared_task
from celery import Celery, states, chain, group
from celery.exceptions import (Ignore,
                               InvalidTaskError,
                               TimeLimitExceeded,
                               SoftTimeLimitExceeded)

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True)
def send_email(self, recipients, subject, message,
               from_email=None, fail_silently=False):
    if from_email is None:
        from_email = settings.EMAIL_HOST_USER

    # import html2text
    # message = html2text.html2text(rendered_template)

    # NOTE: for more sophisticated emailing (eg retries), see:
    #       http://bameda.github.io/djmail/
    #       .. or just use Mailgun
    msg = EmailMultiAlternatives(
        subject,
        message,
        from_email,
        recipients)

    # msg.attach_alternative(
    #     rendered_template,
    #     "text/html")

    msg.send(fail_silently=fail_silently)
