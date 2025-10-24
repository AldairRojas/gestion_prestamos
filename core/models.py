from django.db import models

class TimestampModel(models.Model):
    """
    Un modelo base abstracto que proporciona campos de auditoría
    (fecha de creación y actualización) para otros modelos.
    """
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de actualización"
    )

    class Meta:
        # Esto es clave: le dice a Django que este modelo es "abstracto".
        # No se creará una tabla en la base de datos para TimestampModel.
        # Solo se usará para añadir sus campos a otros modelos.
        abstract = True