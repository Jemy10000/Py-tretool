import chardet
from typing import Any, Union, Dict, List, BinaryIO

class JSONEncodeError(Exception):
    """JSON 编码异常"""
    pass

class JSONDecodeError(Exception):
    """JSON 解码异常"""
    pass

def dump_to_str(obj: Any, indent: Union[int, None] = None) -> str:
    """
    将 Python 对象转换为 JSON 字符串
    
    参数：
        obj: 要序列化的 Python 对象
        indent: 缩进空格数（None 表示紧凑格式）
    
    返回：
        JSON 格式字符串
    
    异常：
        JSONEncodeError: 当遇到不可序列化的对象时
    """
    if indent is not None and not isinstance(indent, int):
        raise TypeError("indent must be int or None")
    
    return _Encoder(indent).encode(obj)

def load_from_str(json_str: str) -> Any:
    """
    将 JSON 字符串解析为 Python 对象
    
    参数：
        json_str: JSON 格式字符串
    
    返回：
        对应的 Python 对象
    
    异常：
        JSONDecodeError: 当 JSON 格式无效时
    """
    parser = _Parser(json_str)
    return parser.parse()

class _Encoder:
    """JSON 编码器实现"""
    
    def __init__(self, indent: Union[int, None] = None):
        self.indent = indent
        self._current_indent = 0
    
    def encode(self, obj: Any) -> str:
        if obj is None:
            return "null"
        elif isinstance(obj, bool):
            return "true" if obj else "false"
        elif isinstance(obj, (int, float)):
            return self._encode_number(obj)
        elif isinstance(obj, str):
            return self._encode_string(obj)
        elif isinstance(obj, (list, tuple)):
            return self._encode_array(obj)
        elif isinstance(obj, dict):
            return self._encode_object(obj)
        else:
            raise JSONEncodeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def _encode_number(self, num: Union[int, float]) -> str:
        if isinstance(num, int):
            return str(num)
        elif num.is_integer():
            return str(int(num))
        else:
            return str(num)
    
    def _encode_string(self, s: str) -> str:
        escape_map = {
            '\"': '\\"',
            '\\': '\\\\',
            '\b': '\\b',
            '\f': '\\f',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
        }
        
        result = []
        for char in s:
            if char in escape_map:
                result.append(escape_map[char])
            elif ord(char) < 0x20:
                result.append(f"\\u{ord(char):04x}")
            else:
                result.append(char)
        
        return f'"{"".join(result)}"'
    
    def _encode_array(self, array: List[Any]) -> str:
        if not array:
            return "[]"
        
        if self.indent is None:
            items = [self.encode(item) for item in array]
            return f"[{','.join(items)}]"
        else:
            self._current_indent += self.indent
            indent_str = "\n" + " " * self._current_indent
            items = [f"{indent_str}{self.encode(item)}" for item in array]
            self._current_indent -= self.indent
            return f"[{','.join(items)}\n{' ' * self._current_indent}]"
    
    def _encode_object(self, obj: Dict[str, Any]) -> str:
        if not obj:
            return "{}"
        
        if self.indent is None:
            items = [f"{self.encode(k)}:{self.encode(v)}" for k, v in obj.items()]
            return f"{{{','.join(items)}}}"
        else:
            self._current_indent += self.indent
            indent_str = "\n" + " " * self._current_indent
            items = []
            for k, v in obj.items():
                key_str = self.encode(k)
                value_str = self.encode(v)
                items.append(f"{indent_str}{key_str}: {value_str}")
            self._current_indent -= self.indent
            return f"{{{','.join(items)}\n{' ' * self._current_indent}}}"

class _Parser:
    """JSON 解析器实现"""
    
    def __init__(self, json_str: str):
        self.json_str = json_str.strip()
        self.idx = 0
        self.len = len(json_str)
    
    def parse(self) -> Any:
        char = self._peek()
        
        if char == '{':
            return self._parse_object()
        elif char == '[':
            return self._parse_array()
        elif char == '"':
            return self._parse_string()
        elif char == 'n' and self._peek_next(4) == 'null':
            self.idx += 4
            return None
        elif char == 't' and self._peek_next(4) == 'true':
            self.idx += 4
            return True
        elif char == 'f' and self._peek_next(5) == 'false':
            self.idx += 5
            return False
        elif char == '-' or char.isdigit():
            return self._parse_number()
        else:
            raise JSONDecodeError(f"Unexpected character at position {self.idx}: {char}")
    
    def _parse_object(self) -> Dict[str, Any]:
        obj = {}
        self._consume('{')
        
        while self._peek() != '}':
            # 解析键
            key = self._parse_string()
            self._consume(':')
            
            # 解析值
            value = self.parse()
            obj[key] = value
            
            # 处理逗号或结束
            if self._peek() == ',':
                self._consume(',')
            elif self._peek() != '}':
                raise JSONDecodeError("Expected ',' or '}' after object pair")
        
        self._consume('}')
        return obj
    
    def _parse_array(self) -> List[Any]:
        arr = []
        self._consume('[')
        
        while self._peek() != ']':
            # 解析元素
            arr.append(self.parse())
            
            # 处理逗号或结束
            if self._peek() == ',':
                self._consume(',')
            elif self._peek() != ']':
                raise JSONDecodeError("Expected ',' or ']' after array element")
        
        self._consume(']')
        return arr
    
    def _parse_string(self) -> str:
        self._consume('"')
        chars = []
        
        while self._peek() != '"':
            char = self._peek()
            
            if char == '\\':
                self._consume('\\')
                esc_char = self._peek()
                if esc_char == 'u':
                    # Unicode 转义
                    self._consume('u')
                    hex_str = self.json_str[self.idx:self.idx+4]
                    if len(hex_str) != 4:
                        raise JSONDecodeError("Invalid Unicode escape sequence")
                    self.idx += 4
                    chars.append(chr(int(hex_str, 16)))
                else:
                    # 简单转义字符
                    escape_map = {
                        '"': '"',
                        '\\': '\\',
                        '/': '/',
                        'b': '\b',
                        'f': '\f',
                        'n': '\n',
                        'r': '\r',
                        't': '\t',
                    }
                    chars.append(escape_map.get(esc_char, esc_char))
                    self._consume(esc_char)
            else:
                chars.append(char)
                self._consume(char)
        
        self._consume('"')
        return ''.join(chars)
    
    def _parse_number(self) -> Union[int, float]:
        start_idx = self.idx
        is_float = False
        
        # 处理符号
        if self._peek() == '-':
            self._consume('-')
        
        # 整数部分
        while self._peek().isdigit():
            self._consume()
        
        # 小数部分
        if self._peek() == '.':
            is_float = True
            self._consume('.')
            while self._peek().isdigit():
                self._consume()
        
        # 指数部分
        if self._peek().lower() == 'e':
            is_float = True
            self._consume()
            if self._peek() in ('+', '-'):
                self._consume()
            while self._peek().isdigit():
                self._consume()
        
        num_str = self.json_str[start_idx:self.idx]
        try:
            return float(num_str) if is_float else int(num_str)
        except ValueError:
            raise JSONDecodeError(f"Invalid number literal: {num_str}")
    
    def _peek(self) -> str:
        if self.idx >= self.len:
            raise JSONDecodeError("Unexpected end of JSON input")
        return self.json_str[self.idx]
    
    def _peek_next(self, n: int) -> str:
        if self.idx + n > self.len:
            raise JSONDecodeError("Unexpected end of JSON input")
        return self.json_str[self.idx:self.idx+n]
    
    def _consume(self, expected: str = None):
        if expected is not None and self._peek() != expected:
            raise JSONDecodeError(f"Expected '{expected}' at position {self.idx}")
        self.idx += 1

# 简化版接口
def dump_to_file(obj: Any, filepath: str, indent: Union[int, None] = 4, encoding:str='utf-8'):
    """将 Python 对象序列化为 JSON 格式并写入文件"""
    with open(filepath, 'w', encoding=encoding) as file:
        file.write(dump_to_str(obj, indent))

def load_from_file(filepath:str, encoding:str='utf-8'):
    """从文件读取 JSON 数据并解析为 Python 对象"""
    with open(filepath, 'r', encoding=encoding) as file:
        return load_from_str(file.read())