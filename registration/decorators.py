from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps

def rol_requerido(*roles_permitidos):
    """
    Decorador para verificar que el usuario tenga uno de los roles permitidos.
    Uso: @rol_requerido('Administrador', 'Vendedor')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            try:
                perfil = request.user.perfilusuario
                if perfil.rol.nombre in roles_permitidos:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f'⛔ No tienes permisos para acceder a esta sección. Rol requerido: {", ".join(roles_permitidos)}')
                    # Redirigir según el rol del usuario
                    if perfil.rol.nombre == 'Cliente':
                        return redirect('carrito:catalogo')
                    else:
                        return redirect('inventario:lista_productos')
            except:
                messages.error(request, '⛔ Debes tener un perfil válido para acceder')
                return redirect('carrito:catalogo')
        return wrapper
    return decorator


def solo_administrador(view_func):
    """
    Decorador que solo permite acceso a administradores.
    Uso: @solo_administrador
    """
    return rol_requerido('Administrador')(view_func)


def solo_vendedor_o_admin(view_func):
    """
    Decorador que permite acceso a vendedores y administradores.
    Uso: @solo_vendedor_o_admin
    """
    return rol_requerido('Administrador', 'Vendedor')(view_func)


def solo_cliente(view_func):
    """
    Decorador que solo permite acceso a clientes.
    Uso: @solo_cliente
    """
    return rol_requerido('Cliente')(view_func)