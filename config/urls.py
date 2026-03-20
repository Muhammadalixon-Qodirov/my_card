from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="MyCard API",
        default_version='v1',
        description="API documentation for MyCard project",
        terms_of_service="https://github.com/rozievich/mycard/README.md",
        contact=openapi.Contact(email="oybekrozievich@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/v1/accounts/', include('apps.accounts.urls')),
    path('api/v1/education/', include('apps.education.urls')),
    path('api/v1/news/', include('apps.news.urls')),

    path('swdoc/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
