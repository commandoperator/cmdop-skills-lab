"""Tortoise ORM models for email tracking."""

from tortoise import fields
from tortoise.models import Model


class SentEmail(Model):
    id = fields.IntField(primary_key=True)
    to_addr = fields.CharField(max_length=512)
    cc_addr = fields.CharField(max_length=512, default="")
    bcc_addr = fields.CharField(max_length=512, default="")
    subject = fields.CharField(max_length=1024)
    body = fields.TextField()
    from_account = fields.CharField(max_length=256, default="default")
    action = fields.CharField(max_length=16)   # "send" | "draft"
    status = fields.CharField(max_length=16)   # "ok" | "error"
    error_message = fields.TextField(default="")
    sent_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "sent_emails"
