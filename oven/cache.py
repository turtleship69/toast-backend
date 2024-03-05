from functools import wraps


def cache(seconds):
    """
    Function decorator to set cache header in Netlify for a specified duration.

    Args:
        seconds: The number of seconds to cache the response.

    Returns:
        The decorator function.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            response.headers["Netlify-CDN-Cache-Control"] = f"public, max-age={seconds}"
            return response

        return wrapper

    return decorator
