from django.urls import path
from . import views

app_name = 'registration'

urlpatterns = [
    # Login y Registro
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    
    # Perfil propio (todos los usuarios autenticados)
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    
    # Gestión de vendedores (solo Admin)
    path('vendedores/', views.lista_vendedores_view, name='lista_vendedores'),
    path('vendedores/<int:user_id>/editar/', views.editar_vendedor_view, name='editar_vendedor'),
]