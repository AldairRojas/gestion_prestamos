"""
Configuración para PRODUCCIÓN del sistema de gestión de préstamos.

"""

from .settings import *

# ===========================================
# CONFIGURACIÓN DE PRODUCCIÓN
# ===========================================

# SEGURIDAD CRÍTICA
DEBUG = False  # NUNCA True en producción
SECRET_KEY = 'TU_CLAVE_SECRETA_SUPER_SEGURA_AQUI'  # Cambiar por una clave segura

# Dominios permitidos (agregar tu dominio real)
ALLOWED_HOSTS = [
    'tu-dominio.com',
    'www.tu-dominio.com',
    'api.tu-dominio.com',
]

# ===========================================
# BASE DE DATOS DE PRODUCCIÓN
# ===========================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db_prestamos_prod',
        'USER': 'usuario_prod',
        'PASSWORD': 'password_super_seguro',
        'HOST': 'localhost',  # O tu servidor de BD
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',  # Para conexiones seguras
        }
    }
}

# ===========================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ===========================================

# Archivos estáticos (CSS, JS, imágenes)
STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/prestamos/static/'  # Ruta donde se recopilarán los archivos estáticos

# Archivos subidos por usuarios
MEDIA_URL = '/media/'
MEDIA_ROOT = '/var/www/prestamos/media/'

# ===========================================
# SEGURIDAD ADICIONAL
# ===========================================

# HTTPS en producción
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguras
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ===========================================
# LOGGING PARA PRODUCCIÓN
# ===========================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/prestamos.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# ===========================================
# EMAIL PARA PRODUCCIÓN
# ===========================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.tu-servidor.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'noreply@tu-dominio.com'
EMAIL_HOST_PASSWORD = 'tu_password_email'

# ===========================================
# CACHE PARA PRODUCCIÓN
# ===========================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# ===========================================
# CONFIGURACIONES ADICIONALES
# ===========================================

# Tiempo de sesión
SESSION_COOKIE_AGE = 3600  # 1 hora

# Límites de archivos
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB