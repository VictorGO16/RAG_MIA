from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    def save(self, *args, **kwargs):
        # Convert the username to lowercase before saving
        self.username = self.username.lower()
        super().save(*args, **kwargs)


class Company(models.Model):
    COMPANIES_CHOICES = [
        ('500_GLOBAL', '500 GLOBAL'),
    ]
    name = models.CharField(
        max_length=50,
        choices=COMPANIES_CHOICES,
        default='500_GLOBAL'
    )

    def __str__(self):
        return self.name


# class Skill(models.Model):
#     name = models.CharField(max_length=50)

#     def __str__(self):
#         return self.name


# class Project(models.Model):
#     name = models.CharField(max_length=100)
#     description = models.TextField()
#     link = models.URLField()

#     def __str__(self):
#         return self.name


class Profile(models.Model):
    PROFILE_TYPE = [
        ('USER', 'user'),
        ('CLIENT', 'client'),
    ]
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
    )
    profile_type = models.CharField(
        max_length=10,
        choices=PROFILE_TYPE,
        default='USER',
        null=True,
    )
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=100)
    about = models.TextField()
    experience = models.TextField()
    education = models.TextField()
    hobbies = models.TextField()
    languages = models.TextField()
    linkedin = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.user.username
