"""
### memoize_utils.py - 高级记忆化装饰器工具集

#### 提供功能强大的缓存装饰器
"""

import functools

def memorize(func):
    """
    功能强大的缓存装饰器。
    """
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)

        if key not in cache:
            cache[key] = func(*args, **kwargs)

        return cache[key]
    
    return wrapper