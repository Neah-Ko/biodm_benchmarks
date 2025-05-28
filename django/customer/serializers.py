from rest_framework import serializers
from .models import Project



class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project 
        fields = ['id', 'short_name', 'long_name', 'created_at', 'description', 'logo_url']
