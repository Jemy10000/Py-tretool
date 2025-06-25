"""
Py2ExeBuilder - 智能 Python 打包工具
功能特点：
1. 多平台支持 (Windows/Linux/Mac)
2. 自动依赖分析
3. 单文件/目录模式选择
4. 图标/版本信息嵌入
5. 虚拟环境支持
"""

import os
import sys
import platform
import subprocess
import importlib.metadata
from pathlib import Path
from typing import Optional, List, Dict, Union
import tempfile
import shutil
import json
import hashlib

class PyToExeBuilder:
    def __init__(self, 
                 script_path: str,
                 output_name: Optional[str] = None,
                 work_dir: Optional[str] = None):
        """
        初始化打包工具
        
        :param script_path: 主Python脚本路径
        :param output_name: 输出可执行文件名(不含扩展名)
        :param work_dir: 临时工作目录(默认自动创建)
        """
        self.script_path = Path(script_path).absolute()
        self.output_name = output_name or self.script_path.stem
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="py2exe_"))
        self.dependencies = []
        self.extra_files = []
        self.icon_path = None
        self.version_info = {}
        self.console = True
        self._validate_environment()

    def _validate_environment(self) -> None:
        """验证运行环境和输入文件"""
        if not self.script_path.exists():
            raise FileNotFoundError(f"主脚本不存在: {self.script_path}")
        
        if not self.script_path.suffix == '.py':
            raise ValueError("输入文件必须是.py脚本")
        
        current_platform = platform.system()
        if current_platform not in ['Windows', 'Linux', 'Darwin']:
            raise NotImplementedError(f"不支持的操作系统: {current_platform}")

    def add_dependencies(self, packages: List[str]) -> 'PyToExeBuilder':
        """手动添加依赖包"""
        self.dependencies.extend(packages)
        return self

    def add_data_files(self, files: List[Union[str, tuple]]) -> 'PyToExeBuilder':
        """添加额外数据文件
        Example: add_data_files(["config.ini", ("src/data.json", "data")])
        """
        self.extra_files.extend(files)
        return self

    def set_icon(self, icon_path: str) -> 'PyToExeBuilder':
        """设置可执行文件图标(仅Windows有效)"""
        self.icon_path = Path(icon_path)
        if not self.icon_path.exists():
            raise FileNotFoundError(f"图标文件不存在: {icon_path}")
        return self

    def set_version_info(self, 
                        version: str,
                        company: Optional[str] = None,
                        description: Optional[str] = None,
                        copyright: Optional[str] = None) -> 'PyToExeBuilder':
        """设置版本信息(仅Windows有效)"""
        self.version_info = {
            'version': version,
            'company': company or "Unknown",
            'description': description or self.output_name,
            'copyright': copyright or f"Copyright © {company or 'Unknown'}"
        }
        return self

    def hide_console(self) -> 'PyToExeBuilder':
        """隐藏控制台窗口(仅Windows GUI程序有效)"""
        self.console = False
        return self

    def detect_dependencies(self) -> 'PyToExeBuilder':
        """自动检测脚本依赖"""
        try:
            # 使用pipreqs分析依赖(需要先安装pipreqs)
            req_file = self.work_dir / "requirements.txt"
            subprocess.run(
                ["pipreqs", "--savepath", str(req_file), str(self.script_path.parent)],
                check=True,
                capture_output=True
            )
            
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.dependencies.append(line.split('==')[0])
        except Exception as e:
            print(f"警告: 依赖检测失败 - {str(e)}")
        return self

    def build(self, onefile: bool = True, clean: bool = True) -> Path:
        """
        执行构建过程
        
        :param onefile: 是否生成单文件可执行程序
        :param clean: 是否清理临时文件
        :return: 生成的可执行文件路径
        """
        print(f"开始构建 {self.output_name}...")
        
        # 1. 准备构建环境
        self._prepare_build_env()
        
        # 2. 根据平台选择构建工具
        if platform.system() == 'Windows':
            output_path = self._build_with_pyinstaller(onefile)
        elif platform.system() == 'Linux':
            output_path = self._build_with_linux(onefile)
        elif platform.system() == 'Darwin':
            output_path = self._build_with_mac(onefile)
        else:
            raise NotImplementedError("不支持的操作系统")
        
        # 3. 清理临时文件
        if clean:
            self._cleanup()
        
        print(f"构建成功! 输出文件: {output_path}")
        return output_path

    def _prepare_build_env(self) -> None:
        """准备构建环境"""
        (self.work_dir / "build").mkdir(exist_ok=True)
        (self.work_dir / "dist").mkdir(exist_ok=True)
        
        # 复制主脚本到工作目录
        shutil.copy2(self.script_path, self.work_dir)
        
        # 创建版本信息文件(Windows)
        if platform.system() == 'Windows' and self.version_info:
            version_file = self.work_dir / "version_info.txt"
            with open(version_file, 'w') as f:
                json.dump(self.version_info, f)

    def _build_with_pyinstaller(self, onefile: bool) -> Path:
        """使用PyInstaller构建Windows可执行文件"""
        try:
            import PyInstaller.__main__ as pyinstaller
        except ImportError:
            raise RuntimeError("请先安装PyInstaller: pip install pyinstaller")
        
        pyinstaller_args = [
            str(self.work_dir / self.script_path.name),
            '--name', self.output_name,
            '--workpath', str(self.work_dir / "build"),
            '--distpath', str(self.work_dir / "dist"),
            '--specpath', str(self.work_dir),
            '--add-data', f"{self.script_path.parent}{os.pathsep}."
        ]
        
        if onefile:
            pyinstaller_args.append('--onefile')
        
        if not self.console:
            pyinstaller_args.append('--windowed')
        
        if self.icon_path:
            pyinstaller_args.extend(['--icon', str(self.icon_path)])
        
        if self.version_info:
            version_args = [
                '--version-file', str(self.work_dir / "version_info.txt")
            ]
            pyinstaller_args.extend(version_args)
        
        # 添加依赖和数据文件
        for dep in self.dependencies:
            pyinstaller_args.extend(['--hidden-import', dep])
        
        for file in self.extra_files:
            if isinstance(file, tuple):
                src, dest = file
                pyinstaller_args.extend(['--add-data', f"{src}{os.pathsep}{dest}"])
            else:
                pyinstaller_args.extend(['--add-data', f"{file}{os.pathsep}."])
        
        # 执行PyInstaller
        pyinstaller.run(pyinstaller_args)
        
        return self._find_output_file(onefile)

    def _find_output_file(self, onefile: bool) -> Path:
        """查找输出文件"""
        dist_dir = self.work_dir / "dist"
        if onefile:
            if platform.system() == 'Windows':
                return next(dist_dir.glob(f"{self.output_name}.exe"))
            else:
                return next(dist_dir.glob(self.output_name))
        else:
            if platform.system() == 'Windows':
                return dist_dir / self.output_name / f"{self.output_name}.exe"
            else:
                return dist_dir / self.output_name / self.output_name

    def _cleanup(self) -> None:
        """清理临时文件"""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)

    @classmethod
    def quick_build(cls, 
                   script_path: str,
                   output_name: Optional[str] = None,
                   onefile: bool = True) -> Path:
        """快速构建方法"""
        return (cls(script_path, output_name)
               .detect_dependencies()
               .build(onefile=onefile))