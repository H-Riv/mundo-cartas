from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Carrito, ItemCarrito
from inventario.models import Producto, Categoria, Subcategoria
from decimal import Decimal
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
from django.conf import settings
from .models import Pedido, DetallePedido
from inventario.models import Venta, DetalleVenta, MovimientoStock

def catalogo_productos(request):
    """Catálogo público de productos para clientes (con filtros)"""
    productos = Producto.objects.filter(activo=True, stock__gt=0).select_related('categoria', 'subcategoria')
    categorias = Categoria.objects.filter(activo=True)
    subcategorias = Subcategoria.objects.filter(activo=True)
    
    # Filtros
    categoria_filtro = request.GET.get('categoria')
    subcategoria_filtro = request.GET.get('subcategoria')
    busqueda = request.GET.get('busqueda')
    
    if categoria_filtro:
        productos = productos.filter(categoria_id=categoria_filtro)
    
    if subcategoria_filtro:
        productos = productos.filter(subcategoria_id=subcategoria_filtro)
    
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | Q(codigo_sku__icontains=busqueda)
        )
    
    # Estadísticas
    total_productos = productos.count()
    
    # Contador de carrito
    cantidad_carrito = 0
    if request.user.is_authenticated:
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            cantidad_carrito = carrito.cantidad_items()
        except Carrito.DoesNotExist:
            pass
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'total_productos': total_productos,
        'cantidad_carrito': cantidad_carrito,
    }
    
    return render(request, 'carrito/catalogo.html', context)


@login_required
def ver_carrito(request):
    """Vista principal del carrito"""
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    items = carrito.itemcarrito_set.select_related('producto').all()

    total = carrito.total()
    
    neto = int(total / Decimal('1.19'))
    iva = total - neto
    
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
        'neto': neto,
        'iva': iva,
    }
    return render(request, 'carrito/ver_carrito.html', context)



def agregar_al_carrito(request, producto_id):
    """Agregar un producto al carrito"""
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    
    # Verificar stock disponible
    if producto.stock <= 0:
        messages.error(request, f'El producto "{producto.nombre}" no tiene stock disponible')
        return redirect(request.META.get('HTTP_REFERER', 'carrito:catalogo'))
    
    # Obtener o crear el item en el carrito
    item, created = ItemCarrito.objects.get_or_create(
        carrito=carrito,
        producto=producto
    )
    
    if not created:
        # Si ya existe, verificar que no exceda el stock
        if item.cantidad >= producto.stock:
            messages.warning(request, f'No puedes agregar más unidades de "{producto.nombre}". Stock disponible: {producto.stock}')
            return redirect(request.META.get('HTTP_REFERER', 'carrito:catalogo'))
        
        item.cantidad += 1
        item.save()
        messages.success(request, f'Se agregó otra unidad de "{producto.nombre}" al carrito')
    else:
        messages.success(request, f'"{producto.nombre}" agregado al carrito')
    
    return redirect(request.META.get('HTTP_REFERER', 'carrito:catalogo'))



def eliminar_item(request, item_id):
    """Eliminar un item del carrito"""
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    nombre_producto = item.producto.nombre
    item.delete()
    messages.success(request, f'"{nombre_producto}" eliminado del carrito')
    return redirect('carrito:ver_carrito')



def incrementar_item(request, item_id):
    """Incrementar cantidad de un item"""
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    
    # Verificar stock
    if item.cantidad >= item.producto.stock:
        messages.warning(request, f'No hay más stock disponible de "{item.producto.nombre}"')
        return redirect('carrito:ver_carrito')
    
    item.cantidad += 1
    item.save()
    return redirect('carrito:ver_carrito')


@login_required
def disminuir_item(request, item_id):
    """Disminuir cantidad de un item"""
    item = get_object_or_404(ItemCarrito, id=item_id, carrito__usuario=request.user)
    
    if item.cantidad > 1:
        item.cantidad -= 1
        item.save()
    else:
        # Si llega a 0, eliminar el item
        nombre_producto = item.producto.nombre
        item.delete()
        messages.info(request, f'"{nombre_producto}" eliminado del carrito')
    
    return redirect('carrito:ver_carrito')



def vaciar_carrito(request):
    """Vaciar todo el carrito"""
    if request.method == 'POST':
        carrito = get_object_or_404(Carrito, usuario=request.user)
        carrito.itemcarrito_set.all().delete()
        messages.success(request, 'Carrito vaciado exitosamente')
    
    return redirect('carrito:ver_carrito')



@login_required
def confirmar_pedido(request):
    """Vista de confirmación antes de pagar"""
    carrito = get_object_or_404(Carrito, usuario=request.user)
    items = carrito.itemcarrito_set.select_related('producto').all()
    
    if not items.exists():
        messages.warning(request, 'Tu carrito está vacío')
        return redirect('carrito:ver_carrito')
    
    # Calcular totales
    total = carrito.total()
    from decimal import Decimal
    neto = int(total / Decimal('1.19'))
    iva = total - neto
    
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
        'neto': neto,
        'iva': iva,
    }
    return render(request, 'carrito/confirmar_pedido.html', context)

@login_required
def iniciar_pago(request):
    """Iniciar proceso de pago con Transbank"""
    carrito = get_object_or_404(Carrito, usuario=request.user)
    items = carrito.itemcarrito_set.select_related('producto').all()
    
    if not items.exists():
        messages.warning(request, 'Tu carrito está vacío')
        return redirect('carrito:ver_carrito')
    
    # Verificar stock antes de iniciar pago
    for item in items:
        if item.cantidad > item.producto.stock:
            messages.error(request, f'Stock insuficiente para {item.producto.nombre}. Disponible: {item.producto.stock}')
            return redirect('carrito:ver_carrito')
    
    try:
        # Crear pedido pendiente
        pedido = Pedido.objects.create(
            usuario=request.user,
            estado='PENDIENTE'
        )
        
        # Crear detalles del pedido
        for item in items:
            DetallePedido.objects.create(
                pedido=pedido,
                producto=item.producto,
                cantidad=item.cantidad,
                precio_unitario=item.producto.precio
            )
        
        # Calcular totales
        pedido.calcular_totales()
        
        # Configurar Transbank
        if settings.TRANSBANK_ENVIRONMENT == 'TEST':
            options = WebpayOptions(
                commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                api_key=settings.TRANSBANK_API_KEY,
                integration_type=IntegrationType.TEST
            )
        else:
            options = WebpayOptions(
                commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                api_key=settings.TRANSBANK_API_KEY,
                integration_type=IntegrationType.LIVE
            )
        
        tx = Transaction(options)
        
        # Preparar datos de la transacción
        buy_order = pedido.numero_pedido
        session_id = str(request.user.id)
        amount = int(pedido.total)
        return_url = request.build_absolute_uri('/carrito/pago/retorno/')
        
        # Crear transacción en Transbank
        response = tx.create(buy_order, session_id, amount, return_url)
        
        # Guardar token en el pedido
        pedido.token_ws = response['token']
        pedido.buy_order = buy_order
        pedido.save()
        
        # Redirigir a Webpay
        return redirect(f"{response['url']}?token_ws={response['token']}")
        
    except Exception as e:
        messages.error(request, f'Error al iniciar el pago: {str(e)}')
        return redirect('carrito:ver_carrito')


@login_required
def retorno_pago(request):
    """Procesar retorno desde Transbank"""
    token_ws = request.GET.get('token_ws')
    
    if not token_ws:
        messages.error(request, 'No se recibió confirmación de Transbank')
        return redirect('carrito:ver_carrito')
    
    try:
        # Configurar Transbank
        if settings.TRANSBANK_ENVIRONMENT == 'TEST':
            options = WebpayOptions(
                commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                api_key=settings.TRANSBANK_API_KEY,
                integration_type=IntegrationType.TEST
            )
        else:
            options = WebpayOptions(
                commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                api_key=settings.TRANSBANK_API_KEY,
                integration_type=IntegrationType.LIVE
            )
        
        tx = Transaction(options)
        response = tx.commit(token_ws)
        
        # Buscar el pedido
        pedido = get_object_or_404(Pedido, token_ws=token_ws, usuario=request.user)
        
        # Verificar si la transacción fue exitosa
        if response['status'] == 'AUTHORIZED':
            # Guardar información de la transacción
            pedido.estado = 'PAGADO'
            pedido.fecha_pago = timezone.now()
            pedido.transaction_date = response.get('transaction_date')
            pedido.authorization_code = response.get('authorization_code')
            pedido.payment_type_code = response.get('payment_type_code')
            pedido.save()
            
            # CRÍTICO: Descontar stock y crear movimientos
            detalles = pedido.detalles.select_related('producto').all()
            
            for detalle in detalles:
                producto = detalle.producto
                
                # Verificar stock disponible antes de descontar
                if producto.stock >= detalle.cantidad:
                    stock_anterior = producto.stock
                    producto.stock -= detalle.cantidad
                    producto.save()
                    
                    # Registrar movimiento de stock
                    MovimientoStock.objects.create(
                        producto=producto,
                        tipo='VENTA',
                        cantidad=detalle.cantidad,
                        stock_anterior=stock_anterior,
                        stock_nuevo=producto.stock,
                        motivo=f'Compra online - Pedido {pedido.numero_pedido}',
                        observaciones=f'Venta realizada por sitio web. Cliente: {request.user.username}',
                        usuario=None  # Sin vendedor (compra online)
                    )
                else:
                    # Si no hay stock suficiente, registrar el problema pero continuar
                    messages.warning(
                        request, 
                        f'ADVERTENCIA: Stock insuficiente para {producto.nombre}. '
                        f'Se registró la venta pero revisa el inventario.'
                    )
            
            # Crear venta en el sistema (para el historial de ventas)
            venta = Venta.objects.create(
                cliente_nombre=f"{request.user.username} (Compra Web)",
                usuario=None,  # Sin vendedor
                observaciones=f'Compra por sitio web - Pedido {pedido.numero_pedido}'
            )
            
            # Crear detalles de venta
            for detalle in detalles:
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=detalle.producto,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario
                )
            
            # Calcular totales de la venta
            venta.calcular_totales()
            
            # Vaciar el carrito
            carrito = Carrito.objects.filter(usuario=request.user).first()
            if carrito:
                carrito.itemcarrito_set.all().delete()
            
            messages.success(request, f'¡Pago exitoso! Tu pedido {pedido.numero_pedido} ha sido confirmado.')
            return redirect('carrito:pedido_exitoso', pedido_id=pedido.id)
        else:
            pedido.estado = 'CANCELADO'
            pedido.save()
            messages.error(request, 'El pago no fue autorizado. Por favor, intenta nuevamente.')
            return redirect('carrito:ver_carrito')
            
    except Exception as e:
        messages.error(request, f'Error al procesar el pago: {str(e)}')
        # Imprimir el error en consola para debugging
        import traceback
        print("ERROR EN RETORNO_PAGO:")
        print(traceback.format_exc())
        return redirect('carrito:ver_carrito')


@login_required
def pedido_exitoso(request, pedido_id):
    """Vista de confirmación de pedido exitoso"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    detalles = pedido.detalles.select_related('producto').all()
    
    context = {
        'pedido': pedido,
        'detalles': detalles,
    }
    
    return render(request, 'carrito/pedido_exitoso.html', context)


@login_required
def mis_pedidos(request):
    """Historial de pedidos del usuario"""
    pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('detalles__producto')
    
    context = {
        'pedidos': pedidos,
    }
    
    return render(request, 'carrito/mis_pedidos.html', context)


@login_required
def detalle_pedido(request, pedido_id):
    """Ver detalle de un pedido específico"""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    detalles = pedido.detalles.select_related('producto').all()
    
    context = {
        'pedido': pedido,
        'detalles': detalles,
    }
    
    return render(request, 'carrito/detalle_pedido.html', context)