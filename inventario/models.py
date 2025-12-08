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
    