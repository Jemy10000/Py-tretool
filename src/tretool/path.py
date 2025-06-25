import os
import sys
import stat
import shutil
import fnmatch
import tempfile
import hashlib
import filecmp
from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    Union, List, Optional, Iterator, Tuple, Dict, Any, overload, IO
)

PathLike = Union[str, bytes, os.PathLike]

class PurePath(ABC):
    """
    纯路径基类，提供与操作系统无关的路径操作
    
    这是一个抽象基类，提供不依赖实际文件系统的路径操作。
    子类应实现特定平台的行为。
    
    参数:
        *pathsegments: 路径组成部分，可以是字符串、字节或os.PathLike对象
    
    示例:
        >>> path = PurePath('foo', 'bar', 'baz.txt')
        >>> str(path)
        'foo/bar/baz.txt'
    """
    
    def __init__(self, *pathsegments: PathLike):
        """初始化一个新的PurePath实例"""
        self._parts = self._parse_args(pathsegments)
        self._drv = self._parse_drive(self._parts[0]) if self._parts else ''
        self._root = self._parse_root(self._parts[0]) if self._parts else ''
        
    def _parse_args(self, args) -> List[str]:
        """
        将路径参数解析为路径组件列表
        
        参数:
            args: 路径段序列
            
        返回:
            清理后的路径组件列表
            
        异常:
            TypeError: 如果参数不是字符串、字节或os.PathLike对象
        """
        parts = []
        for arg in args:
            if isinstance(arg, (str, bytes)):
                if isinstance(arg, bytes):
                    arg = arg.decode('utf-8', 'surrogateescape')
                parts.extend(arg.split(os.sep))
            elif hasattr(arg, '__fspath__'):
                parts.extend(str(arg).split(os.sep))
            else:
                raise TypeError(f"参数应为路径或字符串，不是 {type(arg)}")
        return [p for p in parts if p]  # 过滤空部分
    
    def _parse_drive(self, part: str) -> str:
        """
        从路径组件中提取驱动器号(Windows专用)
        
        参数:
            part: 第一个路径组件
            
        返回:
            驱动器号(如'C:')或空字符串
        """
        if len(part) > 1 and part[1] == ':':
            return part[:2]
        return ''
    
    def _parse_root(self, part: str) -> str:
        """
        从路径组件中提取根目录
        
        参数:
            part: 第一个路径组件
            
        返回:
            根目录(如'/')或空字符串
        """
        if part.startswith(os.sep):
            return os.sep
        return ''
    
    @property
    def parts(self) -> Tuple[str, ...]:
        """
        以元组形式访问路径的各个组件
        
        返回:
            路径组件的元组
        """
        return tuple(self._parts)
    
    @property
    def drive(self) -> str:
        """
        驱动器字母或名称(仅Windows)
        
        返回:
            驱动器号(如'C:')或空字符串
        """
        return self._drv
    
    @property
    def root(self) -> str:
        """
        路径的根目录(如果有)
        
        返回:
            根目录(如'/')或空字符串
        """
        return self._root
    
    @property
    def name(self) -> str:
        """
        路径的最后一个组件(如果有)
        
        返回:
            最后一个路径组件或空字符串
        """
        if not self._parts:
            return ''
        return self._parts[-1]
    
    @property
    def suffix(self) -> str:
        """
        最后一个组件的文件扩展名
        
        返回:
            包含点的文件扩展名(如'.txt')或空字符串
        """
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[i:]
        return ''
    
    @property
    def suffixes(self) -> List[str]:
        """
        路径的所有文件扩展名列表
        
        返回:
            包含点的扩展名列表(如['.tar', '.gz'])
        """
        name = self.name
        if name.endswith('.'):
            return []
        return ['.' + ext for ext in name.split('.')[1:]]
    
    @property
    def stem(self) -> str:
        """
        最后一个组件不带后缀
        
        返回:
            不带扩展名的名称
        """
        name = self.name
        i = name.rfind('.')
        if 0 < i < len(name) - 1:
            return name[:i]
        return name
    
    def joinpath(self, *args) -> 'PurePath':
        """
        将此路径与一个或多个参数组合
        
        参数:
            *args: 要连接的路径段
            
        返回:
            新路径，组合了当前路径和参数
        """
        return self.__class__(self, *args)
    
    def to_str(self) -> str:
        """
        将路径对象转换为字符串形式。

        返回:
            str: 使用系统路径分隔符的路径字符串表示，效果等同于直接调用 str(path_obj)。

        注意:
            - 转换结果取决于操作系统的路径规范（Windows/Linux 可能不同）
            - 对于纯路径对象（PurePath），不会验证路径是否真实存在

        示例:
        ```
            >>> p = Path('/usr/local/bin')
            >>> p.to_str()
            '/usr/local/bin'
        """
        return str(self)
    
    def __truediv__(self, other) -> 'PurePath':
        """
        使用/运算符连接路径
        
        参数:
            other: 要追加的路径段
            
        返回:
            新组合的路径
        """
        return self.joinpath(other)
    
    def __str__(self) -> str:
        """返回路径的字符串表示"""
        if self._drv and self._root:
            return self._drv + self._root + os.sep.join(self._parts[1:])
        elif self._root:
            return self._root + os.sep.join(self._parts)
        elif self._drv:
            return self._drv + os.sep.join(self._parts)
        return os.sep.join(self._parts)
    
    def __repr__(self) -> str:
        """返回路径的正式字符串表示"""
        return f"{self.__class__.__name__}('{self}')"
    
    def __eq__(self, other) -> bool:
        """比较路径是否相等"""
        if not isinstance(other, PurePath):
            return NotImplemented
        return str(self) == str(other)
    
    def __hash__(self) -> int:
        """计算路径的哈希值"""
        return hash(str(self))


class PurePosixPath(PurePath):
    """
    非Windows系统的PurePath子类
    
    此版本不支持驱动器号并使用正斜杠
    """


class PureWindowsPath(PurePath):
    """
    Windows系统的PurePath子类
    
    此版本支持驱动器号并使用反斜杠
    """


class Path(PurePath):
    """
    具体路径类，提供文件系统操作
    
    此类继承自PurePath并添加实际文件系统操作
    """

    def stat(self) -> os.stat_result:
        """
        返回此路径的stat信息
        
        返回:
            os.stat_result对象
            
        异常:
            OSError: 如果路径不存在
        """
        return os.stat(str(self))
    
    def exists(self) -> bool:
        """
        检查路径是否存在
        
        返回:
            如果路径存在返回True，否则返回False
        """
        return os.path.exists(str(self))
    
    def is_file(self) -> bool:
        """
        检查路径是否是普通文件
        
        返回:
            如果路径是文件返回True，否则返回False
        """
        return os.path.isfile(str(self))
    
    def is_dir(self) -> bool:
        """
        检查路径是否是目录
        
        返回:
            如果路径是目录返回True，否则返回False
        """
        return os.path.isdir(str(self))
    
    def mkdir(self, mode=0o777, parents=False, exist_ok=False):
        """
        创建新目录
        
        参数:
            mode: 权限(八进制数)
            parents: 如果需要是否创建父目录
            exist_ok: 如果目录已存在是否不报错
            
        异常:
            FileExistsError: 如果目录已存在且exist_ok为False
            OSError: 如果目录无法创建
        """
        path = str(self)
        if parents:
            os.makedirs(path, mode, exist_ok=exist_ok)
        else:
            try:
                os.mkdir(path, mode)
            except FileExistsError:
                if not exist_ok:
                    raise
    
    def open(self, mode='r', buffering=-1, encoding=None, 
             errors=None, newline=None) -> IO:
        """
        打开此路径指向的文件
        
        参数:
            mode: 打开模式('r', 'w'等)
            buffering: 缓冲策略
            encoding: 文本编码
            errors: 编码错误处理策略
            newline: 换行控制
            
        返回:
            文件对象
            
        异常:
            OSError: 如果文件无法打开
        """
        return open(str(self), mode, buffering, encoding, errors, newline)
    
    def read_text(self, encoding=None, errors=None) -> str:
        """
        以文本形式读取文件内容
        
        参数:
            encoding: 文本编码
            errors: 编码错误处理策略
            
        返回:
            文件内容字符串
            
        异常:
            OSError: 如果文件无法读取
        """
        with open(str(self), 'r', encoding=encoding, errors=errors) as f:
            return f.read()
    
    def write_text(self, data: str, encoding=None, errors=None):
        """
        以文本形式写入文件内容
        
        参数:
            data: 要写入的字符串
            encoding: 文本编码
            errors: 编码错误处理策略
            
        返回:
            写入的字符数
            
        异常:
            OSError: 如果文件无法写入
        """
        with open(str(self), 'w', encoding=encoding, errors=errors) as f:
            return f.write(data)
    
    def read_bytes(self) -> bytes:
        """
        以二进制形式读取文件内容
        
        返回:
            文件内容的字节串
            
        异常:
            OSError: 如果文件无法读取
        """
        with open(str(self), 'rb') as f:
            return f.read()
    
    def write_bytes(self, data: bytes):
        """
        以二进制形式写入文件内容
        
        参数:
            data: 要写入的字节串
            
        返回:
            写入的字节数
            
        异常:
            OSError: 如果文件无法写入
        """
        with open(str(self), 'wb') as f:
            return f.write(data)
    
    def unlink(self, missing_ok=False):
        """
        删除文件
        
        参数:
            missing_ok: 如果文件不存在是否不报错
            
        异常:
            FileNotFoundError: 如果文件不存在且missing_ok为False
            OSError: 如果文件无法删除
        """
        try:
            os.unlink(str(self))
        except FileNotFoundError:
            if not missing_ok:
                raise
    
    def rmdir(self):
        """
        删除空目录
        
        异常:
            OSError: 如果目录不为空或无法删除
        """
        os.rmdir(str(self))
    
    def rename(self, target) -> 'Path':
        """
        重命名文件或目录
        
        参数:
            target: 目标路径
            
        返回:
            新的Path对象
            
        异常:
            OSError: 如果重命名失败
        """
        os.rename(str(self), str(target))
        return self.__class__(target)
    
    def resolve(self) -> 'Path':
        """
        解析符号链接的绝对路径
        
        返回:
            解析后的新Path对象
        """
        return self.__class__(os.path.realpath(str(self)))
    
    def absolute(self) -> 'Path':
        """
        获取绝对路径
        
        返回:
            绝对路径的新Path对象
        """
        return self.__class__(os.path.abspath(str(self)))
    
    def glob(self, pattern: str) -> Iterator['Path']:
        """
        匹配文件模式
        
        参数:
            pattern: 要匹配的模式(如'*.txt')
            
        返回:
            匹配路径的生成器
        """
        import glob
        for p in glob.glob(str(self / pattern)):
            yield self.__class__(p)
    
    def rglob(self, pattern: str) -> Iterator['Path']:
        """
        递归匹配文件模式
        
        参数:
            pattern: 要匹配的模式
            
        返回:
            匹配路径的生成器
        """
        return self.glob('**' + os.sep + pattern)
    
    def iterdir(self) -> Iterator['Path']:
        """
        迭代目录内容
        
        返回:
            目录中子项的Path对象生成器
            
        异常:
            OSError: 如果不是目录或无法读取
        """
        for name in os.listdir(str(self)):
            yield self.__class__(self, name)
    
    @property
    def parent(self) -> 'Path':
        """
        父目录
        
        返回:
            父目录的Path对象
        """
        return self.__class__(os.path.dirname(str(self)))
    
    @property
    def parents(self) -> List['Path']:
        """
        所有父目录列表
        
        返回:
            从近到远的所有父目录Path对象列表
        """
        path = self
        parents = []
        while True:
            parent = path.parent
            if parent == path:
                break
            parents.append(parent)
            path = parent
        return parents
    
    def with_name(self, name: str) -> 'Path':
        """
        返回修改文件名后的新路径
        
        参数:
            name: 新文件名
            
        返回:
            新Path对象
            
        异常:
            ValueError: 如果当前路径没有名称
        """
        if not self.name:
            raise ValueError(f"{self} 没有名称")
        return self.__class__(self.parent, name)
    
    def with_suffix(self, suffix: str) -> 'Path':
        """
        返回修改后缀后的新路径
        
        参数:
            suffix: 新后缀(必须以点开头)
            
        返回:
            新Path对象
            
        异常:
            ValueError: 如果后缀无效或路径没有名称
        """
        if not suffix.startswith('.'):
            raise ValueError("无效的后缀")
        name = self.name
        if not name:
            raise ValueError(f"{self} 没有名称")
        
        old_suffix = self.suffix
        if old_suffix:
            name = name[:-len(old_suffix)]
        return self.__class__(self.parent, name + suffix)
    
    # ===== 增强功能 =====
    def touch(self, mode=0o666, exist_ok=True):
        """
        创建空文件(类似Unix touch命令)
        
        参数:
            mode: 文件权限
            exist_ok: 如果文件存在是否不报错
            
        异常:
            FileExistsError: 如果文件存在且exist_ok为False
            OSError: 如果文件无法创建
        """
        if self.exists():
            if exist_ok:
                os.utime(str(self), None)
            else:
                raise FileExistsError(str(self))
        else:
            open(str(self), 'a').close()
            self.chmod(mode)
    
    def copy(self, target, follow_symlinks=True):
        """
        复制文件到目标路径
        
        参数:
            target: 目标路径
            follow_symlinks: 是否跟随符号链接
            
        返回:
            目标路径的Path对象
            
        异常:
            OSError: 如果复制失败
        """
        shutil.copy2(str(self), str(target), follow_symlinks=follow_symlinks)
        return self.__class__(target)
    
    def move(self, target):
        """
        移动文件/目录到目标位置
        
        参数:
            target: 目标路径
            
        返回:
            目标路径的Path对象
            
        异常:
            OSError: 如果移动失败
        """
        shutil.move(str(self), str(target))
        return self.__class__(target)
    
    def size(self) -> int:
        """
        获取文件大小(字节)
        
        返回:
            文件大小(字节)
            
        异常:
            OSError: 如果无法获取大小
        """
        return self.stat().st_size
    
    def access_time(self) -> datetime:
        """
        获取最后访问时间
        
        返回:
            最后访问时间的datetime对象
        """
        return datetime.fromtimestamp(self.stat().st_atime)
    
    def modify_time(self) -> datetime:
        """
        获取最后修改时间
        
        返回:
            最后修改时间的datetime对象
        """
        return datetime.fromtimestamp(self.stat().st_mtime)
    
    def create_time(self) -> datetime:
        """
        获取创建时间(Windows)或元数据修改时间(Unix)
        
        返回:
            创建时间的datetime对象
        """
        if os.name == 'nt':
            return datetime.fromtimestamp(self.stat().st_ctime)
        return datetime.fromtimestamp(self.stat().st_mtime)
    
    def rmtree(self, ignore_errors=False, onerror=None):
        """
        递归删除目录树
        
        参数:
            ignore_errors: 是否忽略错误
            onerror: 错误处理回调函数
            
        异常:
            OSError: 如果删除失败且ignore_errors为False
        """
        shutil.rmtree(str(self), ignore_errors, onerror)
    
    def find(self, pattern: str = "*") -> Iterator['Path']:
        """
        递归查找匹配模式的文件
        
        参数:
            pattern: 要匹配的模式(如'*.py')
            
        返回:
            匹配路径的生成器
        """
        for root, _, files in os.walk(str(self)):
            for name in fnmatch.filter(files, pattern):
                yield self.__class__(root, name)
    
    def read_lines(self, encoding=None, errors=None) -> List[str]:
        """
        按行读取文件内容
        
        参数:
            encoding: 文本编码
            errors: 编码错误处理策略
            
        返回:
            行列表
            
        异常:
            OSError: 如果文件无法读取
        """
        with self.open('r', encoding=encoding, errors=errors) as f:
            return f.readlines()
    
    def write_lines(self, lines: List[str], encoding=None, errors=None):
        """
        按行写入文件内容
        
        参数:
            lines: 要写入的行列表
            encoding: 文本编码
            errors: 编码错误处理策略
            
        异常:
            OSError: 如果文件无法写入
        """
        with self.open('w', encoding=encoding, errors=errors) as f:
            f.writelines(lines)
    
    def append_text(self, text: str, encoding=None, errors=None):
        """
        追加文本内容
        
        参数:
            text: 要追加的文本
            encoding: 文本编码
            errors: 编码错误处理策略
            
        异常:
            OSError: 如果文件无法写入
        """
        with self.open('a', encoding=encoding, errors=errors) as f:
            f.write(text)
    
    def md5(self, chunk_size=8192) -> str:
        """
        计算文件的MD5哈希值
        
        参数:
            chunk_size: 读取块大小
            
        返回:
            MD5哈希字符串
        """
        hash_md5 = hashlib.md5()
        with self.open('rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def sha256(self, chunk_size=8192) -> str:
        """
        计算文件的SHA256哈希值
        
        参数:
            chunk_size: 读取块大小
            
        返回:
            SHA256哈希字符串
        """
        hash_sha = hashlib.sha256()
        with self.open('rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_sha.update(chunk)
        return hash_sha.hexdigest()
    
    def compare(self, other: 'Path', shallow=True) -> bool:
        """
        比较文件内容是否相同
        
        参数:
            other: 要比较的另一路径
            shallow: 是否只比较元数据
            
        返回:
            如果内容相同返回True，否则返回False
        """
        if not isinstance(other, Path):
            other = Path(other)
        return filecmp.cmp(str(self), str(other), shallow=shallow)
    
    @classmethod
    def temp_file(cls, suffix=None, prefix=None, dir=None) -> 'Path':
        """
        创建临时文件
        
        参数:
            suffix: 后缀名
            prefix: 前缀名
            dir: 目录路径
            
        返回:
            临时文件的Path对象
        """
        fd, name = tempfile.mkstemp(suffix, prefix, dir)
        os.close(fd)
        return cls(name)
    
    @classmethod
    def temp_dir(cls, suffix=None, prefix=None, dir=None) -> 'Path':
        """
        创建临时目录
        
        参数:
            suffix: 后缀名
            prefix: 前缀名
            dir: 目录路径
            
        返回:
            临时目录的Path对象
        """
        return cls(tempfile.mkdtemp(suffix, prefix, dir))
    
    def readlink(self) -> 'Path':
        """
        读取符号链接指向的实际路径
        
        返回:
            实际路径的Path对象
            
        异常:
            OSError: 如果不是符号链接或无法读取
        """
        if not self.is_symlink():
            raise OSError(f"{self} 不是符号链接")
        return self.__class__(os.readlink(str(self)))
    
    def chmod(self, mode: int, *, follow_symlinks=True):
        """
        修改文件权限
        
        参数:
            mode: 权限模式(八进制)
            follow_symlinks: 是否跟随符号链接
            
        异常:
            OSError: 如果修改失败
        """
        if follow_symlinks:
            os.chmod(str(self), mode)
        else:
            if hasattr(os, 'lchmod'):  # 仅Unix
                os.lchmod(str(self), mode)
    
    def is_executable(self) -> bool:
        """
        检查文件是否可执行
        
        返回:
            如果可执行返回True，否则返回False
        """
        return os.access(str(self), os.X_OK)
    
    def relative_to(self, other: Union['Path', str]) -> 'Path':
        """
        计算相对于另一路径的相对路径
        
        参数:
            other: 基准路径
            
        返回:
            相对路径的Path对象
            
        异常:
            ValueError: 如果路径没有共同前缀
        """
        if not isinstance(other, Path):
            other = Path(other)
        return self.__class__(os.path.relpath(str(self), str(other)))
    
    def matches(self, pattern: str) -> bool:
        """
        检查路径是否匹配通配符模式
        
        参数:
            pattern: 要匹配的模式
            
        返回:
            如果匹配返回True，否则返回False
        """
        return fnmatch.fnmatch(str(self), pattern)
    
    def __enter__(self):
        """支持with语句，返回自身"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句，无操作"""
        pass


class PosixPath(Path, PurePosixPath):
    """
    POSIX系统专用路径实现
    
    仅在POSIX兼容系统(如Linux, macOS)上可用
    """
    
    def __new__(cls, *args, **kwargs):
        if os.name != 'posix' and os.name != 'java' and not sys.platform.startswith('linux'):
            raise NotImplementedError("PosixPath 仅支持POSIX系统")
        return super().__new__(cls, *args, **kwargs)
    
    def resolve(self, strict=False) -> 'PosixPath':
        """
        解析符号链接的绝对路径
        
        参数:
            strict: 如果路径不存在是否抛出异常
            
        返回:
            解析后的新Path对象
            
        异常:
            FileNotFoundError: 如果路径不存在且strict为True
        """
        path = os.path.realpath(str(self))
        if strict and not os.path.exists(path):
            raise FileNotFoundError(path)
        return self.__class__(path)
    
    def owner(self) -> str:
        """
        获取文件所有者
        
        返回:
            所有者用户名
            
        异常:
            OSError: 如果无法获取所有者信息
        """
        import pwd
        return pwd.getpwuid(self.stat().st_uid).pw_name
    
    def group(self) -> str:
        """
        获取文件所属组
        
        返回:
            组名
            
        异常:
            OSError: 如果无法获取组信息
        """
        import grp
        return grp.getgrgid(self.stat().st_gid).gr_name
    
    def symlink_to(self, target, target_is_directory=False):
        """
        创建符号链接
        
        参数:
            target: 目标路径
            target_is_directory: 目标是否是目录
            
        异常:
            OSError: 如果创建失败
        """
        os.symlink(
            str(target),
            str(self),
            target_is_directory=target_is_directory
        )
    
    def is_symlink(self) -> bool:
        """
        检查是否是符号链接
        
        返回:
            如果是符号链接返回True，否则返回False
        """
        return os.path.islink(str(self))
    
    def is_socket(self) -> bool:
        """
        检查是否是套接字文件
        
        返回:
            如果是套接字文件返回True，否则返回False
        """
        return stat.S_ISSOCK(self.stat().st_mode)
    
    def is_fifo(self) -> bool:
        """
        检查是否是FIFO管道
        
        返回:
            如果是FIFO管道返回True，否则返回False
        """
        return stat.S_ISFIFO(self.stat().st_mode)
    
    def is_block_device(self) -> bool:
        """
        检查是否是块设备
        
        返回:
            如果是块设备返回True，否则返回False
        """
        return stat.S_ISBLK(self.stat().st_mode)
    
    def is_char_device(self) -> bool:
        """
        检查是否是字符设备
        
        返回:
            如果是字符设备返回True，否则返回False
        """
        return stat.S_ISCHR(self.stat().st_mode)
    
    def expanduser(self) -> 'PosixPath':
        """
        展开用户目录(~)
        
        返回:
            展开后的新Path对象
        """
        return self.__class__(os.path.expanduser(str(self)))
    
    def is_hidden(self) -> bool:
        """
        检查文件是否隐藏(以点开头)
        
        返回:
            如果隐藏返回True，否则返回False
        """
        return self.name.startswith('.')


class WindowsPath(Path, PureWindowsPath):
    """
    Windows系统专用路径实现
    
    仅在Windows系统上可用
    """
    
    def __new__(cls, *args, **kwargs):
        if os.name != 'nt':
            raise NotImplementedError("WindowsPath 仅支持Windows系统")
        return super().__new__(cls, *args, **kwargs)
    
    def resolve(self, strict=False) -> 'WindowsPath':
        """
        解析绝对路径(Windows专用)
        
        参数:
            strict: 如果路径不存在是否抛出异常
            
        返回:
            解析后的新Path对象
            
        异常:
            FileNotFoundError: 如果路径不存在且strict为True
        """
        path = os.path.abspath(str(self))
        if strict and not os.path.exists(path):
            raise FileNotFoundError(path)
        return self.__class__(path)
    
    def owner(self) -> str:
        """
        获取文件所有者(需要pywin32)
        
        返回:
            所有者字符串(格式: 'DOMAIN\\username')
            
        异常:
            NotImplementedError: 如果没有安装pywin32
            OSError: 如果无法获取所有者信息
        """
        try:
            import win32security
            sd = win32security.GetFileSecurity(
                str(self), win32security.OWNER_SECURITY_INFORMATION
            )
            sid = sd.GetSecurityDescriptorOwner()
            name, domain, _ = win32security.LookupAccountSid(None, sid)
            return f"{domain}\\{name}"
        except ImportError:
            raise NotImplementedError("需要win32security模块")
    
    def is_junction(self) -> bool:
        """
        检查是否是junction点
        
        返回:
            如果是junction点返回True，否则返回False
        """
        try:
            return os.path.isjunction(str(self))
        except AttributeError:  # Python < 3.12 兼容
            try:
                import win32file
                return win32file.GetFileAttributes(str(self)) & win32file.FILE_ATTRIBUTE_REPARSE_POINT
            except ImportError:
                return False
    
    def is_mount(self) -> bool:
        """
        检查是否是挂载点(网络驱动器)
        
        返回:
            如果是挂载点返回True，否则返回False
        """
        try:
            import win32file
            drive = os.path.splitdrive(str(self))[0]
            if not drive:
                return False
            return win32file.GetDriveType(drive) == win32file.DRIVE_REMOTE
        except ImportError:
            return False
    
    def expanduser(self) -> 'WindowsPath':
        """
        Windows用户目录展开
        
        返回:
            展开后的新Path对象
        """
        if self.drive or self.root:
            return self
        home = os.path.expanduser("~")
        return self.__class__(home) / self
    
    def is_hidden(self) -> bool:
        """
        检查文件是否隐藏(系统隐藏属性或以点开头)
        
        返回:
            如果隐藏返回True，否则返回False
        """
        try:
            import win32api
            return win32api.GetFileAttributes(str(self)) & win32api.FILE_ATTRIBUTE_HIDDEN
        except ImportError:
            return self.name.startswith('.') or super().is_hidden()


# 根据系统选择默认Path实现
if os.name == 'nt':
    Path = WindowsPath
else:
    Path = PosixPath