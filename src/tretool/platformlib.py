import os
import sys
import ctypes
import platform
from typing import (Any, Dict, List, Union, SupportsIndex)


def get_python_dll() -> ctypes.PyDLL:
    """内部函数：获取 Python DLL 句柄"""
    is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
    dll_suffix = '_d' if hasattr(sys, 'gettotalrefcount') else ''
    dll_name = f"python{''.join(map(str, sys.version_info[:2]))}{dll_suffix}.dll"
    return ctypes.PyDLL(dll_name)


def get_python_version() -> str:
    """
    获取 Python 版本号
    返回格式：'major.minor.micro'
    """
    try:
        dll = get_python_dll()
        Py_GetVersion = dll.Py_GetVersion
        Py_GetVersion.restype = ctypes.c_char_p
        return Py_GetVersion().decode('ascii').split()[0]
    except Exception as e:
        return f'Error: {str(e)}'


def get_python_build() -> str:
    """
    获取 Python 构建信息
    返回格式：如 "v3.9.7:8d82e9e9b3, Aug 31 2021, 13:28:12"
    """
    try:
        dll = get_python_dll()
        Py_GetVersion = dll.Py_GetVersion
        Py_GetVersion.restype = ctypes.c_char_p
        version_info = Py_GetVersion().decode('ascii')
        return f"v{version_info.split('(', 1)[1].split(')')[0]}"
    except Exception as e:
        return f'Error: {str(e)}'


def get_python_compiler() -> str:
    """
    获取 Python 编译器信息
    返回格式：如 "[GCC 8.4.0]"
    """
    try:
        dll = get_python_dll()
        Py_GetVersion = dll.Py_GetVersion
        Py_GetVersion.restype = ctypes.c_char_p
        version_info = Py_GetVersion().decode('ascii')
        return version_info.split('[')[1].split(']')[0]
    except Exception as e:
        return f'Error: {str(e)}'


def get_python_path() -> str:
    """
    获取 Python 安装根目录（如 C:\\Python39）
    """
    try:
        return sys.executable.rsplit('\\', 1)[0]
    
    except Exception as e:
        return f'Error: {str(e)}'


def get_python_executable() -> str:
    """
    获取 Python 解释器路径
    """
    try:
        return sys.executable
    except Exception as e:
        return f'Error: {str(e)}'


def get_python_flags() -> Dict[str, bool]:
    """
    获取 Python 编译标志
    返回字典包含：
    - debug: 是否是调试版本
    - utf8_mode: 是否启用UTF-8模式
    """
    try:
        flags = {
            'debug': hasattr(sys, 'gettotalrefcount'),
            'utf8_mode': sys.flags.utf8_mode
        }
        return flags
    except Exception as e:
        return {'error': str(e)}


def get_python_implementation() -> str:
    """
    获取更友好的实现名称
    """
    impl = sys.implementation.name
    return {
        'cpython': 'CPython',
        'pypy': 'PyPy',
        'ironpython': 'IronPython',
        'jython': 'Jython'
    }.get(impl, impl.capitalize())


def get_full_python_info() -> Dict[str, str]:
    """
    获取完整的 Python 信息
    返回包含所有信息的字典
    """
    return {
        'version': get_python_version(),
        'build': get_python_build(),
        'compiler': get_python_compiler(),
        'path': get_python_path(),
        'executable': get_python_executable(),
        'flags': get_python_flags(),
        'implementation': get_python_implementation()
    }


def uname():
    return platform.uname()


def get_system() -> str:
    """
    获取操作系统类型（增强版）
    返回：
        'Windows'/'Linux'/'Darwin'/'Java' 等友好名称
    """
    system = platform.uname().system
    return {
        'Linux': 'Linux',
        'Darwin': 'macOS',
        'Windows': 'Windows',
        'Java': 'Java'
    }.get(system, system)


def release() -> str:
    """
    获取操作系统版本号（跨平台）
    返回：
        Linux: 内核版本 (如 '5.4.0-80-generic')
        Windows: 版本号 (如 '10')
        macOS: Darwin 版本 (如 '21.1.0')
    """
    try:
        if hasattr(os, 'uname'):
            return os.uname().release
        return platform.release()
    except Exception:
        return "unknown"


def machine() -> str:
    """
    获取系统架构（跨平台）
    返回：
        'x86_64'/'AMD64'/'arm64' 等标准架构名称
    """
    try:
        if hasattr(os, 'uname'):
            return os.uname().machine
        return platform.machine()
    except Exception:
        return "unknown"


def get_byteorder() -> str:
    """
    智能检测字节顺序（优先使用标准库）
    """
    try:
        import sys
        return sys.byteorder
    except ImportError:
        try:
            import ctypes
            num = 0x12345678
            buf = (ctypes.c_byte * 4).from_buffer_copy(ctypes.c_uint32(num))
            return 'big' if buf[0] == 0x12 else 'little'
        except:
            return 'unknown'


def get_args(index: SupportsIndex = None) -> Union[List[str], str]:
    """
    获取命令行参数（支持索引访问）
    
    参数：
        index - 可选参数索引（支持负数索引）
        
    返回：
        当index为None时：返回完整参数列表['script.py', 'arg1', ...]
        当指定index时：返回对应位置的参数值
        
    异常：
        IndexError - 当索引超出范围时引发
    """
    args = sys.argv
    
    if index is None:
        return args.copy()  # 返回副本避免外部修改
    
    try:
        return args[index]  # 自动支持SupportsIndex类型
    except IndexError:
        raise IndexError(f"参数索引 {index} 超出范围 (参数总数: {len(args)})") from None


def get_all_flags() -> Dict[str, Dict[str, Any]]:
    """
    获取Python解释器的完整标志信息
    
    返回：
        包含三个子字典的字典：
        - 'runtime_flags': 运行时标志（来自sys.flags）
        - 'build_info': 构建配置信息
        - 'unicode_info': Unicode相关配置
    
    标志说明：
        runtime_flags:
            debug: 调试模式
            inspect: 交互模式后进入检查模式
            interactive: 交互模式
            optimize: 优化级别 (0/1/2)
            dont_write_bytecode: 不生成.pyc文件
            no_user_site: 忽略用户site-packages
            no_site: 忽略所有site-packages
            ignore_environment: 忽略环境变量
            verbose: 详细输出
            bytes_warning: 字节警告
            quiet: 安静模式
            hash_randomization: 哈希随机化
            isolated: 隔离模式
            dev_mode: 开发模式
            utf8_mode: UTF-8模式
            warn_default_encoding: 默认编码警告
            safe_path: 安全路径模式
            int_max_str_digits: 整数字符串转换最大位数
    """
    return {
        'runtime_flags': get_runtime_flags(),
        'build_info': get_build_info(),
        'unicode_info': get_unicode_info()
    }


def get_runtime_flags() -> Dict[str, Any]:
    """获取sys.flags中的所有运行时标志"""
    flags = sys.flags
    return {
        'debug': flags.debug,
        'inspect': flags.inspect,
        'interactive': flags.interactive,
        'optimize': flags.optimize,
        'dont_write_bytecode': flags.dont_write_bytecode,
        'no_user_site': flags.no_user_site,
        'no_site': flags.no_site,
        'ignore_environment': flags.ignore_environment,
        'verbose': flags.verbose,
        'bytes_warning': flags.bytes_warning,
        'quiet': flags.quiet,
        'hash_randomization': flags.hash_randomization,
        'isolated': flags.isolated,
        'dev_mode': flags.dev_mode,
        'utf8_mode': flags.utf8_mode,
        'warn_default_encoding': getattr(flags, 'warn_default_encoding', 0),
        'safe_path': getattr(flags, 'safe_path', False),
        'int_max_str_digits': getattr(flags, 'int_max_str_digits', 0)
    }


def get_build_info() -> Dict[str, Any]:
    """获取构建配置信息"""
    return {
        'debug_build': hasattr(sys, 'gettotalrefcount'),
        'compiler': get_python_compiler(),
        'build_options': parse_build_options(),
        'platform': get_system(),
        'implementation': get_python_implementation()
    }


def parse_build_options() -> Dict[str, bool]:
    """从构建字符串解析编译选项"""
    build_str = sys.version
    options = {}
    
    # 常见构建选项检测
    for opt in ['WITH_PYMALLOC', 'WITH_THREAD', 'PYTHONFRAMEWORK']:
        options[opt] = opt in build_str
    
    # 检测内存分配器
    options['PYMALLOC'] = 'pymalloc' in build_str.lower()
    return options


def get_unicode_info() -> Dict[str, Any]:
    """获取Unicode配置信息"""
    return {
        'maxunicode': sys.maxunicode,
        'wide_build': sys.maxunicode > 0xFFFF,
        'default_encoding': sys.getdefaultencoding(),
        'filesystem_encoding': sys.getfilesystemencoding()
    }


def get_environment_report() -> Dict[str, Dict[str, str]]:
    """生成完整的环境报告"""
    return {
        'python': {
            'version': get_python_version(),
            'build': get_python_build(),
            'implementation': get_python_implementation(),
            'compiler': get_python_compiler(),
            'path': get_python_path(),
            'executable': get_python_executable()
        },
        'runtime': {
            'byteorder': get_byteorder(),
            'flags': get_all_flags(),
            'argv': get_args()
        }
    }
