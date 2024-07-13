# models.py

from django.db import models

class Deadline(models.Model):
    your_name = models.TextField()
    your_email = models.TextField()
    role = models.IntegerField(null=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    file = models.FileField(upload_to='deadlines/', blank=True, null=True)
    group = models.TextField()
    assigned_emails = models.TextField()

    def __str__(self):
        return self.title