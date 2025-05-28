from django.db import models

# Create your models here.

class Project(models.Model):
    id = models.AutoField(primary_key=True)

    short_name = models.CharField()
    long_name = models.CharField()
    created_at = models.DateTimeField()
    description = models.CharField()
    logo_url = models.CharField()

    def __str__(self):
        return self.short_name
