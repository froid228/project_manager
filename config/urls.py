from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from users.views import login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('users.urls')),
    path('api/', include('projects.urls')),
    path('api/', include('tasks.urls')),
    path('login/', login_view, name='login'),
    path('', include('core.web_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
