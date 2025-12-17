from django.contrib import admin
from .models import Carrito, ItemCarrito

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'cantidad_items', 'total', 'creado', 'actualizado']
    search_fields = ['usuario__username']
    readonly_fields = ['creado', 'actualizado']
    
    def cantidad_items(self, obj):
        return obj.cantidad_items()
    cantidad_items.short_description = 'Items'
    
    def total(self, obj):
        return f"${obj.total():,.0f}"
    total.short_description = 'Total'


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    readonly_fields = ['subtotal_display']
    fields = ['producto', 'cantidad', 'subtotal_display']
    
    def subtotal_display(self, obj):
        return f"${obj.subtotal():,.0f}"
    subtotal_display.short_description = 'Subtotal'


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ['carrito', 'producto', 'cantidad', 'subtotal_display', 'agregado']
    list_filter = ['agregado']
    search_fields = ['carrito__usuario__username', 'producto__nombre']
    readonly_fields = ['agregado', 'subtotal_display']
    
    def subtotal_display(self, obj):
        return f"${obj.subtotal():,.0f}"
    subtotal_display.short_description = 'Subtotal'