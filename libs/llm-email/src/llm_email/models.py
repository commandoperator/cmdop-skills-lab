"""Tortoise ORM models for email tracking."""

from tortoise import fields
from tortoise.models import Model

from llm_email.types import EmailAction, EmailStatus, BounceType, ReplyType


class SentEmail(Model):
    id = fields.IntField(primary_key=True)
    to_addr = fields.CharField(max_length=512)
    cc_addr = fields.CharField(max_length=512, default="")
    bcc_addr = fields.CharField(max_length=512, default="")
    subject = fields.CharField(max_length=1024)
    body = fields.TextField()
    from_account = fields.CharField(max_length=256, default="default")
    action = fields.CharEnumField(EmailAction)
    status = fields.CharEnumField(EmailStatus)
    error_message = fields.TextField(default="")
    sent_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "sent_emails"


class BounceEmail(Model):
    id = fields.IntField(primary_key=True)
    email = fields.CharField(max_length=512)
    bounce_type = fields.CharEnumField(BounceType)
    reason = fields.CharField(max_length=512, default="")
    source_subject = fields.CharField(max_length=512, default="")
    detected_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "bounce_emails"


class EmailReply(Model):
    id = fields.IntField(primary_key=True)
    from_email = fields.CharField(max_length=512)
    from_name = fields.CharField(max_length=512, default="")
    to_account = fields.CharField(max_length=512, default="")
    subject = fields.CharField(max_length=1024, default="")
    body = fields.TextField(default="")
    reply_type = fields.CharEnumField(ReplyType)
    summary = fields.CharField(max_length=512, default="")
    redirect_email = fields.CharField(max_length=512, default="")
    handled = fields.BooleanField(default=False)
    detected_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "email_replies"
