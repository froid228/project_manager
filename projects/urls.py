from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
router = DefaultRouter()
router.register(r'projects', views.ProjectViewSet, basename='project')
urlpatterns = [
    path('', include(router.urls)),
    path('projects/<int:project_pk>/members/', views.ProjectMemberViewSet.as_view({'get':'list','post':'create'}), name='project-members'),
    path('projects/<int:project_pk>/members/<int:pk>/', views.ProjectMemberViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update','delete':'destroy'})),
]
