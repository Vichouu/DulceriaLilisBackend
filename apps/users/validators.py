from django.core.exceptions import ValidationError
import re

class ComplexPasswordValidator:
    """
    Valida que la contraseña contenga al menos una mayúscula y un número.
    """
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe contener al menos una letra mayúscula.", code='password_no_upper')
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe contener al menos un número.", code='password_no_number')

    def get_help_text(self):
        return "Su contraseña debe contener al menos una letra mayúscula y un número."