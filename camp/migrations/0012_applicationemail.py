import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("camp", "0011_application_dress_size_application_kind_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicationEmail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("training_selection", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed")], default="pending", max_length=10)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="notification_email", to="camp.application")),
            ],
        ),
    ]
