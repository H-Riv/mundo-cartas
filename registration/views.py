from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import PerfilUsuario

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
    """Vista de perfil de usuario"""
    perfil = request.user.perfilusuario
    
    context = {
        'perfil': perfil,
    }
    
    return render(request, 'registration/perfil.html', context)