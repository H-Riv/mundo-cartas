from django.db import models
from django.contrib.auth.models import User

class Rol(models.Model):
    """Roles del sistema: Administrador, Vendedor, Cliente"""
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
    
    def __str__(self):
        return self.nombre


def rol_default():
    """Rol por defecto para nuevos usuarios: Cliente"""
    rol, created = Rol.objects.get_or_create(
        nombre="Cliente",
        defaults={'descripcion': 'Usuario cliente con acceso al carrito de compras'}
    )
    return rol.id


class PerfilUsuario(models.Model):
    """Perfil extendido de usuario con rol asignado"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.RESTRICT, default=rol_default)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.user.username} ({self.rol.nombre})"