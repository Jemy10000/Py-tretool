"""
### 标记函数，并在调用时发出提示。
##### 例:
    ```
    @wrapper.deprecated_func(version='1.2.1', alternative='main')
    def slow():
        print('slow func')
"""

import functools
import warnings
import inspect
import time

from typing import Optional, Callable, Any


def info(func: Optional[Callable] = None, *, 
         show_args: bool = True,
         show_kwargs: bool = True,
         show_return: bool = True,
         show_time: bool = True,
         log_file: Optional[str] = None,
         indent: int = 0) -> Callable:
    """
    装饰器：输出函数的详细调用信息
    
    参数:
        func (Callable): 被装饰的函数(自动传入，无需手动指定)
        show_args (bool): 是否显示位置参数，默认True
        show_kwargs (bool): 是否显示关键字参数，默认True
        show_return (bool): 是否显示返回值，默认True
        show_time (bool): 是否显示执行时间，默认True
        log_file (str): 日志文件路径，不指定则输出到stdout
        indent (int): 缩进空格数，用于嵌套调用时格式化输出
        
    返回:
        包装后的函数，调用时会输出详细信息
        
    示例:
        ```python
        @info()
        def add(a, b):
            return a + b
            
        @info(show_kwargs=False, log_file="app.log")
        def greet(name, message="Hello"):
            return f"{message}, {name}"
        ```
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            # 准备输出内容
            output = []
            indent_str = ' ' * indent
            
            # 函数基本信息
            output.append(f"{indent_str}┌── 调用函数: {f.__name__}")
            
            # 参数信息
            if show_args and args:
                sig = inspect.signature(f)
                params = list(sig.parameters.values())
                arg_details = []
                for i, arg in enumerate(args):
                    if i < len(params):
                        param_name = params[i].name
                        arg_details.append(f"{param_name}={repr(arg)}")
                    else:
                        arg_details.append(repr(arg))
                output.append(f"{indent_str}├── 位置参数: {', '.join(arg_details)}")
            
            if show_kwargs and kwargs:
                kwargs_details = [f"{k}={repr(v)}" for k, v in kwargs.items()]
                output.append(f"{indent_str}├── 关键字参数: {', '.join(kwargs_details)}")
            
            # 执行函数并计时
            start_time = time.perf_counter()
            result = f(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            
            # 返回值和执行时间
            if show_return:
                output.append(f"{indent_str}├── 返回值: {repr(result)}")
            
            if show_time:
                output.append(f"{indent_str}└── 执行时间: {elapsed:.6f}秒")
            else:
                output[-1] = output[-1].replace('├──', '└──')
            
            # 输出日志
            log_message = '\n'.join(output)
            if log_file:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\n\n')
            else:
                print(log_message + '\n')
            
            return result
        
        return wrapper
    
    # 处理带参数和不带参数的装饰器用法
    if func is None:
        return decorator
    else:
        return decorator(func)



def deprecated_func(original_func=None, *, reason=None, version=None, alternative=None):
    """
    装饰器：标记函数已弃用，并在调用时发出警告
    
    参数:
        reason (str): 弃用的原因说明
        version (str): 计划移除的版本号
        alternative (str): 推荐的替代函数或方法
        
    返回:
        包装后的函数，调用时会发出弃用警告
        
    示例:
        ```@deprecated_func(reason="使用新API", version="2.0", alternative="new_function")
        def old_function():
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 构建详细的警告消息
            message = f"函数 {func.__name__} 已被弃用"
            if reason:
                message += f"，原因: {reason}"
            if version:
                message += f"，将在 {version} 版本中移除"
            if alternative:
                message += f"，请使用 {alternative} 替代"
                
            # 发出更正式的警告
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            
            # 执行原始函数
            return func(*args, **kwargs)
        return wrapper
    
    # 处理带参数和不带参数的装饰器用法
    if original_func is None:
        return decorator
    else:
        return decorator(original_func)