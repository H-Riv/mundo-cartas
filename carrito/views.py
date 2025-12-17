from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Carrito, ItemCarrito
from inventario.models import Producto, Categoria, Subcategoria


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


def ver_carrito(request):
    """Vista principal del carrito"""
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)
    items = carrito.itemcarrito_set.select_related('producto').all()
    total = carrito.total()
    
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
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



def confirmar_pedido(request):
    """Vista temporal para confirmar pedido (sin Transbank por ahora)"""
    carrito = get_object_or_404(Carrito, usuario=request.user)
    items = carrito.itemcarrito_set.select_related('producto').all()
    
    if not items.exists():
        messages.warning(request, 'Tu carrito está vacío')
        return redirect('carrito:ver_carrito')
    
    total = carrito.total()
    
    context = {
        'carrito': carrito,
        'items': items,
        'total': total,
    }
    return render(request, 'carrito/confirmar_pedido.html', context)