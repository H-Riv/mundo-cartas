from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario

class CustomUserCreationForm(UserCreationForm):
    """Formulario de registro para nuevos usuarios (clientes)"""
    email = forms.EmailField(required=True, label="Correo electrónico")
    telefono = forms.CharField(max_length=15, required=False, label="Teléfono")
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nombre de usuario',
            'password1': 'Contraseña',
            'password2': 'Confirmar contraseña',
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Crear perfil de usuario automáticamente (rol Cliente por defecto)
            PerfilUsuario.objects.create(
                user=user,
                telefono=self.cleaned_data.get('telefono', '')
            )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Formulario de login personalizado"""
    username = forms.CharField(label="Usuario", widget=forms.TextInput(attrs={'placeholder': 'Usuario'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'}))