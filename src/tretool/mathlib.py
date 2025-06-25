"""
PurePythonMath - 纯Python实现的完整数学函数库
包含所有基础数学运算、三角函数、双曲函数、指数对数函数、特殊函数等
"""

from typing import Union, Tuple, Optional
from decimal import Decimal, getcontext, Context
import sys
import itertools

# ==================== 类型定义 ====================
AnyNum = Union[int, float, Decimal]
PrecisionType = Union[int, float, Decimal, None]

# ==================== 常数定义 ====================
PI = Decimal('3.14159265358979323846264338327950288419716939937510')
E = Decimal('2.71828182845904523536028747135266249775724709369995')
INF = float('inf')
NAN = float('nan')
PHI = Decimal('1.61803398874989484820458683436563811772030917980576')  # 黄金比例
GAMMA = Decimal('0.57721566490153286060651209008240243104215933593992')  # 欧拉-马歇罗尼常数

# ==================== 配置管理 ====================
class MathConfig:
    _precision = 15
    _rounding = 'ROUND_HALF_EVEN'

    @classmethod
    def set_precision(cls, prec: int):
        """设置全局计算精度（小数位数）"""
        cls._precision = prec
        getcontext().prec = prec + 2  # Decimal保留额外位数

    @classmethod
    def set_rounding(cls, mode: str):
        """设置舍入模式（同Decimal模块）"""
        cls._rounding = mode
        getcontext().rounding = mode

# 初始化配置
MathConfig.set_precision(15)

# ==================== 辅助函数 ====================
def _convert_to_decimal(x: AnyNum, prec: PrecisionType = None) -> Decimal:
    """将输入转换为Decimal，应用指定精度"""
    if isinstance(x, Decimal):
        return x
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    return Decimal(str(float(x))).quantize(Decimal(10) ** -ctx.prec)

def _keep_type(x: AnyNum, result: Decimal, prec: PrecisionType = None) -> AnyNum:
    """保持输入类型输出"""
    if prec is not None or isinstance(x, Decimal):
        return +result  # 应用当前精度
    return float(result)

# ==================== 基本运算 ====================
def sqrt(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """平方根（牛顿迭代法）"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_sqrt(x, prec)
    
    if x < 0:
        raise ValueError("math domain error")
    if x == 0:
        return 0.0
    
    guess = max(float(x), 1)
    while True:
        new_guess = (guess + x / guess) / 2
        if abs(new_guess - guess) < 1e-15:
            return new_guess
        guess = new_guess

def _decimal_sqrt(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版平方根"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    if x < 0:
        raise ValueError("math domain error")
    if x == 0:
        return Decimal(0)
    
    guess = max(x, Decimal(1))
    while True:
        new_guess = (guess + x / guess) / 2
        if abs(new_guess - guess) < Decimal(10) ** (-ctx.prec + 1):
            return +new_guess
        guess = new_guess

def power(base: AnyNum, exponent: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """幂运算 base^exponent"""
    if isinstance(base, Decimal) or isinstance(exponent, Decimal) or prec is not None:
        return _decimal_power(base, exponent, prec)
    
    if isinstance(exponent, int):
        return _int_power(base, exponent)
    else:
        return exp(exponent * ln(base))

def _decimal_power(base: AnyNum, exponent: AnyNum, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版幂运算"""
    base_dec = _convert_to_decimal(base, prec)
    exponent_dec = _convert_to_decimal(exponent, prec)
    
    if exponent_dec == 0:
        return Decimal(1)
    if base_dec == 0:
        if exponent_dec < 0:
            raise ValueError("0 cannot be raised to a negative power")
        return Decimal(0)
    
    return _decimal_exp(exponent_dec * _decimal_ln(base_dec, prec), prec)

def _int_power(base: AnyNum, n: int) -> AnyNum:
    """快速幂算法（仅整数指数）"""
    if n == 0:
        return type(base)(1)
    if n < 0:
        return 1 / _int_power(base, -n)
    
    result = type(base)(1)
    while n > 0:
        if n % 2 == 1:
            result *= base
        base *= base
        n //= 2
    return result

# ==================== 指数对数函数 ====================
def exp(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """指数函数 e^x"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_exp(x, prec)
    
    result = 1.0
    term = 1.0
    for n in range(1, 100):
        term *= x / n
        result += term
        if abs(term) < 1e-15:
            break
    return result

def _decimal_exp(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版指数函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    result = Decimal(1)
    term = Decimal(1)
    n = 1
    
    while True:
        term *= x / Decimal(n)
        result += term
        if abs(term) < Decimal(10) ** (-ctx.prec + 1):
            return +result
        n += 1

def ln(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """自然对数 ln(x)"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_ln(x, prec)
    
    if x <= 0:
        raise ValueError("math domain error")
    
    # 调整x到收敛区间(0.5, 2)
    n = 0
    while x > 2:
        x /= float(E)
        n += 1
    while x < 0.5:
        x *= float(E)
        n -= 1
    
    # 泰勒展开
    x -= 1
    result = 0.0
    sign = 1
    for k in range(1, 100):
        term = sign * (x ** k) / k
        result += term
        sign *= -1
        if abs(term) < 1e-15:
            break
    return result + n

def _decimal_ln(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版自然对数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    if x <= 0:
        raise ValueError("math domain error")
    
    n = 0
    while x > 2:
        x /= E
        n += 1
    while x < Decimal('0.5'):
        x *= E
        n -= 1
    
    x -= Decimal(1)
    result = Decimal(0)
    sign = Decimal(1)
    for k in range(1, ctx.prec * 2):
        term = sign * (x ** k) / k
        result += term
        sign *= -1
        if abs(term) < Decimal(10) ** (-ctx.prec + 1):
            break
    return +(result + n)

def log(base: AnyNum, x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """对数函数 logₐ(x)"""
    if base <= 0 or base == 1 or x <= 0:
        raise ValueError("math domain error")
    
    if isinstance(base, Decimal) or isinstance(x, Decimal) or prec is not None:
        base_dec = _convert_to_decimal(base, prec)
        x_dec = _convert_to_decimal(x, prec)
        return _decimal_ln(x_dec, prec) / _decimal_ln(base_dec, prec)
    
    return ln(x) / ln(base)

# ==================== 三角函数 ====================
def sin(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """正弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_sin(x, prec)
    
    x = x % (2 * float(PI))
    if x > float(PI):
        x -= 2 * float(PI)
    
    result = 0.0
    term = x
    n = 1
    for _ in range(100):
        result += term
        term *= -x * x / ((2 * n) * (2 * n + 1))
        if abs(term) < 1e-15:
            break
        n += 1
    return result

def _decimal_sin(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版正弦函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    x = x % (2 * PI)
    if x > PI:
        x -= 2 * PI
    
    result = Decimal(0)
    term = x
    n = 1
    while True:
        result += term
        term *= -x * x / (Decimal(2 * n) * Decimal(2 * n + 1))
        if abs(term) < Decimal(10) ** (-ctx.prec + 1):
            break
        n += 1
    return +result

def cos(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """余弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_cos(x, prec)
    
    x = x % (2 * float(PI))
    if x > float(PI):
        x -= 2 * float(PI)
    
    result = 1.0
    term = 1.0
    n = 1
    for _ in range(100):
        term *= -x * x / ((2 * n - 1) * (2 * n))
        result += term
        if abs(term) < 1e-15:
            break
        n += 1
    return result

def _decimal_cos(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版余弦函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    x = x % (2 * PI)
    if x > PI:
        x -= 2 * PI
    
    result = Decimal(1)
    term = Decimal(1)
    n = 1
    while True:
        term *= -x * x / (Decimal(2 * n - 1) * Decimal(2 * n))
        result += term
        if abs(term) < Decimal(10) ** (-ctx.prec + 1):
            break
        n += 1
    return +result

def tan(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """正切函数"""
    if isinstance(x, Decimal) or prec is not None:
        c = _decimal_cos(x, prec)
        if abs(c) < Decimal(10) ** (-getcontext().prec + 1):
            raise ValueError("math domain error")
        return _decimal_sin(x, prec) / c
    
    c = cos(x)
    if abs(c) < 1e-10:
        raise ValueError("math domain error")
    return sin(x) / c

def cot(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """余切函数"""
    if isinstance(x, Decimal) or prec is not None:
        s = _decimal_sin(x, prec)
        if abs(s) < Decimal(10) ** (-getcontext().prec + 1):
            raise ValueError("math domain error")
        return _decimal_cos(x, prec) / s
    
    s = sin(x)
    if abs(s) < 1e-10:
        raise ValueError("math domain error")
    return cos(x) / s

# ==================== 反三角函数 ====================
def asin(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反正弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_asin(x, prec)
    
    if abs(x) > 1:
        raise ValueError("math domain error")
    if x == 1:
        return float(PI) / 2
    elif x == -1:
        return -float(PI) / 2
    
    result = float(x)
    term = float(x)
    n = 1
    while True:
        term *= (x ** 2) * (2 * n - 1) ** 2 / (2 * n * (2 * n + 1))
        new_result = result + term
        if abs(new_result - result) < 1e-15:
            break
        result = new_result
        n += 1
    return result

def _decimal_asin(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版反正弦函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    if abs(x) > 1:
        raise ValueError("math domain error")
    if x == 1:
        return PI / 2
    elif x == -1:
        return -PI / 2
    
    result = x
    term = x
    n = 1
    while True:
        term *= (x ** 2) * (Decimal(2 * n - 1) ** 2) / (Decimal(2 * n) * Decimal(2 * n + 1))
        new_result = result + term
        if abs(new_result - result) < Decimal(10) ** (-ctx.prec + 1):
            break
        result = new_result
        n += 1
    return +result

def acos(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反余弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return PI / 2 - _decimal_asin(x, prec)
    return float(PI) / 2 - asin(x)

def atan(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反正切函数"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_atan(x, prec)
    
    if x == 1:
        return float(PI) / 4
    elif x == -1:
        return -float(PI) / 4
    elif abs(x) < 1:
        # 小x用泰勒级数
        result = float(x)
        term = float(x)
        n = 1
        while True:
            term *= -x * x
            new_result = result + term / (2 * n + 1)
            if abs(new_result - result) < 1e-15:
                break
            result = new_result
            n += 1
        return result
    else:
        # 大x用恒等式 atan(x) = π/2 - atan(1/x)
        return float(PI) / 2 - atan(1 / x)

def _decimal_atan(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版反正切函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    if x == 1:
        return PI / 4
    elif x == -1:
        return -PI / 4
    elif abs(x) < 1:
        result = x
        term = x
        n = 1
        while True:
            term *= -x * x
            new_result = result + term / Decimal(2 * n + 1)
            if abs(new_result - result) < Decimal(10) ** (-ctx.prec + 1):
                break
            result = new_result
            n += 1
        return +result
    else:
        return PI / 2 - _decimal_atan(1 / x, prec)

# ==================== 双曲函数 ====================
def sinh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """双曲正弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return (_decimal_exp(x, prec) - _decimal_exp(-x, prec)) / 2
    return (exp(x) - exp(-x)) / 2

def cosh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """双曲余弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return (_decimal_exp(x, prec) + _decimal_exp(-x, prec)) / 2
    return (exp(x) + exp(-x)) / 2

def tanh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """双曲正切函数"""
    if isinstance(x, Decimal) or prec is not None:
        return sinh(x, prec) / cosh(x, prec)
    return sinh(x) / cosh(x)

def coth(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """双曲余切函数"""
    if isinstance(x, Decimal) or prec is not None:
        return cosh(x, prec) / sinh(x, prec)
    return cosh(x) / sinh(x)

# ==================== 反双曲函数 ====================
def asinh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反双曲正弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_ln(x + _decimal_sqrt(x * x + 1, prec), prec)
    return ln(x + sqrt(x * x + 1))

def acosh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反双曲余弦函数"""
    if isinstance(x, Decimal) or prec is not None:
        if x < 1:
            raise ValueError("math domain error")
        return _decimal_ln(x + _decimal_sqrt(x * x - 1, prec), prec)
    
    if x < 1:
        raise ValueError("math domain error")
    return ln(x + sqrt(x * x - 1))

def atanh(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """反双曲正切函数"""
    if isinstance(x, Decimal) or prec is not None:
        if abs(x) >= 1:
            raise ValueError("math domain error")
        return _decimal_ln((1 + x) / (1 - x), prec) / 2
    
    if abs(x) >= 1:
        raise ValueError("math domain error")
    return ln((1 + x) / (1 - x)) / 2

# ==================== 取整函数 ====================
def floor(x: AnyNum) -> int:
    """向下取整"""
    if isinstance(x, Decimal):
        return int(x.to_integral_value(rounding='ROUND_FLOOR'))
    return int(x) if x >= 0 or x == int(x) else int(x) - 1

def ceil(x: AnyNum) -> int:
    """向上取整"""
    if isinstance(x, Decimal):
        return int(x.to_integral_value(rounding='ROUND_CEILING'))
    return int(x) if x <= 0 or x == int(x) else int(x) + 1

def trunc(x: AnyNum) -> int:
    """截断取整"""
    if isinstance(x, Decimal):
        return int(x.to_integral_value(rounding='ROUND_DOWN'))
    return int(x)

def round(x: AnyNum, ndigits: int = 0) -> AnyNum:
    """四舍五入"""
    if isinstance(x, Decimal):
        return x.quantize(Decimal(10) ** -ndigits)
    return type(x)(int(x * 10**ndigits + 0.5) / 10**ndigits)

# ==================== 特殊函数 ====================
def factorial(n: int) -> int:
    """阶乘函数"""
    if n < 0:
        raise ValueError("math domain error")
    if n < 2:
        return 1
    
    # 分治法优化
    def _product(a, b):
        if a == b:
            return a
        mid = (a + b) // 2
        return _product(a, mid) * _product(mid + 1, b)
    
    return _product(1, n)

def gamma(x: AnyNum, prec: PrecisionType = None) -> AnyNum:
    """伽马函数（Lanczos近似）"""
    if isinstance(x, Decimal) or prec is not None:
        return _decimal_gamma(x, prec)
    
    if x <= 0 and x == int(x):
        raise ValueError("math domain error")
    
    # Lanczos近似参数
    g = 7
    p = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7
    ]
    
    def _gamma(z):
        if z < 0.5:
            return PI / (sin(PI * z) * _gamma(1 - z))
        z -= 1
        x = p[0]
        for i in range(1, len(p)):
            x += p[i] / (z + i)
        t = z + g + 0.5
        return sqrt(2 * PI) * t ** (z + 0.5) * exp(-t) * x
    
    return _gamma(x)

def _decimal_gamma(x: Decimal, prec: PrecisionType = None) -> Decimal:
    """高精度Decimal版伽马函数"""
    ctx = Context(prec=prec + 2 if prec else getcontext().prec)
    if x <= 0 and x == int(x):
        raise ValueError("math domain error")
    
    g = Decimal(7)
    p = [
        Decimal('0.99999999999980993'),
        Decimal('676.5203681218851'),
        Decimal('-1259.1392167224028'),
        Decimal('771.32342877765313'),
        Decimal('-176.61502916214059'),
        Decimal('12.507343278686905'),
        Decimal('-0.13857109526572012'),
        Decimal('9.9843695780195716e-6'),
        Decimal('1.5056327351493116e-7')
    ]
    
    def _gamma(z):
        if z < Decimal('0.5'):
            return PI / (_decimal_sin(PI * z, prec) * _gamma(Decimal(1) - z))
        z -= Decimal(1)
        x = p[0]
        for i in range(1, len(p)):
            x += p[i] / (z + Decimal(i))
        t = z + g + Decimal('0.5')
        return _decimal_sqrt(2 * PI, prec) * t ** (z + Decimal('0.5')) * _decimal_exp(-t, prec) * x
    
    return +_gamma(x)

# ==================== 测试代码 ====================
if __name__ == "__main__":
    # 验证基础函数
    assert abs(sqrt(2) - 1.414213562) < 1e-6
    assert abs(exp(1) - float(E)) < 1e-6
    assert abs(ln(float(E))) - 1 < 1e-6
    
    # 三角函数验证
    assert abs(sin(PI/2) - 1) < 1e-10
    assert abs(cos(PI) + 1) < 1e-10
    assert abs(tan(PI/4) - 1) < 1e-10
    
    # 反三角函数验证
    assert abs(asin(0.5) - 0.523598775) < 1e-6
    assert abs(acos(0.5) - 1.047197551) < 1e-6
    assert abs(atan(1) - PI/4) < 1e-10
    
    # 双曲函数验证
    assert abs(sinh(0)) < 1e-10
    assert abs(cosh(0) - 1) < 1e-10
    assert abs(tanh(1) - 0.761594155) < 1e-6
    
    # 特殊函数验证
    assert factorial(5) == 120
    assert abs(gamma(0.5) - sqrt(PI)) < 1e-6
    
    # 高精度测试
    MathConfig.set_precision(50)
    assert str(exp(Decimal(1)))[:52] == "2.71828182845904523536028747135266249775724709369995"
    assert str(ln(Decimal(10)))[:52] == "2.30258509299404568401799145468436420760110148862877"
    
    print("所有测试通过！")