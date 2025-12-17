from django.contrib import admin
from .models import Rol, PerfilUsuario

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    search_fields = ['nombre']

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['user', 'rol', 'telefono', 'fecha_creacion']
    list_filter = ['rol']
    search_fields = ['user__username', 'user__email']