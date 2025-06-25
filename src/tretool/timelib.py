import re
import sys
import ctypes

from typing import overload, Literal

class SYSTEMTIME(ctypes.Structure):
    _fields_ = [
        ("wYear", ctypes.c_ushort),
        ("wMonth", ctypes.c_ushort),
        ("wDayOfWeek", ctypes.c_ushort),
        ("wDay", ctypes.c_ushort),
        ("wHour", ctypes.c_ushort),
        ("wMinute", ctypes.c_ushort),
        ("wSecond", ctypes.c_ushort),
        ("wMilliseconds", ctypes.c_ushort),
    ]


def get_timestamp():
    """返回毫秒级时间戳（跨平台）"""
    if sys.platform == "win32":
        # Windows 使用 GetSystemTimeAsFileTime
        libc = ctypes.windll.kernel32
        filetime = ctypes.c_uint64()
        libc.GetSystemTimeAsFileTime(ctypes.byref(filetime))
        return (filetime.value - 116444736000000000) // 10000  # 转毫秒
    else:
        # Unix 使用 gettimeofday
        class Timeval(ctypes.Structure):
            _fields_ = [("tv_sec", ctypes.c_long), ("tv_usec", ctypes.c_long)]
        libc = ctypes.CDLL(None)
        tv = Timeval()
        libc.gettimeofday(ctypes.byref(tv), None)
        return tv.tv_sec * 1000 + tv.tv_usec // 1000  # 毫秒


def get_now_by_fmt(fmt: str = '%YYYY-%mm-%dd %HH:%MM:%SS.%fff') -> str:
    """
    获取当前时间（支持自定义格式，包含毫秒），仅适用于 Windows
    支持的格式符：
        %Y / %YYYY - 年（4位）
        %YY - 年（2位）
        %m / %mm - 月（01-12）
        %d / %dd - 日（01-31）
        %H / %HH - 时（00-23）
        %M / %MM - 分（00-59）
        %S / %SS - 秒（00-59）
        %f / %ff / %fff - 毫秒（1-3位）
    """
    kernel32 = ctypes.windll.kernel32
    time = SYSTEMTIME()
    kernel32.GetLocalTime(ctypes.byref(time))

    # 替换格式化字符串（按长度从长到短处理，避免替换冲突）
    formatted = fmt
    replacements = [
        ("%YYYY", f"{time.wYear:04d}"),
        ("%YYY", f"{time.wYear % 1000:03d}"),
        ("%YY", f"{time.wYear % 100:02d}"),
        ("%Y", f"{time.wYear:01d}"),
        ("%mm", f"{time.wMonth:02d}"),
        ("%m", f"{time.wMonth:01d}"),
        ("%dd", f"{time.wDay:02d}"),
        ("%d", f"{time.wDay:01d}"),
        ("%HH", f"{time.wHour:02d}"),
        ("%H", f"{time.wHour:01d}"),
        ("%MM", f"{time.wMinute:02d}"),
        ("%M", f"{time.wMinute:01d}"),
        ("%SS", f"{time.wSecond:02d}"),
        ("%S", f"{time.wSecond:01d}"),
        ("%fff", f"{time.wMilliseconds:03d}"),
        ("%ff", f"{time.wMilliseconds // 10:02d}"),
        ("%f", f"{time.wMilliseconds // 100:01d}")
    ]
    
    for pattern, replacement in replacements:
        formatted = formatted.replace(pattern, replacement)

    return formatted


def get_now_by_systemtime(
    wYear: bool = True,
    wMonth: bool = True,
    wDay: bool = True,
    wHour: bool = True,
    wMinute: bool = True,
    wSecond: bool = True,
    wMilliseconds: bool = True
) -> SYSTEMTIME:
    """
    获取当前时间的 SYSTEMTIME 对象（可选字段）\n
    参数：
        参数：指定需要包含的字段
    返回：
        SYSTEMTIME 结构体
    """
    kernel32 = ctypes.windll.kernel32
    time = SYSTEMTIME()
    kernel32.GetLocalTime(ctypes.byref(time))
    
    result = SYSTEMTIME()
    if wYear: result.wYear = time.wYear
    if wMonth: result.wMonth = time.wMonth
    if wDay: result.wDay = time.wDay
    if wHour: result.wHour = time.wHour
    if wMinute: result.wMinute = time.wMinute
    if wSecond: result.wSecond = time.wSecond
    if wMilliseconds: result.wMilliseconds = time.wMilliseconds
    return result


def parse_time_systemtime(time_str: str, fmt: str) -> SYSTEMTIME:
    """
    将时间字符串解析为 SYSTEMTIME 结构（支持毫秒）
    
    参数：
        time_str: 时间字符串
        fmt: 格式字符串
    
    返回：
        SYSTEMTIME 结构体（包含毫秒）
    
    异常：
        ValueError: 当时间字符串与格式不匹配或包含无效值时
    """
    time = SYSTEMTIME()
    
    # 初始化默认值
    time.wYear = 0
    time.wMonth = 1
    time.wDay = 1
    time.wHour = 0
    time.wMinute = 0
    time.wSecond = 0
    time.wMilliseconds = 0

    # 构建正则表达式模式（添加毫秒支持）
    format_patterns = {
        '%YYYY': r'(?P<year>\d{4})',
        '%Y': r'(?P<year>\d{1,4})',
        '%yy': r'(?P<year>\d{2})',
        '%y': r'(?P<year>\d{1,2})',
        '%mm': r'(?P<month>0[1-9]|1[0-2])',
        '%m': r'(?P<month>[1-9]|1[0-2])',
        '%dd': r'(?P<day>0[1-9]|[12]\d|3[01])',
        '%d': r'(?P<day>[1-9]|[12]\d|3[01])',
        '%HH': r'(?P<hour>[01]\d|2[0-3])',
        '%H': r'(?P<hour>\d|1\d|2[0-3])',
        '%MM': r'(?P<minute>[0-5]\d)',
        '%M': r'(?P<minute>\d|[0-5]\d)',
        '%SS': r'(?P<second>[0-5]\d)',
        '%S': r'(?P<second>\d|[0-5]\d)',
        '%fff': r'(?P<millis>\d{3})',
        '%ff': r'(?P<millis>\d{2})',
        '%f': r'(?P<millis>\d{1})'
    }

    # 转义fmt中的特殊字符，但保留格式说明符
    pattern = re.escape(fmt)
    for fmt_code, regex in format_patterns.items():
        pattern = pattern.replace(re.escape(fmt_code), regex)

    # 匹配时间字符串
    match = re.fullmatch(pattern, time_str)
    if not match:
        raise ValueError(f"时间字符串 '{time_str}' 与格式 '{fmt}' 不匹配")

    # 提取并验证各字段
    groups = match.groupdict()
    
    try:
        if 'year' in groups and groups['year']:
            year = int(groups['year'])
            if year < 0 or year > 9999:
                raise ValueError("年份必须在0-9999范围内")
            if len(groups['year']) <= 2:  # 2位年份处理
                current_year = get_now_by_fmt("%YYYY")
                century = int(current_year[:2]) * 100
                year = century + year
                if year > int(current_year) + 50:  # 处理跨世纪
                    year -= 100
            time.wYear = year

        if 'month' in groups and groups['month']:
            month = int(groups['month'])
            if not 1 <= month <= 12:
                raise ValueError("月份必须在1-12范围内")
            time.wMonth = month

        if 'day' in groups and groups['day']:
            day = int(groups['day'])
            max_day = days_in_month(time.wYear, time.wMonth)
            if not 1 <= day <= max_day:
                raise ValueError(f"日期无效，{time.wYear}年{time.wMonth}月最多有{max_day}天")
            time.wDay = day

        if 'hour' in groups and groups['hour']:
            hour = int(groups['hour'])
            if not 0 <= hour <= 23:
                raise ValueError("小时必须在0-23范围内")
            time.wHour = hour

        if 'minute' in groups and groups['minute']:
            minute = int(groups['minute'])
            if not 0 <= minute <= 59:
                raise ValueError("分钟必须在0-59范围内")
            time.wMinute = minute

        if 'second' in groups and groups['second']:
            second = int(groups['second'])
            if not 0 <= second <= 59:
                raise ValueError("秒数必须在0-59范围内")
            time.wSecond = second

        if 'millis' in groups and groups['millis']:
            millis = int(groups['millis'])
            # 根据格式长度调整毫秒值
            if fmt.count('f') == 1:  # %f
                millis *= 100
            elif fmt.count('f') == 2:  # %ff
                millis *= 10
            if not 0 <= millis <= 999:
                raise ValueError("毫秒必须在0-999范围内")
            time.wMilliseconds = millis

    except ValueError as e:
        raise ValueError(f"无效的时间值: {e}") from e

    return time


def is_leap_year(year: int) -> bool:
    """判断是否为闰年"""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """返回某年某月的天数"""
    if month > 12:
        raise ValueError('月份不能大于12')
    if month == 2:
        return 29 if is_leap_year(year) else 28
    elif month in [4, 6, 9, 11]:
        return 30
    else:
        return 31


@overload
def sub_time(start: str, end: str, fmt: str = "%YYYY-%mm-%dd %HH:%MM:%SS.%fff") -> dict:
    """
    计算两个时间的差值（考虑月份、闰年、时间进位）
    返回格式：{"days": X, "hours": X, "minutes": X, "seconds": X, "ms": X}
    """
    ...

@overload
def sub_time(start: str, end: SYSTEMTIME, fmt: str = "%YYYY-%mm-%dd %HH:%MM:%SS.%fff") -> dict:
    """
    计算两个时间的差值（考虑月份、闰年、时间进位）
    返回格式：{"days": X, "hours": X, "minutes": X, "seconds": X, "ms": X}
    """
    ...

@overload
def sub_time(start: SYSTEMTIME, end: str, fmt: str = "%YYYY-%mm-%dd %HH:%MM:%SS.%fff") -> dict:
    """
    计算两个时间的差值（考虑月份、闰年、时间进位）
    返回格式：{"days": X, "hours": X, "minutes": X, "seconds": X, "ms": X}
    """
    ...

@overload
def sub_time(start: SYSTEMTIME, end: SYSTEMTIME, fmt: str = "%YYYY-%mm-%dd %HH:%MM:%SS.%fff") -> dict:
    """
    计算两个时间的差值（考虑月份、闰年、时间进位）
    返回格式：{"days": X, "hours": X, "minutes": X, "seconds": X, "ms": X}
    """
    ...

def sub_time(start: str|SYSTEMTIME, end: str|SYSTEMTIME, fmt: str = "%YYYY-%mm-%dd %HH:%MM:%SS.%fff") -> dict:
    """
    计算两个时间的差值（考虑月份、闰年、时间进位）
    返回格式：{"days": X, "hours": X, "minutes": X, "seconds": X, "ms": X}
    """
    if isinstance(start, str):
        start_time = parse_time_systemtime(start, fmt)
    else:
        start_time = start
    
    if isinstance(end, str):
        end_time = parse_time_systemtime(end, fmt)
    else:
        end_time = end

    # 计算总毫秒数差
    total_ms = 0

    # 计算年份差（转换为天数）
    for year in range(start_time.wYear, end_time.wYear):
        total_ms += (366 if is_leap_year(year) else 365) * 86400 * 1000

    # 计算月份差（转换为天数）
    if end_time.wYear == start_time.wYear:
        month_range = range(start_time.wMonth, end_time.wMonth)
    else:
        month_range = list(range(start_time.wMonth, 13)) + list(range(1, end_time.wMonth))
    
    for month in month_range:
        year = start_time.wYear if month >= start_time.wMonth else end_time.wYear
        total_ms += days_in_month(year, month) * 86400 * 1000

    # 计算天数差
    total_ms += (end_time.wDay - start_time.wDay) * 86400 * 1000

    # 计算时、分、秒差
    total_ms += (end_time.wHour - start_time.wHour) * 3600 * 1000
    total_ms += (end_time.wMinute - start_time.wMinute) * 60 * 1000
    total_ms += (end_time.wSecond - start_time.wSecond) * 1000
    total_ms += (end_time.wMilliseconds - start_time.wMilliseconds)

    # 转换为天数、小时、分钟、秒、毫秒
    days = total_ms // (86400 * 1000)
    remaining_ms = total_ms % (86400 * 1000)
    hours = remaining_ms // (3600 * 1000)
    remaining_ms %= (3600 * 1000)
    minutes = remaining_ms // (60 * 1000)
    remaining_ms %= (60 * 1000)
    seconds = remaining_ms // 1000
    ms = remaining_ms % 1000

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "ms": ms
    }


def sleep(duration: int | float, unit: Literal["minutes", "seconds", "milliseconds"] = "seconds") -> None:
    """
    实现精确休眠，仅适用于Windows\n
    参数：
        duration: 时间长度
        unit: 时间单位（"minutes"/"seconds"/"milliseconds"）
    """
    kernel32 = ctypes.windll.kernel32
    
    # 根据单位转换为毫秒
    if unit == "minutes":
        ms = int(duration * 60 * 1000)
    elif unit == "seconds":
        ms = int(duration * 1000)
    else:  # milliseconds
        ms = int(duration)
    
    kernel32.Sleep(ms)


class Counter:
    def __init__(self, default_count: int = 0):
        """
        计数器类
        
        参数：
            default_count: 初始计数值，默认为0
        """
        self.count = default_count

    def add(self, value: int = 1) -> None:
        """
        增加计数值
        
        参数：
            value: 要增加的值，默认为1
        """
        self.count += value

    def reset(self, new_value: int = 0) -> None:
        """
        重置计数器
        
        参数：
            new_value: 重置后的值，默认为0
        """
        self.count = new_value

    def __call__(self, add_value: int = 1) -> None:
        """
        使实例可调用，等同于add()方法
        
        参数：
            add_value: 要增加的值，默认为1
        """
        self.add(add_value)

    def __eq__(self, other) -> bool:
        """
        比较两个计数器的值
        
        参数：
            other: 可以是Counter实例或整数
        """
        if isinstance(other, Counter):
            return self.count == other.count
        elif isinstance(other, int):
            return self.count == other
        return NotImplemented

    def __str__(self) -> str:
        """
        字符串表示
        """
        return f"Counter: var count is {self.count}"

    def __repr__(self) -> str:
        """
        官方字符串表示
        """
        return f"Counter(count={self.count})"
    
    def __hash__(self):
        return hash(f'Counter(count={self.count})')
        
    def __ne__(self, other):
        if isinstance(other, Counter):
            return self.count != other.count
        elif isinstance(other, int):
            return self.count != other
        return NotImplemented

    def __add__(self, value) -> 'Counter':
        self.count += value
        return self

    def __sub__(self, value: int) -> 'Counter':
        self.count -= value
        return self

    @property
    def value(self) -> int:
        """
        获取当前计数值
        """
        return self.count


class Timer:
    def __init__(self, auto_start=False):
        """
        初始化计时器\n
        :param auto_start: 是否自动开始计时（默认False）
        """
        self.start_time = 0
        self.end_time = 0
        self.time_sub = 0
        if auto_start:
            self.start_timer()


    def __repr__(self):
        """返回可用于重新创建对象的官方字符串表示"""
        return (f"Timer(start_time={self.start_time}, "
                f"end_time={self.end_time}, "
                f"elapsed={self.elapsed_time()})")


    def __str__(self):
        """返回用户友好的字符串表示"""
        status = "运行中" if self.end_time == 0 and self.start_time != 0 else "已停止"
        return (f"计时器状态: {status}\n"
                f"开始时间: {self.start_time}\n"
                f"结束时间: {self.end_time}\n"
                f"已耗时: {self.elapsed_time()}秒")


    def start_timer(self):
        """启动/重启计时器"""
        self.reset()
        self.start_time = get_timestamp()
        return self.start_time


    def end_timer(self):
        """停止计时器"""
        if self.start_time == 0:
            raise RuntimeError("计时器尚未启动")
        self.end_time = get_timestamp()
        return self.end_time


    def elapsed_time(self):
        """获取当前耗时（自动处理未停止情况）"""
        if self.start_time == 0:
            return 0
        current_end = self.end_time if self.end_time != 0 else get_timestamp()
        self.time_sub = current_end - self.start_time
        return self.time_sub


    def end_get_time(self):
        """停止计时并返回最终耗时"""
        if self.start_time == 0:
            raise RuntimeError("计时器未启动")
        if self.end_time == 0:
            self.end_timer()
        return self.time_sub
    

    def reset(self):
        """完全重置计时器"""
        self.start_time = 0
        self.end_time = 0
        self.time_sub = 0

