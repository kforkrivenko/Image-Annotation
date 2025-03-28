import logging
from functools import wraps
import time


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def log_method(func):
    """Декоратор для логирования вызовов методов класса."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # args[0] — это self (экземпляр класса)
        class_name = args[0].__class__.__name__
        method_name = func.__name__

        logger.info(f"Вызов метода {class_name}.{method_name} с аргументами: args={args[1:]}, kwargs={kwargs}")

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            logger.info(
                f"Метод {class_name}.{method_name} завершился успешно. Время выполнения: {time.time() - start_time:.4f} сек.")
            return result
        except Exception as e:
            logger.error(f"Ошибка в методе {class_name}.{method_name}: {str(e)}", exc_info=True)
            raise

    return wrapper
