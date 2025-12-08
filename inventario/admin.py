from django.contrib import admin
from .models import Categoria, Subcategoria, Producto, MovimientoStock

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'fecha_creacion']
    list_filter = ['activo']
    search_fields = ['nombre']
    
@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'fecha_creacion']
    list_filter = ['activo']
    search_fields = ['nombre']
    
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo_sku', 'nombre', 'categoria', 'subcategoria', 'precio', 'stock', 'activo']
    list_filter = ['categoria', 'subcategoria', 'activo']
    search_fields = ['codigo_sku', 'nombre']
    readonly_fields = ['codigo_sku', 'fecha_creacion', 'fecha_modificacion']
    
@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['producto','tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'fecha_movimiento', 'usuario']
    list_filter = ['tipo', 'fecha_movimiento']
    search_fields = ['producto__codigo_sku', 'producto__nombre', 'motivo']
    readonly_fields = ['fecha_movimiento']