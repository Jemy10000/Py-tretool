"""
### PyPlugin - Python 高级插件库
##### 概述\n
PyPlugin 是一个功能强大的 Python 插件系统框架，提供了完整的插件开发、加载和执行解决方案。该系统特别适合构建可扩展的应用程序，支持：

- 插件生命周期管理：自动处理插件的加载、验证和执行

- 智能依赖检查：支持版本规范的依赖管理 (package>=1.2.0)

- 元数据验证：自动检查插件元数据的完整性和合理性

- 优先级系统：数值越小优先级越高(1-100范围)

- 彩色终端输出：使用 Rich 库提供直观的状态反馈
"""

import importlib

from abc import ABC, abstractmethod
from typing import Type, List, Dict, Any, overload, Union

from rich import print as rich_print
from packaging.version import parse as parse_version



class PluginBase(ABC):
    """插件基类，支持高级扩展功能"""
    
    # 类属性定义元数据（子类可覆盖）
    metadata = {
        "name": "Unnamed Plugin",
        "version": "1.0.0",
        "author": "Anonymous",
        "description": "No description provided"
    }
    
    # 定义插件依赖包（子类可覆盖）
    required_packages: List[str] = []
    
    # 默认执行优先级（数值越小优先级越高）
    priority: int = 10

    

    def __init__(self):
        """初始化时自动检查依赖"""
        self._check_metadata()

        self._check_dependencies()
        
    def _check_dependencies(self):
        """验证依赖包是否已安装，并检查版本要求"""
        missing = []
        invalid = []
        version_issues = []
        
        # 处理特殊的依赖格式 (如 "package>=1.0")
        dependencies = []
        for dep in self.required_packages:
            if isinstance(dep, str) and any(op in dep for op in [">", "<", "=", "!"]):
                # 处理版本要求
                try:
                    pkg_name = dep.split('>')[0].split('<')[0].split('=')[0].split('!')[0].strip()
                    dependencies.append((pkg_name, dep))
                except Exception:
                    dependencies.append((dep, None))
            else:
                dependencies.append((dep, None))
        
        for pkg, version_spec in dependencies:
            try:
                # 尝试导入模块
                module = importlib.import_module(pkg)
                
                # 检查版本要求
                if version_spec:
                    if hasattr(module, "__version__"):
                        installed_version = module.__version__
                        
                        # 解析版本规范
                        if ">=" in version_spec:
                            min_version = version_spec.split(">=")[1].strip()
                            if parse_version(installed_version) < parse_version(min_version):
                                version_issues.append(f"{pkg} (需要版本 >= {min_version}, 当前版本 {installed_version})")
                        
                        elif "<=" in version_spec:
                            max_version = version_spec.split("<=")[1].strip()
                            if parse_version(installed_version) > parse_version(max_version):
                                version_issues.append(f"{pkg} (需要版本 <= {max_version}, 当前版本 {installed_version})")
                        
                        elif "==" in version_spec:
                            exact_version = version_spec.split("==")[1].strip()
                            if parse_version(installed_version) != parse_version(exact_version):
                                version_issues.append(f"{pkg} (需要版本 == {exact_version}, 当前版本 {installed_version})")
                        
                        elif "!=" in version_spec:
                            exclude_version = version_spec.split("!=")[1].strip()
                            if parse_version(installed_version) == parse_version(exclude_version):
                                version_issues.append(f"{pkg} (需要版本 != {exclude_version}, 当前版本 {installed_version})")
                        
                        elif ">" in version_spec:
                            min_version = version_spec.split(">")[1].strip()
                            if parse_version(installed_version) <= parse_version(min_version):
                                version_issues.append(f"{pkg} (需要版本 > {min_version}, 当前版本 {installed_version})")
                        
                        elif "<" in version_spec:
                            max_version = version_spec.split("<")[1].strip()
                            if parse_version(installed_version) >= parse_version(max_version):
                                version_issues.append(f"{pkg} (需要版本 < {max_version}, 当前版本 {installed_version})")
            except ModuleNotFoundError:
                invalid.append(f"{pkg} (Module not found)")
            except ImportError:
                missing.append(pkg)
            except Exception as e:
                invalid.append(f"{pkg} ({str(e)})")
    
        # 构建错误消息
        error_msgs = []
        if missing:
            error_msgs.append(
                f"缺少必要依赖包: {', '.join(missing)}\n"
                f"请使用命令安装: pip install {' '.join(missing)}"
            )
        
        if invalid:
            error_msgs.append(
                f"无效的依赖包: {', '.join(invalid)}\n"
                f"请检查包名是否正确或尝试重新安装"
            )
        
        if version_issues:
            error_msgs.append(
                f"版本不兼容的依赖包: {', '.join(version_issues)}\n"
                f"请使用命令升级: pip install --upgrade {' '.join([v.split(' ')[0] for v in version_issues])}"
            )
        
        if error_msgs:
            raise ImportError("\n\n".join(error_msgs))

    def _check_metadata(self):
        """检查元数据是否被正确覆盖"""
        default_meta = PluginBase.metadata
        current_meta = self.metadata
        
        # 检查所有默认元数据字段是否存在
        missing_fields = [field for field in default_meta if field not in current_meta]
        
        # 检查是否有字段使用默认值
        default_values = [field for field in default_meta if current_meta.get(field) == default_meta[field]]
        
        if missing_fields:
            rich_print(f"[yellow]⚠️ 元数据字段缺失: {', '.join(missing_fields)}[/yellow]")
        
        if default_values:
            rich_print(f"[yellow]⚠️ 使用默认元数据值: {', '.join(default_values)}[/yellow]")
        
        # 检查关键字段是否有效
        if current_meta.get("name") == "Unnamed Plugin":
            rich_print("[yellow]⚠️ 插件名称未定义，使用默认名称[/yellow]")
        
        if current_meta.get("version") == "1.0.0":
            rich_print("[yellow]⚠️ 插件版本未定义，使用默认版本[/yellow]")

    def get_plugin_name(self):
        return self.metadata['name']

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """插件核心处理方法"""
        pass

    @classmethod
    def get_metadata(cls) -> Dict[str, str]:
        """获取插件元数据"""
        return cls.metadata.copy()



# 全局插件注册表（保持按优先级排序）
_PLUGIN_REGISTRY: List[PluginBase] = []



def load_plugin(
    plugin_class: Type[PluginBase],
    priority: int = None,
    verbose: bool = False
) -> bool:
    """
    加载并验证插件类
    
    参数:
        plugin_class: 必须继承自PluginBase的类
        priority: 执行优先级（覆盖类默认值）
        verbose: 是否显示加载详情
        
    返回:
        bool: 是否成功加载
    """
    try:
        # 类型验证
        if not issubclass(plugin_class, PluginBase):
            raise TypeError("必须继承自PluginBase")
            
        # 实例化插件（自动触发依赖检查）
        instance = plugin_class()
        
        # 设置优先级
        if priority is not None:
            instance.priority = priority
        else:
            instance.priority = plugin_class.priority
            
        # 插入排序保持注册表有序
        insert_pos = 0
        while (insert_pos < len(_PLUGIN_REGISTRY) and 
               _PLUGIN_REGISTRY[insert_pos].priority <= instance.priority):
            insert_pos += 1
            
        _PLUGIN_REGISTRY.insert(insert_pos, instance)
        
        if verbose:
            meta = plugin_class.get_metadata()
            print(
                f"✅ 成功加载插件: {meta['name']} v{meta['version']}\n"
                f"   作者: {meta['author']}\n"
                f"   优先级: {instance.priority}\n"
                f"   依赖: {plugin_class.required_packages}"
            )
            
        return True
        
    except Exception as e:
        if verbose:
            print(f"❌ 加载失败: {str(e)}")
        return False



@overload
def execute_pipeline(data: List[Any] = None):
    """按优先级顺序执行所有插件"""
    ...


@overload
def execute_pipeline(data: Dict[str, Any] = None):
    """按优先级顺序执行所有插件"""
    ...


def execute_pipeline(data: Any = None) -> dict:
    """按优先级顺序执行所有插件"""
    if isinstance(data, list):
        res_dict = {}
        for index, plugin in enumerate(_PLUGIN_REGISTRY):
            result = plugin.execute(data[index])
            res_dict[plugin.get_plugin_name()] = result
        return res_dict
    else:
        res_dict = {}
        for index, plugin in enumerate(_PLUGIN_REGISTRY):
            result = plugin.execute(data[plugin.get_plugin_name()])
            res_dict[plugin.get_plugin_name()] = result
        return res_dict


def execute_plugin_by_file(
    filepath: str, 
    data: Any = None,
    plugin_class_name: str = None,
    execute_all: bool = False
) -> Union[Any, Dict[str, Any]]:
    """
    从Python文件加载并执行插件
    
    参数:
        filepath: Python文件路径
        data: 传递给插件的数据
        plugin_class_name: 指定要执行的插件类名(可选)
        execute_all: 是否执行文件中所有插件(默认False)
        
    返回:
        单个插件结果 或 字典格式的{插件类名: 执行结果}
        
    异常:
        ValueError: 当文件包含多个插件但未指定执行方式时
        ImportError: 如果文件加载失败
    """
    import os
    import importlib.util
    from collections import OrderedDict

    # 验证文件存在
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"插件文件不存在: {filepath}")
    
    # 动态加载模块
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None:
        raise ImportError(f"无效的Python模块: {filepath}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # 查找所有合法插件类
    plugin_classes = OrderedDict()
    for name, obj in module.__dict__.items():
        if (isinstance(obj, type) and 
            issubclass(obj, PluginBase) and 
            obj != PluginBase):
            plugin_classes[name] = obj
    
    # 处理插件类发现情况
    if not plugin_classes:
        raise AttributeError(f"文件中未找到有效的插件类(需继承PluginBase): {filepath}")
    
    # 多插件处理逻辑
    if len(plugin_classes) > 1:
        if not (plugin_class_name or execute_all):
            raise ValueError(
                f"文件中发现多个插件类: {list(plugin_classes.keys())}\n"
                "请指定 plugin_class_name 或设置 execute_all=True"
            )
    
    # 执行单个指定插件
    if plugin_class_name:
        if plugin_class_name not in plugin_classes:
            raise KeyError(f"插件类 '{plugin_class_name}' 不存在，可选: {list(plugin_classes.keys())}")
        
        plugin_class = plugin_classes[plugin_class_name]
        if load_plugin(plugin_class, verbose=True):
            return plugin_class().execute(data)
        raise RuntimeError(f"插件加载失败: {plugin_class_name}")
    
    # 执行所有插件
    results = {}
    for name, plugin_class in plugin_classes.items():
        try:
            if load_plugin(plugin_class, verbose=True):
                results[name] = plugin_class().execute(data)
        except Exception as e:
            rich_print(f"[red]❌ 插件 {name} 执行失败: {str(e)}[/red]")
            results[name] = {"error": str(e)}
    
    return results