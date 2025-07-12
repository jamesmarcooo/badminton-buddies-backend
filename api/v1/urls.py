from django.urls import path, include


app_name = "v1"

urlpatterns = [
    path('accounts/', include('api.v1.account.urls')),
]