# Generated by Django 5.2.1 on 2025-05-30 18:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_alter_examdate_exam_type_holiday'),
    ]

    operations = [
        migrations.AddField(
            model_name='examdate',
            name='end_date',
            field=models.DateField(blank=True, help_text='Optional: End date of the exam period', null=True),
        ),
    ]
