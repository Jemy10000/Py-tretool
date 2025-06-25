"""
### 配置管理库，提供安全的键值对存储和访问机制

特性:
- 类型安全的设置和获取
- 默认值支持
- 批量操作支持
- 配置项存在性检查
- 防止意外覆盖
- 配置文件持久化
- 配置变更回调
"""

import json
import os
from typing import Any, Callable, Dict, Optional

class Config:
    """
    配置管理类，提供安全的键值对存储和访问机制
    
    特性:
    - 类型安全的设置和获取
    - 默认值支持
    - 批量操作支持
    - 配置项存在性检查
    - 防止意外覆盖
    - 配置变更通知
    
    使用示例:
    ```
        config = Config({"theme": "dark"})
        config.set_config("font_size", 14)
        theme = config.get_config("theme", default="light")
        
        # 添加配置变更监听
        def on_config_change(key, old_value, new_value):
            print(f"配置变更: {key} 从 {old_value} 改为 {new_value}")
            
        config.add_change_listener(on_config_change)
        
        # 保存和加载配置
        config.save_to_file("settings.json")
        new_config = Config.load_from_file("settings.json")
    ```
    """
    
    def __init__(self, initial_config: Optional[Dict[str, Any]] = None):
        """
        初始化配置存储
        
        参数:
            initial_config: 初始配置字典 (可选)
        """
        self.config_dict = initial_config.copy() if initial_config else {}
        self._lock = False  # 防止意外修改的锁
        self._change_listeners = []  # 配置变更监听器列表
        
    def __str__(self) -> str:
        """返回配置的可读字符串表示"""
        return json.dumps(self.config_dict, indent=2, ensure_ascii=False)
    
    def __repr__(self) -> str:
        """返回配置的正式表示"""
        return f"Config({self.config_dict})"
    
    def __contains__(self, item: str) -> bool:
        """检查配置项是否存在"""
        return item in self.config_dict
    
    def __len__(self) -> int:
        """返回配置项的数量"""
        return len(self.config_dict)
    
    def add_change_listener(self, listener: Callable[[str, Any, Any], None]):
        """
        添加配置变更监听器
        
        参数:
            listener: 回调函数，格式为 func(key, old_value, new_value)
        """
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable[[str, Any, Any], None]):
        """移除配置变更监听器"""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    def _notify_change(self, key: str, old_value: Any, new_value: Any):
        """通知所有监听器配置变更"""
        for listener in self._change_listeners:
            try:
                listener(key, old_value, new_value)
            except Exception as e:
                print(f"配置变更通知错误: {e}")
    
    def get_config(self, item: str, default: Any = None) -> Any:
        """
        安全获取配置项
        
        参数:
            item: 配置键名
            default: 当键不存在时返回的默认值
            
        返回:
            配置值或默认值
        """
        return self.config_dict.get(item, default)

    def set_config(self, item: str, value: Any) -> bool:
        """
        设置配置项
        
        参数:
            item: 配置键名
            value: 配置值
            
        返回:
            True 设置成功, False 设置失败
        """
        if self._lock:
            print(f"警告: 配置系统已锁定，无法修改 '{item}'")
            return False
            
        old_value = self.config_dict.get(item)
        self.config_dict[item] = value
        
        # 通知变更
        self._notify_change(item, old_value, value)
        return True

    def delete_config(self, item: str) -> bool:
        """
        删除配置项
        
        参数:
            item: 要删除的配置键名
            
        返回:
            True 删除成功, False 键不存在
        """
        if item in self.config_dict:
            old_value = self.config_dict[item]
            del self.config_dict[item]
            
            # 通知变更 (值为 None 表示删除)
            self._notify_change(item, old_value, None)
            return True
        return False

    def save_to_file(self, filename: str) -> bool:
        """
        保存配置到文件
        
        参数:
            filename: 文件名
            
        返回:
            True 保存成功, False 保存失败
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.get_all_configs(), f, indent=2, ensure_ascii=False)
            return True
        except (IOError, TypeError) as e:
            print(f"保存配置失败: {e}")
            return False

    @classmethod
    def load_from_file(cls, filename: str) -> Optional['Config']:
        """
        从文件加载配置
        
        参数:
            filename: 文件名
            
        返回:
            加载成功的 Config 实例，失败返回 None
        """
        if not os.path.exists(filename):
            print(f"配置文件不存在: {filename}")
            return None
            
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                return cls(config_data)
        except (IOError, json.JSONDecodeError) as e:
            print(f"加载配置失败: {e}")
            return None

    def has_config(self, item: str) -> bool:
        """检查配置项是否存在"""
        return item in self.config_dict

    def lock_config(self):
        """锁定配置防止修改"""
        self._lock = True

    def unlock_config(self):
        """解锁配置允许修改"""
        self._lock = False

    def is_locked(self) -> bool:
        """检查配置是否已锁定"""
        return self._lock

    def bulk_update(self, update_dict: Dict[str, Any]) -> bool:
        """
        批量更新配置
        
        参数:
            update_dict: 包含多个键值对的字典
            
        返回:
            True 更新成功, False 更新失败
        """
        if self._lock:
            print("警告: 配置系统已锁定，批量更新被拒绝")
            return False
            
        # 记录变更
        changes = {}
        for key, value in update_dict.items():
            old_value = self.config_dict.get(key)
            self.config_dict[key] = value
            changes[key] = (old_value, value)
        
        # 批量通知变更
        for key, (old_value, new_value) in changes.items():
            self._notify_change(key, old_value, new_value)
            
        return True

    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置的副本"""
        return self.config_dict.copy()
    
    def reset_config(self, new_config: Optional[Dict[str, Any]] = None) -> None:
        """
        重置所有配置
        
        参数:
            new_config: 新的配置字典 (可选，默认清空)
        """
        if self._lock:
            print("警告: 配置系统已锁定，无法重置")
            return
            
        # 记录所有变更（删除）
        for key in list(self.config_dict.keys()):
            old_value = self.config_dict[key]
            self._notify_change(key, old_value, None)
        
        # 重置配置
        self.config_dict = new_config.copy() if new_config else {}
        
        # 通知所有新配置项
        for key, value in self.config_dict.items():
            self._notify_change(key, None, value)

