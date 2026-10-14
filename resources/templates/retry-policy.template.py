"""
Plantilla: Política de Reintentos con Backoff Exponencial y Jitter
Clasifica errores transitorios vs fatales y calcula el tiempo de espera.
"""

import random
from typing import Type

# Excepciones consideradas transitorias (aptas para reintento)
TRANSIENT_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

# Excepciones fatales (datos corruptos, errores de negocio; NO deben reintentarse)
FATAL_EXCEPTIONS = (
    ValueError,
    KeyError,
    TypeError,
)

class RetryPolicy:
    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 300.0,
        max_attempts: int = 3,
        jitter: float = 1.0
    ) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter = jitter

    def is_retryable(self, exception: Exception, current_attempt: int) -> bool:
        """
        Determina si una excepción debe reintentarse o enviarse directamente a fallo.
        """
        if current_attempt >= self.max_attempts:
            return False

        if isinstance(exception, FATAL_EXCEPTIONS):
            return False

        if isinstance(exception, TRANSIENT_EXCEPTIONS):
            return True

        # Por defecto, errores desconocidos se reintentan hasta agotar el límite
        return True

    def calculate_delay(self, attempt: int) -> int:
        """
        Calcula el retraso en segundos usando backoff exponencial con jitter:
        delay = min(max_delay, base_delay * (2 ** attempt)) + random_jitter
        """
        exponential = self.base_delay * (2 ** max(0, attempt - 1))
        capped = min(self.max_delay, exponential)
        jitter_value = random.uniform(0, self.jitter)

        return int(round(capped + jitter_value))

# Instancia estándar para uso en workers
default_retry_policy = RetryPolicy()
