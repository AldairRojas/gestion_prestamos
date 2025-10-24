from django.db import models
from core.models import TimestampModel
# Importamos Cliente desde la app clientes
from clientes.models import Cliente

class CuentaBancaria(TimestampModel):
    """
    Almacena la información bancaria de un cliente.
    """
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="cuentas_bancarias",
        verbose_name="Cliente"
    )
    banco = models.CharField(max_length=100, verbose_name="Nombre del Banco")
    numero_cuenta = models.CharField(max_length=50, unique=True, verbose_name="Número de Cuenta")
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=[('Ahorros', 'Ahorros'), ('Corriente', 'Corriente')],
        default='Ahorros',
        verbose_name="Tipo de Cuenta"
    )
    cci = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name="CCI (Código de Cuenta Interbancario)"
    )
    es_principal = models.BooleanField(
        default=True,
        verbose_name="¿Es cuenta principal?"
    )

    def __str__(self):
        # Es más seguro verificar si cliente existe antes de acceder a sus atributos
        cliente_nombre = self.cliente.nombre_completo if self.cliente else "Cliente no asignado"
        return f"{self.banco} - {self.numero_cuenta} ({cliente_nombre})"

    class Meta:
        verbose_name = "Cuenta Bancaria"
        verbose_name_plural = "Cuentas Bancarias"