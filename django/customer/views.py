import json
from django.http import HttpResponse
# from django.shortcuts import render
from rest_framework import generics, status

from .models import Project
from .serializers import ProjectSerializer

# Create your views here.
# https://dev.to/entuziaz/django-rest-framework-with-postgresql-a-crud-tutorial-1l34


class ProjectCreate(generics.CreateAPIView):
    # API endpoint that allows creation of a new project
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    # Override create to be json only:
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return HttpResponse(
            json.dumps(serializer.data),
            status=status.HTTP_201_CREATED,
            headers=headers,
            content_type='application/json'
        )

class ProjectList(generics.ListAPIView):
    # API endpoint that allows project to be viewed.
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset =  self.queryset
        short_name = self.request.query_params.get('short_name')
        if short_name is not None:
            queryset = queryset.filter(short_name__icontains=short_name.replace('*', '%'))
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        # return Response(serializer.data)
        return HttpResponse(
            json.dumps(serializer.data),
            status=status.HTTP_200_OK,
            # headers=headers,
            content_type='application/json'
        )

class ProjectDetail(generics.RetrieveAPIView):
    # API endpoint that returns a single project by pk.
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

class ProjectUpdate(generics.RetrieveUpdateAPIView):
    # API endpoint that allows a project record to be updated.
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

class ProjectDelete(generics.RetrieveDestroyAPIView):
    # API endpoint that allows a project record to be deleted.
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer