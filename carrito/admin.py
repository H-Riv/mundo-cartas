from django.contrib import admin
from .models import Carrito, ItemCarrito, Pedido, DetallePedido

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


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ['carrito', 'producto', 'cantidad', 'subtotal_display', 'agregado']
    list_filter = ['agregado']
    search_fields = ['carrito__usuario__username', 'producto__nombre']
    readonly_fields = ['agregado', 'subtotal_display']
    
    def subtotal_display(self, obj):
        return f"${obj.subtotal():,.0f}"
    subtotal_display.short_description = 'Subtotal'


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ['producto', 'cantidad', 'precio_unitario', 'subtotal']
    can_delete = False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero_pedido', 'usuario', 'fecha_pedido', 'total', 'estado']
    list_filter = ['estado', 'fecha_pedido']
    search_fields = ['numero_pedido', 'usuario__username']
    readonly_fields = ['numero_pedido', 'fecha_pedido', 'fecha_pago', 'subtotal', 'iva', 'total', 
                      'token_ws', 'buy_order', 'transaction_date', 'authorization_code', 'payment_type_code']
    inlines = [DetallePedidoInline]
    
    fieldsets = (
        ('Información del Pedido', {
            'fields': ('numero_pedido', 'usuario', 'fecha_pedido', 'estado')
        }),
        ('Montos', {
            'fields': ('subtotal', 'iva', 'total')
        }),
        ('Información de Transbank', {
            'fields': ('token_ws', 'buy_order', 'transaction_date', 'authorization_code', 'payment_type_code'),
            'classes': ('collapse',)
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ['pedido', 'producto', 'cantidad', 'precio_unitario', 'subtotal']
    list_filter = ['pedido__fecha_pedido']
    search_fields = ['pedido__numero_pedido', 'producto__nombre']
    readonly_fields = ['subtotal']