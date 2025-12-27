from django.db import models
from django.conf import settings
from inventario.models import Producto
from django.utils import timezone
import uuid

class Carrito(models.Model):
    """Carrito de compras para clientes registrados"""
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Carrito"
        verbose_name_plural = "Carritos"
    
    def total(self):
        """Calcula el total del carrito"""
        return sum(item.subtotal() for item in self.itemcarrito_set.all())
    
    def cantidad_items(self):
        """Cuenta total de productos en el carrito"""
        return sum(item.cantidad for item in self.itemcarrito_set.all())
    
    def __str__(self):
        return f"Carrito de {self.usuario.username}"


class ItemCarrito(models.Model):
    """Producto individual dentro del carrito"""
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    agregado = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Item de Carrito"
        verbose_name_plural = "Items de Carrito"
        unique_together = ('carrito', 'producto')
    
    def subtotal(self):
        """Calcula el subtotal del item"""
        return self.cantidad * self.producto.precio
    
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"
    
class Pedido(models.Model):
    """Pedido generado desde el carrito (compra online)"""
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Pago'),
        ('PAGADO', 'Pagado'),
        ('LISTO', 'Listo para Retiro'),
        ('ENTREGADO', 'Entregado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Identificación
    numero_pedido = models.CharField(
        max_length=50, 
        unique=True, 
        editable=False,
        verbose_name="Número de Pedido"
    )
    
    # Usuario
    usuario = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='pedidos',
        verbose_name="Cliente"
    )
    
    # Fechas
    fecha_pedido = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del Pedido")
    fecha_pago = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Pago")
    
    # Montos
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name="Subtotal"
    )
    iva = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name="IVA (19%)"
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name="Total"
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado del Pedido"
    )
    
    # Información de Transbank
    token_ws = models.CharField(max_length=100, blank=True, null=True, verbose_name="Token Webpay")
    buy_order = models.CharField(max_length=100, blank=True, null=True, verbose_name="Orden de Compra")
    transaction_date = models.DateTimeField(blank=True, null=True, verbose_name="Fecha Transacción")
    authorization_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código Autorización")
    payment_type_code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Tipo de Pago")
    
    # Observaciones
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-fecha_pedido']
    
    def __str__(self):
        return f"{self.numero_pedido} - {self.usuario.username} - ${self.total}"
    
    def save(self, *args, **kwargs):
        """Generar número de pedido autoincremental si es nuevo"""
        if not self.numero_pedido:
            # Formato: PED-YYYYMMDD-XXXX
            fecha = timezone.now().strftime('%Y%m%d')
            ultimo_pedido = Pedido.objects.filter(
                numero_pedido__startswith=f'PED-{fecha}'
            ).order_by('id').last()
            
            if ultimo_pedido and ultimo_pedido.numero_pedido:
                try:
                    ultimo_num = int(ultimo_pedido.numero_pedido.split('-')[-1])
                    nuevo_num = ultimo_num + 1
                except:
                    nuevo_num = 1
            else:
                nuevo_num = 1
            
            self.numero_pedido = f"PED-{fecha}-{nuevo_num:04d}"
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcular subtotal, IVA y total basado en los detalles"""
        from decimal import Decimal
        detalles = self.detalles.all()
        
        # Total con IVA incluido
        total_con_iva = sum(detalle.subtotal for detalle in detalles)
        
        # Calcular neto e IVA
        neto = int(total_con_iva / Decimal('1.19'))
        iva = total_con_iva - neto
        
        self.subtotal = neto
        self.iva = iva
        self.total = total_con_iva
        self.save()


class DetallePedido(models.Model):
    """Detalle del pedido (productos comprados)"""
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name="Pedido"
    )
    
    producto = models.ForeignKey(
        'inventario.Producto',
        on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    
    cantidad = models.PositiveIntegerField(
        verbose_name="Cantidad"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Precio Unitario",
        help_text="Precio al momento de la compra (IVA incluido)"
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Subtotal",
        help_text="Cantidad × Precio Unitario"
    )
    
    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedido"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.producto.nombre} × {self.cantidad} = ${self.subtotal}"
    
    def save(self, *args, **kwargs):
        """Calcular subtotal automáticamente"""
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)