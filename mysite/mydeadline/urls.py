from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib import admin
from . import views

app_name = "mydeadline"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path('add_deadline/', views.add_deadline, name='add_deadline'),
    path('my_deadlines/', views.my_deadlines, name='my_deadlines'),
    path('edit_deadline/<int:pk>/', views.edit_deadline, name='edit_deadline'),
    path('delete_deadline/<int:pk>/', views.delete_deadline, name='delete_deadline'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)