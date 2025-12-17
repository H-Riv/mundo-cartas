from django.db import models
from django.conf import settings
from inventario.models import Producto

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