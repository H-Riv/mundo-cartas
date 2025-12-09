from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Producto, Categoria, Subcategoria, MovimientoStock
#Impots para leer Excels
import pandas as pd
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

def lista_productos(request):
    """Vista principal del inventario"""
    productos = Producto.objects.filter(activo=True).select_related('categoria', 'subcategoria')
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
        productos = productos.filter(nombre__icontains=busqueda) | productos.filter(codigo_sku__icontains=busqueda)
    
    # Estadisticas
    total_productos = productos.count()
    total_unidades = sum(p.stock for p in productos)
    
    # Contar productos con stock bajo y critico
    stock_bajo = sum(1 for p in productos if p.get_estado_stock() == 'BAJO')
    stock_critico = sum(1 for p in productos if p.get_estado_stock() == 'CRITICO')
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'total_productos': total_productos,
        'total_unidades': total_unidades,
        'stock_bajo': stock_bajo,
        'stock_critico': stock_critico,
    }
 
    return render(request, 'inventario/lista_productos.html', context)

def crear_producto(request):
    """Crear nuevo producto"""
    
    if request.method == 'POST':
        try:
            producto = Producto(
                nombre=request.POST.get('nombre'),
                categoria_id=request.POST.get('categoria'),
                subcategoria_id=request.POST.get('subcategoria') if request.POST.get('subcategoria') else None,
                descripcion=request.POST.get('descripcion'),
                precio=request.POST.get('precio'),
                stock=request.POST.get('stock'),
                stock_minimo=request.POST.get('stock_minimo', 5),
                stock_critico=request.POST.get('stock_critico', 2),
            )
            
            # Manejar la imagen si fue subida
            if 'imagen' in request.FILES:
                producto.imagen = request.FILES['imagen']
            
            producto.save()
            messages.success(request, f'Producto {producto.codigo_sku} creado exitosamente!')
            return redirect('inventario:lista_productos')
        except Exception as e:
            messages.error(request, f'Error al crear producto {str(e)}')
            
        return redirect('inventario:lista_productos')
    
def editar_producto(request, pk):
    """Editar producto existente"""
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        try:
            producto.nombre = request.POST.get('nombre')
            producto.categoria_id = request.POST.get('categoria')
            producto.subcategoria_id = request.POST.get('subcategoria') if request.POST.get('subcategoria') else None
            producto.descripcion = request.POST.get('descripcion')
            producto.precio = request.POST.get('precio')
            producto.stock = request.POST.get('stock')
            producto.stock_minimo = request.POST.get('stock_minimo', 5)
            producto.stock_critico = request.POST.get('stock_critico', 2)
            
            # Manejar la imagen si fue subida
            if 'imagen' in request.FILES:
                producto.imagen = request.FILES['imagen']
            
            producto.save()
            
            messages.success(request, f'Producto {producto.codigo_sku} actualizado exitosamente')
            return redirect('inventario:lista_productos')
        except Exception as e:
            messages.error(request, f'Error al actualizar producto {str(e)}')
    return redirect('inventario:lista_productos')

def eliminar_producto(request, pk):
    """Baja logica de producto"""
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        producto.activo = False
        producto.save()
        messages.success(request, f'Producto {producto.codigo_sku} dado de baja exitosamente')
    
    return redirect('inventario:lista_productos')


def ajustar_stock(request, pk):
    """Vista para ajustar stock de un producto con historial"""
    producto = get_object_or_404(Producto, pk=pk)
    
    #Obtener historial de movimientos del producto
    movimientos = MovimientoStock.objects.filter(producto=producto).order_by('-fecha_movimiento')[:20]
    
    if request.method == 'POST':
        try:
            tipo_movimiento = request.POST.get('tipo_movimiento')
            cantidad = int(request.POST.get('cantidad'))
            motivo = request.POST.get('motivo')
            observaciones = request.POST.get('observaciones')
            
            #Validar Tipo de movimiento
            if not tipo_movimiento:
                messages.error(request, 'Debe seleccionar un tipo de movimiento')
                return redirect('inventario:ajustar_stock', pk=pk)
            
            #Validar la cantidad
            if cantidad <= 0:
                messages.error (request, 'La cantidad debe ser mayor a 0')
                return redirect('inventario:ajustar_stock', pk=pk)
            
            #Guardar stock anterior
            stock_anterior = producto.stock
            
            #Calcular nuevo stock segun el tipo de movimiento
            if tipo_movimiento == 'ENTRADA':
                producto.stock += cantidad
                
            elif tipo_movimiento == 'SALIDA':
                
                if producto.stock < cantidad:
                    messages.error(request, f'Stock insuficiente. Stock actual: {producto.stock}')
                    return redirect('inventario:ajustar_stock', pk=pk)
                producto.stock -= cantidad
                
            elif tipo_movimiento == 'AJUSTE':
                producto.stock = cantidad
                
            stock_nuevo = producto.stock
            producto.save()
            
            #Registrar producto en el historial
            MovimientoStock.objects.create(
                producto = producto,
                tipo = tipo_movimiento,
                cantidad = cantidad if tipo_movimiento != 'AJUSTE' else abs(stock_nuevo - stock_anterior),
                stock_anterior = stock_anterior,
                stock_nuevo = stock_nuevo,
                motivo = motivo,
                observaciones = observaciones,
                usuario = request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f'Stock actualizado correctamente, Nuevo Stock: {stock_nuevo}')
            return redirect('inventario:ajustar_stock', pk=pk)
        
        except Exception as e:
            messages.error(request, f'Error al ajustar stock: {str(e)}')
            return redirect('inventario:ajustar_stock', pk=pk)
        
    context = {
        'producto' : producto,
        'movimientos' : movimientos
    }
    
    return render(request, 'inventario/ajustar_stock.html', context)

def importar_productos(request):
    """Vista para importar productos desde Excel/CSV"""
    if request.method == 'GET':
        # Solo limpiar errores si viene con el parámetro 'limpiar' o si no hay errores previos
        # Esto permite que el redirect POST->GET mantenga los errores
        if request.GET.get('limpiar') == '1' or not request.session.get('errores_importacion'):
            if 'errores_importacion' in request.session:
                del request.session['errores_importacion']
                request.session.modified = True
        
        # Mostrar la página de importación
        return render(request, 'inventario/importar_productos.html')
    
    elif request.method == 'POST':
        #Procesar archivo subido
        if 'archivo' not in request.FILES:
            messages.error(request, 'No se ha seleccionado ningun archivo')
            return redirect('inventario:importar_productos')
        
        archivo = request.FILES['archivo']
        
        #Validar extension
        if not archivo.name.endswith(('.xlsx', '.xls', '.csv')):
            messages.error(request, 'Formato de archivo no valido. Use .xlsx, .xls o .csv')
            return redirect('inventario:importar_productos')
        
        try:
            #Leer archivo
            if archivo.name.endswith('.csv'):
                df = pd.read_csv(archivo)
            else:
                df = pd.read_excel(archivo)
                
            #Validar columnas requeridas
            columnas_requeridas = ['codigo_sku', 'nombre', 'categoria', 'precio']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            
            if columnas_faltantes:
                messages.error(request, f'Faltan columnas requeridas: {", ".join(columnas_faltantes)}')
                return redirect('inventario:importar_productos')
            
            #Procesar cada fila
            productos_validos = []
            productos_actualizados = 0
            errores = []
            
            for index, row in df.iterrows():
                fila_num = index + 2 #Se usa +2 porque Excel empieza en 1 y tiene header
                
                try:
                    #Validar campos requeridos
                    if pd.isna(row['codigo_sku']):
                        errores.append(f'Fila {fila_num}: Falta el código SKU del producto')
                        continue
                    
                    if pd.isna(row['nombre']):
                        errores.append(f'Fila {fila_num}: Falta el nombre del producto')
                        continue
                        
                    if pd.isna(row['precio']):
                        errores.append(f'Fila {fila_num}: Falta el precio del producto')
                        continue
                    
                    # Validar que precio sea un número válido
                    try:
                        precio = float(row['precio'])
                        if precio <= 0:
                            errores.append(f'Fila {fila_num}: El precio debe ser mayor a 0')
                            continue
                    except:
                        errores.append(f'Fila {fila_num}: El precio tiene un formato inválido')
                        continue
                    
                    # Validar categoría
                    if pd.isna(row['categoria']):
                        errores.append(f'Fila {fila_num}: Falta la categoría del producto')
                        continue
                        
                    try:
                        categoria = Categoria.objects.get(nombre=row['categoria'])
                    except Categoria.DoesNotExist:
                        errores.append(f"Fila {fila_num}: La categoría '{row['categoria']}' no existe en el sistema. Créela primero en el admin.")
                        continue
                    
                    #Buscar la subcategoria (opcional)
                    subcategoria = None
                    if not pd.isna(row.get('subcategoria')):
                        try:
                            subcategoria = Subcategoria.objects.get(nombre=row['subcategoria'])
                        
                        except Subcategoria.DoesNotExist:
                            errores.append(f"Fila {fila_num}: La subcategoría '{row['subcategoria']}' no existe en el sistema. Créela primero en el admin.")
                            continue
                    
                    # Verificar si el producto ya existe
                    producto_existente = Producto.objects.filter(codigo_sku=row['codigo_sku']).first()

                    if producto_existente:
                        # Si existe, validar que sea el MISMO producto (mismo nombre y categoría)
                        if producto_existente.nombre.lower() != str(row['nombre']).lower():
                            errores.append(f"Fila {fila_num}: El código SKU '{row['codigo_sku']}' ya existe con un producto diferente ('{producto_existente.nombre}'). No se puede usar el mismo SKU para productos distintos.")
                            continue
                        
                        if producto_existente.categoria != categoria:
                            errores.append(f"Fila {fila_num}: El código SKU '{row['codigo_sku']}' existe pero con categoría diferente. SKU registrado: '{producto_existente.categoria.nombre}', Excel: '{categoria.nombre}'")
                            continue
                        
                        # Si subcategoría existe en ambos, validar que coincidan
                        if producto_existente.subcategoria and subcategoria:
                            if producto_existente.subcategoria != subcategoria:
                                errores.append(f"Fila {fila_num}: El código SKU '{row['codigo_sku']}' existe pero con subcategoría diferente. SKU registrado: '{producto_existente.subcategoria.nombre}', Excel: '{subcategoria.nombre}'")
                                continue
                        
                        # Si todo coincide, SUMAR el stock en lugar de crear uno nuevo
                        stock_a_sumar = int(row.get('stock', 0)) if not pd.isna(row.get('stock')) else 0
                        
                        if stock_a_sumar > 0:
                            stock_anterior = producto_existente.stock
                            producto_existente.stock += stock_a_sumar
                            producto_existente.save()
                            
                            # Registrar el movimiento en el historial
                            MovimientoStock.objects.create(
                                producto=producto_existente,
                                tipo='ENTRADA',
                                cantidad=stock_a_sumar,
                                stock_anterior=stock_anterior,
                                stock_nuevo=producto_existente.stock,
                                motivo=f'Importación masiva desde Excel',
                                observaciones=f'Importado desde archivo Excel - Fila {fila_num}',
                                usuario=request.user if request.user.is_authenticated else None
                            )
                            
                            productos_actualizados += 1
                        
                        # No agregamos a productos_validos porque ya se guardó directamente
                        continue
                    
                    #Crear producto (en memoria, temporalmente)
                    producto = Producto(
                        codigo_sku=str(row['codigo_sku']),
                        nombre=str(row['nombre']),
                        categoria=categoria,
                        subcategoria=subcategoria,
                        descripcion=str(row.get('descripcion', '')) if not pd.isna(row.get('descripcion')) else '',
                        precio=precio,
                        stock=int(row.get('stock', 0)) if not pd.isna(row.get('stock')) else 0,
                        stock_minimo=int(row.get('stock_minimo', 5)) if not pd.isna(row.get('stock_minimo')) else 5,
                        stock_critico=int(row.get('stock_critico', 2)) if not pd.isna(row.get('stock_critico')) else 2,
                    )
                    
                    productos_validos.append(producto)
                    
                except Exception as e:
                    # Error genérico más amigable
                    errores.append(f"Fila {fila_num}: Error de formato en los datos. Revise que todas las columnas tengan el formato correcto.")
            
            #Guardar productos válidos (nuevos)
            productos_nuevos = 0
            if productos_validos:
                Producto.objects.bulk_create(productos_validos)
                productos_nuevos = len(productos_validos)

            # Mensaje de éxito con detalles
            if productos_nuevos > 0 and productos_actualizados > 0:
                messages.success(request, f'✓ Se importaron {productos_nuevos} productos nuevos y se actualizó el stock de {productos_actualizados} productos existentes')
            elif productos_nuevos > 0:
                messages.success(request, f'✓ Se importaron {productos_nuevos} productos nuevos exitosamente')
            elif productos_actualizados > 0:
                messages.success(request, f'✓ Se actualizó el stock de {productos_actualizados} productos existentes')
            
            # Guardar errores en sesion para mostrarlos
            if errores:
                request.session['errores_importacion'] = errores[:20]
                request.session.modified = True
            else:
                # Si no hay errores, limpiar cualquier error previo
                if 'errores_importacion' in request.session:
                    del request.session['errores_importacion']
                    request.session.modified = True
            
            return redirect('inventario:importar_productos')
        
        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {str(e)}')
            return redirect('inventario:importar_productos')
        
def descargar_plantilla(request):
    """Generar y descargar plantilla Excel para importacion"""
    #Crear un nuevo libro Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Plantilla Productos"
    
    #Definir encabezados
    headers = ['codigo_sku', 'nombre', 'categoria', 'subcategoria', 'descripcion', 'precio', 'stock', 'stock_minimo', 'stock_critico']
    
    #Estilo para encabezados
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    #Escribir encabezados
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.fill = header_fill
        cell.font = header_font
        
    #Agregar ejemplos
    ejemplos = [
        ['MC-0001', 'Starter Deck Digimon TCG', 'Decks', 'Digimon', 'Deck de inicio', 15990, 10, 5, 2],
        ['MC-0002', 'Sobre Pokemon Escarlata', 'Sobres', 'Pokemon', 'Sobre de expansión', 4500, 50, 10, 3],
        ['MC-0003', 'Figura Luffy Gear 5', 'Figuras', 'One Piece', 'Figura coleccionable', 45990, 5, 2, 1],
    ]
    
    for row_num, ejemplo in enumerate(ejemplos, 2):
        for col_num, value in enumerate(ejemplo, 1):
            ws.cell(row=row_num, column=col_num, value=value)
            
    #Ajustar ancho de las columnas
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 30
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 15
    
    #Preparar respuesta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_productos.xlsx'
    
    wb.save(response)
    return response