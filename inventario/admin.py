from django.contrib import admin
from django.utils.html import format_html
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
    list_display = ['codigo_sku', 'imagen_preview', 'nombre', 'categoria', 'subcategoria', 'precio', 'stock', 'activo']
    list_filter = ['categoria', 'subcategoria', 'activo']
    search_fields = ['codigo_sku', 'nombre']
    readonly_fields = ['codigo_sku', 'fecha_creacion', 'fecha_modificacion', 'imagen_preview_large']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo_sku', 'nombre', 'categoria', 'subcategoria', 'descripcion')
        }),
        ('Imagen', {
            'fields': ('imagen', 'imagen_preview_large'),
            'description': 'Suba una imagen del producto (JPG o PNG recomendado)'
        }),
        ('Precios y Stock', {
            'fields': ('precio', 'stock', 'stock_minimo', 'stock_critico')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
    
    def imagen_preview(self, obj):
        """Miniatura pequeña para la lista"""
        if obj.imagen:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd;" />',
                obj.imagen.url
            )
        return format_html(
            '<img src="/static/images/no-image.png" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; opacity: 0.5;" />'
        )
    imagen_preview.short_description = 'Imagen'
    
    def imagen_preview_large(self, obj):
        """Preview grande para el formulario de edición"""
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px; border: 2px solid #ddd; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" />',
                obj.imagen.url
            )
        return format_html(
            '<div style="width: 300px; height: 200px; border: 2px dashed #ddd; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #999; background: #f5f5f5;">'
            '<div style="text-align: center;">'
            '<div style="font-size: 48px; margin-bottom: 10px;">📷</div>'
            '<div>Sin imagen</div>'
            '</div>'
            '</div>'
        )
    imagen_preview_large.short_description = 'Vista Previa'
    
@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['producto','tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'fecha_movimiento', 'usuario']
    list_filter = ['tipo', 'fecha_movimiento']
    search_fields = ['producto__codigo_sku', 'producto__nombre', 'motivo']
    readonly_fields = ['fecha_movimiento']