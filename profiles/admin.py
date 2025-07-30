from django.contrib import admin

# Register your models here.
from .models import CustomUser, Company, Profile

admin.site.register(CustomUser)
admin.site.register(Company)
admin.site.register(Profile)
# admin.site.register(Skill)  
# admin.site.register(Project)