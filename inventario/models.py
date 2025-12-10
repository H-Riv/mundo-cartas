from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Categoria(models.Model):
    """Tipos de productos que se ingresaran, ejemplos como Decks, Fundas, Figuras, Tapetes, etc"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre de Categoria")
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['nombre']
        
    def __str__(self):
        return self.nombre
    

class Subcategoria(models.Model):
    """Subcategorias para organizar (idealmente por franquicia)
    Ejemplos: Pokemon, Digimon, Yu-Gi-Oh!, Magic the Gathering, One Piece, Dragon Ball, etc
    """
    
    nombre = models.CharField(max_length=100, verbose_name="Nombre de Subcategoria (Franquicia)")
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Subcategoria"
        verbose_name_plural = "Subcategorias"
        ordering = ['nombre']
        # Permitir que el mismo nombre sea unico
        unique_together = []

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    # Productos con ID autoincremental
    codigo_sku = models.CharField(max_length=50, unique=True, verbose_name="Codigo SKU", editable=False, help_text="Codigo autogenerado (unico), Ej: MC-0001")
    nombre = models.CharField(max_length=250, verbose_name="Nombre del Producto", help_text="Ej: Starter Deck Digimon TCG Double Typhoon")
    categoria = models.ForeignKey(Categoria,on_delete=models.PROTECT,related_name='productos', verbose_name="Categoria")
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.PROTECT, related_name='productos', verbose_name="Subcategoria (Franquicia)", null=True, blank=True)
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripcion")
    
    #Campo de imagen
    imagen = models.ImageField(
        upload_to='productos/',
        blank=True,
        null=True,
        verbose_name="Imagen del Producto",
        help_text="Imagen del producto (opcional). Formatos: JPG, PNG"
    )
    
    precio = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(Decimal('1'))], verbose_name="Precio de Venta", help_text="Precio en pesos Chilenos")
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Stock Disponible", help_text="Cantidades de unidades disponibles")
    stock_minimo = models.IntegerField(default=5, validators=[MinValueValidator(0)], verbose_name="Stock Minimo (Alerta Baja)", help_text="Cantidad que activa alerta de stock bajo")
    stock_critico = models.IntegerField(default=2, validators=[MinValueValidator(0)], verbose_name="Stock Critico (Alerta Critica)", help_text="Cantidad que activa alerta de stock critico")
    activo = models.BooleanField(default=True, verbose_name="Producto Activo")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creacion")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Ultima modificacion")
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['codigo_sku']
        
    def __str__(self):
        return f"{self.codigo_sku} - {self.nombre}"
    
    def get_estado_stock(self):
        """Retorna el estado del stock segun umbrales personalizados"""
        if self.stock <= self.stock_critico:
            return 'CRITICO'
        elif self.stock <= self.stock_minimo:
            return 'BAJO'
        else:
            return 'OK'
    
    def get_clase_css_stock(self):
        """Retorna la clase CSS segun el estado del stock"""
        estado = self.get_estado_stock()
        if estado == 'CRITICO':
            return 'stock-critical'
        elif estado == 'BAJO':
            return 'stock-low'
        else:
            return 'stock-ok'
    
    def get_imagen_url(self):
        """Retorna la URL de la imagen o una imagen por defecto"""
        if self.imagen and hasattr(self.imagen, 'url'):
            return self.imagen.url
        return '/static/images/no-image.png'  # Imagen por defecto
    
    def save(self, *args, **kwargs):
        """Generador de codigo SKU autoincremental (si el producto es nuevo)"""
        if not self.codigo_sku:
            #Obtener el ultimo producto creado
            ultimo_producto = Producto.objects.all().order_by('id').last()
            if ultimo_producto and ultimo_producto.codigo_sku:
                #Extraer el num del ultimo codigo (ej: MC-0001 -> 1)
                try:
                    ultimo_numero = int(ultimo_producto.codigo_sku.split('-')[-1])
                    nuevo_numero = ultimo_numero + 1
                except:
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
                
            #Generar el nuevo codigo con formato "MC-0001, MC-0002, etc"
            self.codigo_sku = f"MC-{nuevo_numero:04d}"
        
        super().save(*args, **kwargs)
        

#Movimientos de Stock        
class MovimientoStock(models.Model):
    TIPO_MOVIMIENTO = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
        ('AJUSTE', 'Ajuste'),
        ('VENTA', 'Venta'),
        ('ANULACION', 'Anulacion de Venta'),
    ]
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO)
    cantidad = models.IntegerField(validators=[MinValueValidator(1)], help_text="Cantidad del movimiento (siempre positiva)")
    stock_anterior = models.IntegerField(verbose_name="Stock antes del movimiento")
    stock_nuevo = models.IntegerField(verbose_name="Stock despues del movimiento")
    motivo = models.CharField(max_length=255, verbose_name="Motivo del movimiento", help_text="Ej: Ajuste, Compra a proveedor, Venta, etc")
    observaciones = models.TextField(blank=True, null=True)
    
    #Auditoria
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null='True')
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha_movimiento']
        
    def __str__(self):
        return f"{self.tipo} - {self.producto.codigo_sku} - {self.cantidad} unidades"


# Modelo de Venta / POS
class Venta(models.Model):
    """Cabecera de la venta (comprobante)"""
    ESTADO_CHOICES = [
        ('COMPLETADA', 'Completada'),
        ('ANULADA', 'Anulada'),
    ]
    
    # Folio interno autogenerado (ej: V-0001, V-0002)
    folio = models.CharField(
        max_length=50, 
        unique=True, 
        editable=False,
        verbose_name="Folio de Venta",
        help_text="Folio autogenerado, Ej: V-0001"
    )
    
    fecha_venta = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Venta")
    
    # Totales
    subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=0, 
        default=0,
        verbose_name="Subtotal (neto)"
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
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='COMPLETADA',
        verbose_name="Estado de la Venta"
    )
    
    # Información opcional del cliente
    cliente_nombre = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre del Cliente (Opcional)"
    )
    
    observaciones = models.TextField(blank=True, null=True)
    
    # Auditoría
    usuario = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Usuario que realizó la venta"
    )
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_venta']
    
    def __str__(self):
        return f"{self.folio} - ${self.total} - {self.fecha_venta.strftime('%d/%m/%Y %H:%M')}"
    
    def save(self, *args, **kwargs):
        """Generar folio autoincremental si es nueva venta"""
        if not self.folio:
            # Obtener la última venta
            ultima_venta = Venta.objects.all().order_by('id').last()
            if ultima_venta and ultima_venta.folio:
                try:
                    ultimo_numero = int(ultima_venta.folio.split('-')[-1])
                    nuevo_numero = ultimo_numero + 1
                except:
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            
            # Generar folio con formato V-0001, V-0002, etc.
            self.folio = f"V-{nuevo_numero:04d}"
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcular subtotal, IVA y total basado en los detalles"""
        from decimal import Decimal
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal for detalle in detalles)
        
        # Calcular IVA (19%)
        self.iva = int(self.subtotal * Decimal('0.19'))
        
        # Total = Subtotal + IVA
        self.total = self.subtotal + self.iva
        self.save()


class DetalleVenta(models.Model):
    """Detalle de la venta (productos vendidos)"""
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name="Venta"
    )
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    
    cantidad = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Precio Unitario",
        help_text="Precio al momento de la venta"
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name="Subtotal",
        help_text="Cantidad × Precio Unitario"
    )
    
    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.producto.nombre} × {self.cantidad} = ${self.subtotal}"
    
    def save(self, *args, **kwargs):
        """Calcular subtotal automáticamente"""
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)