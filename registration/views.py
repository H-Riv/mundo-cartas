from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import PerfilUsuario
from .decorators import solo_administrador, solo_vendedor_o_admin
from inventario.models import Producto, Venta, MovimientoStock
from carrito.models import Carrito

def registro_view(request):
    """Vista de registro para nuevos clientes"""
    if request.user.is_authenticated:
        return redirect('carrito:catalogo')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'¡Cuenta creada exitosamente! Bienvenido {user.username}')
            login(request, user)
            return redirect('carrito:catalogo')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'fecha_actual': timezone.now(),
        'hora_actual': timezone.now().strftime('%H:%M:%S'),
    }
    
    return render(request, 'registration/registro.html', context)


def login_view(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        # Redirigir según el rol
        try:
            perfil = request.user.perfilusuario
            if perfil.rol.nombre in ['Administrador', 'Vendedor']:
                return redirect('inventario:lista_productos')
        except:
            pass
        return redirect('carrito:catalogo')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Crear perfil si no existe
                perfil, created = PerfilUsuario.objects.get_or_create(user=user)
                
                messages.success(request, f'¡Bienvenido {user.username}!')
                
                # Redirigir según el rol
                if perfil.rol.nombre in ['Administrador', 'Vendedor']:
                    return redirect('inventario:lista_productos')
                else:
                    return redirect('carrito:catalogo')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    else:
        form = CustomAuthenticationForm()
    
    context = {
        'form': form,
        'fecha_actual': timezone.now(),
        'hora_actual': timezone.now().strftime('%H:%M:%S'),
    }
    
    return render(request, 'registration/login.html', context)


def logout_view(request):
    """Vista de cierre de sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('carrito:catalogo')


@login_required
def perfil_view(request):
    """Vista de perfil de usuario con estadísticas según rol"""
    perfil = request.user.perfilusuario
    
    # Inicializar variables
    total_productos = 0
    total_ventas = 0
    total_ingresos = 0
    productos_stock_bajo = 0
    ventas_recientes = []
    actividad_reciente = []
    carrito_items = 0
    carrito_total = 0
    
    # Datos específicos para Vendedor y Administrador
    if perfil.rol.nombre in ['Vendedor', 'Administrador']:
        # Total de productos activos
        total_productos = Producto.objects.filter(activo=True).count()
        
        # VENDEDOR: Solo VE sus propias ventas
        # ADMIN: Ve TODAS las ventas
        if perfil.rol.nombre == 'Vendedor':
            ventas_usuario = Venta.objects.filter(
                estado='COMPLETADA',
                usuario=request.user
            )
        else:  # Administrador
            ventas_usuario = Venta.objects.filter(estado='COMPLETADA')
        
        # Total de ventas
        total_ventas = ventas_usuario.count()
        
        # Ingresos totales
        total_ingresos = ventas_usuario.aggregate(total=Sum('total'))['total'] or 0
        
        # Productos con stock bajo o crítico
        productos = Producto.objects.filter(activo=True)
        productos_stock_bajo = sum(
            1 for p in productos 
            if p.get_estado_stock() in ['BAJO', 'CRITICO']
        )
        
        # Últimas 5 ventas (del usuario o todas según rol)
        ventas_recientes = ventas_usuario.order_by('-fecha_venta')[:5]
        
        # Actividad reciente (últimos movimientos de stock del usuario)
        movimientos = MovimientoStock.objects.filter(
            usuario=request.user
        ).order_by('-fecha_movimiento')[:10]
        
        actividad_reciente = [
            {
                'fecha': mov.fecha_movimiento,
                'descripcion': f"{mov.get_tipo_display()} - {mov.producto.nombre} ({mov.cantidad} unidades)"
            }
            for mov in movimientos
        ]
    
    # Datos específicos para Cliente
    elif perfil.rol.nombre == 'Cliente':
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            carrito_items = carrito.cantidad_items()
            carrito_total = carrito.total()
        except Carrito.DoesNotExist:
            pass
        
        # Obtener pedidos del cliente para la actividad reciente
        from carrito.models import Pedido
        pedidos = Pedido.objects.filter(
            usuario=request.user
        ).prefetch_related('detalles__producto').order_by('-fecha_pedido')[:10]
        
        # Construir actividad reciente con los pedidos
        for pedido in pedidos:
            # Obtener los productos del pedido
            productos_nombres = [detalle.producto.nombre for detalle in pedido.detalles.all()[:3]]
            if pedido.detalles.count() > 3:
                productos_str = f"{', '.join(productos_nombres)} y {pedido.detalles.count() - 3} más"
            else:
                productos_str = ', '.join(productos_nombres)
            
            # Construir descripción según el estado
            if pedido.estado == 'PAGADO':
                icono = '✅'
                accion = 'Pedido pagado'
            elif pedido.estado == 'LISTO':
                icono = '📦'
                accion = 'Pedido listo para retiro'
            elif pedido.estado == 'ENTREGADO':
                icono = '🎉'
                accion = 'Pedido entregado'
            elif pedido.estado == 'CANCELADO':
                icono = '❌'
                accion = 'Pedido cancelado'
            else:  # PENDIENTE
                icono = '⏳'
                accion = 'Pedido pendiente de pago'
            
            actividad_reciente.append({
                'fecha': pedido.fecha_pedido,
                'descripcion': f"{icono} {accion}: {pedido.numero_pedido} - {productos_str} (Total: ${pedido.total:,.0f})"
            })
    
    context = {
        'perfil': perfil,
        'total_productos': total_productos,
        'total_ventas': total_ventas,
        'total_ingresos': total_ingresos,
        'productos_stock_bajo': productos_stock_bajo,
        'ventas_recientes': ventas_recientes,
        'actividad_reciente': actividad_reciente,
        'carrito_items': carrito_items,
        'carrito_total': carrito_total,
    }
    
    return render(request, 'registration/perfil_vendedor.html', context)


@login_required
def editar_perfil_view(request):
    """Vista para editar el PROPIO perfil del usuario (solo Clientes y Admin)"""
    perfil = request.user.perfilusuario
    
    # RESTRICCIÓN: Vendedores NO pueden editar su propio perfil
    if perfil.rol.nombre == 'Vendedor':
        messages.error(request, '⛔ Los vendedores no pueden editar su propio perfil. Contacte al administrador.')
        return redirect('registration:perfil')
    
    if request.method == 'POST':
        try:
            # Actualizar datos del usuario
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            
            email = request.POST.get('email', '').strip()
            if email:
                user.email = email
            else:
                messages.error(request, 'El email es obligatorio')
                return redirect('registration:editar_perfil')
            
            user.save()
            
            # Actualizar datos del perfil
            perfil.telefono = request.POST.get('telefono', '').strip()
            perfil.direccion = request.POST.get('direccion', '').strip()
            perfil.save()
            
            messages.success(request, '✓ Perfil actualizado exitosamente')
            return redirect('registration:perfil')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el perfil: {str(e)}')
            return redirect('registration:editar_perfil')
    
    context = {
        'perfil': perfil,
    }
    
    return render(request, 'registration/editar_perfil.html', context)


@solo_administrador
def lista_vendedores_view(request):
    """Vista para que el ADMIN vea y gestione todos los vendedores"""
    vendedores = PerfilUsuario.objects.filter(
        rol__nombre='Vendedor'
    ).select_related('user')
    
    # Calcular estadísticas por vendedor
    vendedores_data = []
    for vendedor_perfil in vendedores:
        ventas = Venta.objects.filter(
            usuario=vendedor_perfil.user,
            estado='COMPLETADA'
        )
        total_ventas = ventas.count()
        total_ingresos = ventas.aggregate(total=Sum('total'))['total'] or 0
        
        vendedores_data.append({
            'perfil': vendedor_perfil,
            'user': vendedor_perfil.user,
            'total_ventas': total_ventas,
            'total_ingresos': total_ingresos,
        })
    
    context = {
        'vendedores': vendedores_data,
    }
    
    return render(request, 'registration/lista_vendedores.html', context)


@solo_administrador
def editar_vendedor_view(request, user_id):
    """Vista para que el ADMIN edite el perfil de un vendedor"""
    vendedor_user = get_object_or_404(User, id=user_id)
    vendedor_perfil = vendedor_user.perfilusuario
    
    # Verificar que sea un vendedor
    if vendedor_perfil.rol.nombre != 'Vendedor':
        messages.error(request, '⛔ Este usuario no es un vendedor')
        return redirect('registration:lista_vendedores')
    
    if request.method == 'POST':
        try:
            # Actualizar datos del usuario
            vendedor_user.first_name = request.POST.get('first_name', '').strip()
            vendedor_user.last_name = request.POST.get('last_name', '').strip()
            
            email = request.POST.get('email', '').strip()
            if email:
                vendedor_user.email = email
            else:
                messages.error(request, 'El email es obligatorio')
                return redirect('registration:editar_vendedor', user_id=user_id)
            
            vendedor_user.save()
            
            # Actualizar datos del perfil
            vendedor_perfil.telefono = request.POST.get('telefono', '').strip()
            vendedor_perfil.direccion = request.POST.get('direccion', '').strip()
            vendedor_perfil.save()
            
            messages.success(request, f'✓ Perfil de {vendedor_user.username} actualizado exitosamente')
            return redirect('registration:lista_vendedores')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar el perfil: {str(e)}')
            return redirect('registration:editar_vendedor', user_id=user_id)
    
    # Calcular estadísticas del vendedor
    ventas = Venta.objects.filter(
        usuario=vendedor_user,
        estado='COMPLETADA'
    )
    total_ventas = ventas.count()
    total_ingresos = ventas.aggregate(total=Sum('total'))['total'] or 0
    
    context = {
        'vendedor_user': vendedor_user,
        'vendedor_perfil': vendedor_perfil,
        'total_ventas': total_ventas,
        'total_ingresos': total_ingresos,
    }
    
    return render(request, 'registration/editar_vendedor.html', context)