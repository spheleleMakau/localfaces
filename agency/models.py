import uuid

from django.db import models


class TrainingOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        PAID = "paid", "Paid"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    items = models.JSONField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payfast_payment_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return f"{name} - {self.token}" if name else str(self.token)
