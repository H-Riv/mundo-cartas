from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.lista_productos, name='lista_productos'),
    path('crear/', views.crear_producto, name='crear_producto'),
    path('editar/<int:pk>/', views.editar_producto, name='editar_producto'),
    path('eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('ajustar-stock/<int:pk>/', views.ajustar_stock, name='ajustar_stock'),
    path('importar/', views.importar_productos, name='importar_productos'),
    path('descargar-plantilla/', views.descargar_plantilla, name='descargar_plantilla'),
]
