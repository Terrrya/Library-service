# Generated by Django 4.1.7 on 2023-03-28 13:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("borrow", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="borrow",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payments",
                to="borrow.borrow",
            ),
        ),
    ]