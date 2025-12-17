from django.urls import path
from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.ver_carrito, name='ver_carrito'),
    path('catalogo/', views.catalogo_productos, name='catalogo'),  # ← Nueva línea
    path('agregar/<int:producto_id>/', views.agregar_al_carrito, name='agregar_al_carrito'),
    path('eliminar/<int:item_id>/', views.eliminar_item, name='eliminar_item'),
    path('incrementar/<int:item_id>/', views.incrementar_item, name='incrementar_item'),
    path('disminuir/<int:item_id>/', views.disminuir_item, name='disminuir_item'),
    path('vaciar/', views.vaciar_carrito, name='vaciar_carrito'),
    path('confirmar/', views.confirmar_pedido, name='confirmar_pedido'),
]