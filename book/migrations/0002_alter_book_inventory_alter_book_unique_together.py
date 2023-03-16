# Generated by Django 4.1.7 on 2023-03-15 16:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("book", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="book",
            name="inventory",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterUniqueTogether(
            name="book",
            unique_together={("title", "author", "cover")},
        ),
    ]