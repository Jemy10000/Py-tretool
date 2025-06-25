import sys
import datetime
import traceback

from typing import Tuple

class LogWriter:
    def __init__(self) -> None:
        self.log = []


    def save_file(self, filepath:str) -> Tuple[bool, str]:
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write('\n'.join(self.log))
            return (True, 'No error')
        except Exception as e:
            return (False, str(e))
    

    def write_debug(self, content:str, user:str='root', time:str=None):
        if time is None:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log.append(f'[{time}] (debug) {user}: {content}')


    def write_info(self, content:str, user:str='root', time:str=None):
        if time is None:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log.append(f'[{time}] (info) {user}: {content}')

    
    def write_warning(self, content:str, user:str='root', time:str=None):
        if time is None:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log.append(f'[{time}] (warning) {user}: {content}')

    
    def write_error(self, content:str, user:str='root', time:str=None):
        if time is None:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.log.append(f'[{time}] (error) {user}: {content}')


    def write_traceback(self, user: str = 'root', time: str = None):
        """捕获当前异常信息并写入日志"""
        if time is None:
            time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取当前异常信息
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is None:  # 如果没有异常，直接返回
            return
        
        # 格式化 traceback 信息
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        tb_content = ''.join(tb_lines).strip()  # 将 traceback 转为字符串
        
        # 写入日志
        self.log.append(f'[{time}] {user}: [EXCEPTION]\n{tb_content}')

    
    @property
    def log_content(self):
        return self.log