from django.urls import include, path
from .views import (
    ProjectCreate,
    ProjectList,
    ProjectDetail,
    ProjectUpdate,
    ProjectDelete
)


urlpatterns = [
    path('create/', ProjectCreate.as_view(), name='create-project'),
    path('', ProjectList.as_view()),
    path('<int:pk>/', ProjectDetail.as_view(), name='retrieve-project'),
    path('update/<int:pk>/', ProjectUpdate.as_view(), name='update-project'),
    path('delete/<int:pk>/', ProjectDelete.as_view(), name='delete-project')
]
