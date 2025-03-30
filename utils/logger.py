import logging
from functools import wraps
import time


def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def log_method(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = setup_logger()
        class_name = args[0].__class__.__name__
        method_name = func.__name__

        logger.info(f"Calling {class_name}.{method_name}")

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            logger.info(
                f"Method {class_name}.{method_name} completed in "
                f"{time.time() - start_time:.4f} sec."
            )
            return result
        except Exception as e:
            logger.error(f"Error in {class_name}.{method_name}: {str(e)}")
            raise

    return wrapper
