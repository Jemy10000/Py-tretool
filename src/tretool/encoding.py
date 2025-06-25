import chardet

from typing import Union, BinaryIO

def detect_encoding(
    input_data: Union[bytes, str, BinaryIO],
    sample_size: int = 1024,
    fallback_encoding: str = 'utf-8'
) -> str:
    """
    自动检测文本数据的字符编码
    
    参数：
        input_data: 可以是以下类型之一：
                   - bytes: 原始字节数据
                   - str: 字符串（将尝试重新编码检测）
                   - BinaryIO: 文件对象（将读取前sample_size字节）
        sample_size: 从文件/大数据中采样的字节数（默认1024）
        fallback_encoding: 无法检测时使用的回退编码（默认'utf-8'）
    
    返回：
        检测到的编码名称字符串
    
    示例：
        # 检测字节数据编码
        detect_encoding(b'\xc3\xa9chantillon')
        
        # 检测文件编码
        with open('file.txt', 'rb') as f:
            encoding = detect_encoding(f)
    """
    raw_data = _get_sample_data(input_data, sample_size)
    
    if not raw_data:
        return fallback_encoding
    
    try:
        # 使用chardet进行编码检测
        result = chardet.detect(raw_data)
        confidence = result['confidence']
        encoding = result['encoding'].lower()
        
        # 验证检测结果
        if confidence > 0.9:
            return encoding
        if confidence > 0.7 and validate_encoding(raw_data, encoding):
            return encoding
        
        # 尝试常见编码验证
        for enc in ['utf-8', 'latin-1', 'gbk', 'gb2312', 'big5']:
            if validate_encoding(raw_data, enc):
                return enc
                
    except Exception:
        pass
    
    return fallback_encoding


def _get_sample_data(
    input_data: Union[bytes, str, BinaryIO],
    sample_size: int
) -> bytes:
    """获取用于检测的样本数据"""
    if isinstance(input_data, bytes):
        return input_data[:sample_size]
    
    if isinstance(input_data, str):
        try:
            return input_data.encode('latin-1', errors='ignore')[:sample_size]
        except:
            return b''
    
    if hasattr(input_data, 'read'):
        try:
            pos = input_data.tell()
            data = input_data.read(sample_size)
            input_data.seek(pos)  # 重置文件指针
            return data if isinstance(data, bytes) else b''
        except:
            return b''
    
    return b''


def validate_encoding(data: bytes, encoding: str) -> bool:
    """验证编码是否有效"""
    try:
        data.decode(encoding, errors='strict')
        return True
    except:
        return False