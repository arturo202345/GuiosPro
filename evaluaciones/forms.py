"""Formularios del panel de administración propio."""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Dimension, Factor, Subfactor
from .roles import ADMIN, ROLES, admins_activos, asignar_rol, rol
from .services import NIVELES

NIVEL_CHOICES = [(i, f'{i} · {nombre}') for i, nombre in enumerate(NIVELES, 1)]


class DimensionForm(forms.ModelForm):
    class Meta:
        model = Dimension
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class FactorForm(forms.ModelForm):
    sugerida = forms.TypedChoiceField(
        label='Importancia sugerida (referencia de la tesis)', choices=NIVEL_CHOICES, coerce=int)

    class Meta:
        model = Factor
        fields = ['dimension', 'nombre', 'descripcion', 'sugerida', 'alcance', 'activo']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}


class SubfactorForm(forms.ModelForm):
    class Meta:
        model = Subfactor
        fields = ['factor', 'nombre', 'descripcion', 'activo']
        widgets = {'nombre': forms.Textarea(attrs={'rows': 2}), 'descripcion': forms.Textarea(attrs={'rows': 2})}


class UsuarioForm(forms.ModelForm):
    rol = forms.ChoiceField(label='Rol', choices=ROLES, initial='Evaluador')
    password1 = forms.CharField(label='Contraseña', required=False, strip=False, widget=forms.PasswordInput,
                                help_text='Al editar, déjela vacía para conservar la actual.')
    password2 = forms.CharField(label='Confirmar contraseña', required=False, strip=False,
                                widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {'username': 'Usuario', 'first_name': 'Nombres', 'last_name': 'Apellidos',
                  'email': 'Correo', 'is_active': 'Activo'}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if self.instance.pk:
            self.fields['rol'].initial = rol(self.instance)
            if self.instance.is_superuser:
                self.fields['rol'].disabled = True
                self.fields['rol'].help_text = 'Superusuario: siempre es Administrador.'

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if not self.instance.pk and not p1:
            self.add_error('password1', 'Indique una contraseña.')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(p1, self.instance)
                except ValidationError as error:
                    self.add_error('password1', error)
        if self.instance.pk:
            activo, nuevo_rol = datos.get('is_active'), datos.get('rol')
            if self.actor is not None and self.actor.pk == self.instance.pk and activo is False:
                self.add_error('is_active', 'No puede desactivar su propia cuenta.')
            era_admin = self.instance.is_active and rol(self.instance) == ADMIN
            if era_admin and (activo is False or nuevo_rol != ADMIN):
                if not admins_activos().exclude(pk=self.instance.pk).exists():
                    raise ValidationError('Debe existir al menos un administrador activo.')
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            usuario.set_password(self.cleaned_data['password1'])
        usuario.save()
        if not usuario.is_superuser:
            asignar_rol(usuario, self.cleaned_data['rol'])
        return usuario
