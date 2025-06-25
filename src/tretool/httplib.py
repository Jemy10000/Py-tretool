import urllib.request
import urllib.parse
import urllib.error
import json
import time
import os
import mimetypes
import http.cookiejar
import socket
from http.client import HTTPResponse
from typing import Optional, Dict, Union, Any, List, Tuple, Iterator
from concurrent.futures import Future
from dataclasses import dataclass


class NetworkError(Exception):
    """网络请求异常基类"""
    pass


class RetryExhaustedError(NetworkError):
    """重试次数耗尽异常"""
    pass


class TimeoutError(NetworkError):
    """请求超时异常"""
    pass


class AuthError(NetworkError):
    """认证失败异常"""
    pass


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    backoff_factor: float = 0.1
    retry_on: Tuple[int, ...] = (500, 502, 503, 504)


class HttpResponse:
    """HTTP响应封装类"""

    def __init__(self, response: HTTPResponse):
        self.status_code = response.status
        self.headers = dict(response.getheaders())
        self._content = response.read()
        self._response = response
        self.url = response.geturl()

    @property
    def content(self) -> bytes:
        """获取原始字节内容"""
        return self._content

    @property
    def text(self) -> str:
        """获取文本内容(UTF-8解码)"""
        return self._content.decode('utf-8')

    def json(self) -> Any:
        """解析JSON内容"""
        return json.loads(self.text)

    def close(self):
        """关闭响应"""
        self._response.close()

    def __str__(self) -> str:
        return f"<HttpResponse [{self.status_code}]>"


class HttpClient:
    """
    增强版HTTP客户端
    基于urllib标准库实现，支持多种高级功能
    """

    def __init__(self,
                 base_url: str = "",
                 timeout: float = 10.0,
                 retry_config: Optional[RetryConfig] = None,
                 proxy: Optional[Dict[str, str]] = None,
                 auth: Optional[Tuple[str, str]] = None,
                 cookie_jar: Optional[http.cookiejar.CookieJar] = None):
        """
        初始化HTTP客户端

        :param base_url: 基础URL，所有请求会基于此URL
        :param timeout: 请求超时时间(秒)
        :param retry_config: 重试配置
        :param proxy: 代理配置，如 {'http': 'http://proxy.example.com:8080'}
        :param auth: 基本认证 (username, password)
        :param cookie_jar: Cookie存储对象
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.proxy = proxy
        self.auth = auth
        self.cookie_jar = cookie_jar

        # 初始化opener
        self._build_opener()

        self.default_headers = {
            'User-Agent': 'Python HttpClient/2.0',
            'Accept': 'application/json',
        }

    def _build_opener(self):
        """构建urllib opener"""
        handlers = []

        # 添加代理支持
        if self.proxy:
            proxy_handler = urllib.request.ProxyHandler(self.proxy)
            handlers.append(proxy_handler)

        # 添加Cookie支持
        if self.cookie_jar:
            cookie_handler = urllib.request.HTTPCookieProcessor(self.cookie_jar)
            handlers.append(cookie_handler)

        # 添加基本认证支持
        if self.auth:
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, self.base_url, self.auth[0], self.auth[1])
            auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
            handlers.append(auth_handler)

        self.opener = urllib.request.build_opener(*handlers)

    def _request(self,
                 method: str,
                 endpoint: str,
                 params: Optional[Dict] = None,
                 data: Optional[Union[Dict, str, bytes]] = None,
                 json_data: Optional[Any] = None,
                 headers: Optional[Dict] = None,
                 files: Optional[Dict[str, Union[str, Tuple[str, bytes]]]] = None,
                 timeout: Optional[float] = None) -> HttpResponse:
        """
        内部请求方法

        :param method: HTTP方法(GET, POST等)
        :param endpoint: 请求端点
        :param params: URL参数
        :param data: 请求体数据
        :param json_data: JSON格式的请求体
        :param headers: 请求头
        :param files: 要上传的文件 {'name': filepath} 或 {'name': ('filename', content)}
        :param timeout: 本次请求超时时间(覆盖默认值)
        :return: HttpResponse对象
        :raises NetworkError: 当请求失败时抛出
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {**self.default_headers, **(headers or {})}
        timeout = timeout or self.timeout

        # 处理URL参数
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        # 处理请求体数据
        body: Optional[bytes] = None
        content_type = headers.get('Content-Type', '')

        if files:
            boundary = '----------boundary_' + str(int(time.time()))
            headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
            body = self._encode_multipart_formdata(files, boundary)
        elif json_data is not None:
            body = json.dumps(json_data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        elif data is not None:
            if isinstance(data, dict):
                body = urllib.parse.urlencode(data).encode('utf-8')
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
            elif isinstance(data, str):
                body = data.encode('utf-8')
            elif isinstance(data, bytes):
                body = data

        # 创建请求对象
        req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())

        # 实现重试机制
        last_exception = None
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = self.opener.open(req, timeout=timeout)
                return HttpResponse(response)
            except urllib.error.HTTPError as e:
                last_exception = e
                if e.code in (401, 403):
                    raise AuthError(f"认证失败: {e.code} {e.reason}") from e
                if e.code not in self.retry_config.retry_on:
                    raise NetworkError(f"HTTP错误 {e.code}: {e.reason}") from e
            except urllib.error.URLError as e:
                last_exception = e
                if isinstance(e.reason, socket.timeout):
                    raise TimeoutError(f"请求超时: {str(e)}") from e
            except Exception as e:
                last_exception = e
                raise NetworkError(f"请求失败: {str(e)}") from e

            # 如果还有重试机会，等待一段时间
            if attempt < self.retry_config.max_retries:
                sleep_time = self.retry_config.backoff_factor * (2 ** attempt)
                time.sleep(sleep_time)

        raise RetryExhaustedError(f"重试{self.retry_config.max_retries}次后仍然失败: {str(last_exception)}")

    def _encode_multipart_formdata(self, files: Dict[str, Union[str, Tuple[str, bytes]]], boundary: str) -> bytes:
        """编码multipart/form-data请求体"""
        lines = []

        for name, value in files.items():
            if isinstance(value, tuple):
                filename, content = value
            else:
                filename = os.path.basename(value)
                with open(value, 'rb') as f:
                    content = f.read()

            mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            lines.append(f'--{boundary}')
            lines.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"')
            lines.append(f'Content-Type: {mime_type}')
            lines.append('')
            lines.append(content)

        lines.append(f'--{boundary}--')
        lines.append('')

        return '\r\n'.join(lines).encode('utf-8')

    # ========== HTTP方法 ==========
    def get(self, endpoint: str, params: Optional[Dict] = None,
            headers: Optional[Dict] = None, timeout: Optional[float] = None) -> HttpResponse:
        """发送GET请求"""
        return self._request('GET', endpoint, params=params, headers=headers, timeout=timeout)

    def post(self, endpoint: str, data: Optional[Union[Dict, str, bytes]] = None,
             json_data: Optional[Any] = None, headers: Optional[Dict] = None,
             files: Optional[Dict] = None, timeout: Optional[float] = None) -> HttpResponse:
        """发送POST请求"""
        return self._request('POST', endpoint, data=data, json_data=json_data,
                           headers=headers, files=files, timeout=timeout)

    def put(self, endpoint: str, data: Optional[Union[Dict, str, bytes]] = None,
            json_data: Optional[Any] = None, headers: Optional[Dict] = None,
            timeout: Optional[float] = None) -> HttpResponse:
        """发送PUT请求"""
        return self._request('PUT', endpoint, data=data, json_data=json_data,
                           headers=headers, timeout=timeout)

    def delete(self, endpoint: str, headers: Optional[Dict] = None,
               timeout: Optional[float] = None) -> HttpResponse:
        """发送DELETE请求"""
        return self._request('DELETE', endpoint, headers=headers, timeout=timeout)

    def head(self, endpoint: str, params: Optional[Dict] = None,
             headers: Optional[Dict] = None, timeout: Optional[float] = None) -> HttpResponse:
        """发送HEAD请求"""
        return self._request('HEAD', endpoint, params=params, headers=headers, timeout=timeout)

    def patch(self, endpoint: str, data: Optional[Union[Dict, str, bytes]] = None,
              json_data: Optional[Any] = None, headers: Optional[Dict] = None,
              timeout: Optional[float] = None) -> HttpResponse:
        """发送PATCH请求"""
        return self._request('PATCH', endpoint, data=data, json_data=json_data,
                           headers=headers, timeout=timeout)

    def options(self, endpoint: str, headers: Optional[Dict] = None,
                timeout: Optional[float] = None) -> HttpResponse:
        """发送OPTIONS请求"""
        return self._request('OPTIONS', endpoint, headers=headers, timeout=timeout)

    # ========== 高级功能 ==========
    def stream(self, endpoint: str, params: Optional[Dict] = None,
               headers: Optional[Dict] = None, timeout: Optional[float] = None,
               chunk_size: int = 8192) -> Iterator[bytes]:
        """
        流式下载大文件

        :param chunk_size: 每次读取的块大小(字节)
        :return: 生成器，每次产生一个数据块
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {**self.default_headers, **(headers or {})}
        timeout = timeout or self.timeout

        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        req = urllib.request.Request(url, headers=headers, method='GET')

        try:
            response = self.opener.open(req, timeout=timeout)
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        finally:
            response.close()

    def download(self, endpoint: str, file_path: str, params: Optional[Dict] = None,
                 headers: Optional[Dict] = None, timeout: Optional[float] = None,
                 chunk_size: int = 8192, show_progress: bool = False) -> None:
        """
        下载文件到本地

        :param file_path: 保存路径
        :param show_progress: 是否显示进度信息
        """
        total_size = 0
        downloaded = 0

        # 先获取文件大小
        try:
            head_resp = self.head(endpoint, params=params, headers=headers, timeout=timeout)
            total_size = int(head_resp.headers.get('Content-Length', 0))
        except Exception:
            pass

        # 下载文件
        with open(file_path, 'wb') as f:
            for chunk in self.stream(endpoint, params=params, headers=headers,
                                   timeout=timeout, chunk_size=chunk_size):
                f.write(chunk)
                downloaded += len(chunk)

                if show_progress and total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r下载进度: {percent:.2f}% ({downloaded}/{total_size} bytes)", end='')

            if show_progress:
                print()

    def upload(self, endpoint: str, files: Dict[str, Union[str, Tuple[str, bytes]]],
               headers: Optional[Dict] = None, timeout: Optional[float] = None) -> HttpResponse:
        """上传文件"""
        return self._request('POST', endpoint, files=files, headers=headers, timeout=timeout)

    # ========== 配置方法 ==========
    def set_default_header(self, key: str, value: str):
        """设置默认请求头"""
        self.default_headers[key] = value

    def clear_default_headers(self):
        """清除所有默认请求头"""
        self.default_headers.clear()

    def set_basic_auth(self, username: str, password: str):
        """设置基本认证"""
        self.auth = (username, password)
        self._build_opener()

    def set_bearer_token(self, token: str):
        """设置Bearer Token认证"""
        self.default_headers['Authorization'] = f'Bearer {token}'

    def set_proxy(self, proxy: Dict[str, str]):
        """设置代理"""
        self.proxy = proxy
        self._build_opener()

    def set_cookies(self, cookie_jar: http.cookiejar.CookieJar):
        """设置Cookie存储"""
        self.cookie_jar = cookie_jar
        self._build_opener()

    def add_cookie(self, name: str, value: str, domain: str = None, path: str = '/'):
        """添加单个Cookie"""
        if not self.cookie_jar:
            self.cookie_jar = http.cookiejar.CookieJar()
            self._build_opener()

        cookie = http.cookiejar.Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain or urllib.parse.urlparse(self.base_url).netloc,
            domain_specified=bool(domain),
            domain_initial_dot=False,
            path=path,
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={'HttpOnly': None},
            rfc2109=False
        )
        self.cookie_jar.set_cookie(cookie)

    def clear_cookies(self):
        """清除所有Cookies"""
        if self.cookie_jar:
            self.cookie_jar.clear()

    def follow_redirect(self, max_redirects: int = 5):
        """设置是否跟随重定向"""
        # urllib默认会跟随重定向，此方法用于可能的未来扩展
        pass


class SimpleNetwork:
    """
    增强版简单网络请求工具
    提供静态方法方便一次性请求
    """

    @staticmethod
    def request(method: str,
                url: str,
                params: Optional[Dict] = None,
                data: Optional[Union[Dict, str, bytes]] = None,
                json_data: Optional[Any] = None,
                headers: Optional[Dict] = None,
                files: Optional[Dict[str, Union[str, Tuple[str, bytes]]]] = None,
                timeout: float = 10.0,
                retry_config: Optional[RetryConfig] = None,
                proxy: Optional[Dict[str, str]] = None,
                auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """
        发送HTTP请求

        :param method: HTTP方法
        :param url: 请求URL
        :param params: URL参数
        :param data: 请求体数据
        :param json_data: JSON格式的请求体
        :param headers: 请求头
        :param files: 要上传的文件
        :param timeout: 超时时间(秒)
        :param retry_config: 重试配置
        :param proxy: 代理配置
        :param auth: 基本认证 (username, password)
        :return: HttpResponse对象
        """
        # 创建临时客户端
        client = HttpClient(
            base_url=url.split('?')[0].rsplit('/', 1)[0],
            timeout=timeout,
            retry_config=retry_config,
            proxy=proxy,
            auth=auth
        )

        endpoint = '/' + url.split('?')[0].split('/', 3)[-1] if '/' in url[8:] else ''

        try:
            return client._request(
                method=method,
                endpoint=endpoint,
                params=params,
                data=data,
                json_data=json_data,
                headers=headers,
                files=files,
                timeout=timeout
            )
        finally:
            if hasattr(client, 'opener'):
                client.opener.close()

    @staticmethod
    def get(url: str, params: Optional[Dict] = None,
            headers: Optional[Dict] = None, timeout: float = 10.0,
            retry_config: Optional[RetryConfig] = None,
            proxy: Optional[Dict[str, str]] = None,
            auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送GET请求"""
        return SimpleNetwork.request(
            'GET', url, params=params, headers=headers,
            timeout=timeout, retry_config=retry_config,
            proxy=proxy, auth=auth
        )

    @staticmethod
    def post(url: str, data: Optional[Union[Dict, str, bytes]] = None,
             json_data: Optional[Any] = None, headers: Optional[Dict] = None,
             files: Optional[Dict] = None, timeout: float = 10.0,
             retry_config: Optional[RetryConfig] = None,
             proxy: Optional[Dict[str, str]] = None,
             auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送POST请求"""
        return SimpleNetwork.request(
            'POST', url, data=data, json_data=json_data,
            headers=headers, files=files, timeout=timeout,
            retry_config=retry_config, proxy=proxy, auth=auth
        )

    @staticmethod
    def put(url: str, data: Optional[Union[Dict, str, bytes]] = None,
            json_data: Optional[Any] = None, headers: Optional[Dict] = None,
            timeout: float = 10.0, retry_config: Optional[RetryConfig] = None,
            proxy: Optional[Dict[str, str]] = None,
            auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送PUT请求"""
        return SimpleNetwork.request(
            'PUT', url, data=data, json_data=json_data,
            headers=headers, timeout=timeout,
            retry_config=retry_config, proxy=proxy, auth=auth
        )

    @staticmethod
    def delete(url: str, headers: Optional[Dict] = None,
               timeout: float = 10.0, retry_config: Optional[RetryConfig] = None,
               proxy: Optional[Dict[str, str]] = None,
               auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送DELETE请求"""
        return SimpleNetwork.request(
            'DELETE', url, headers=headers,
            timeout=timeout, retry_config=retry_config,
            proxy=proxy, auth=auth
        )

    @staticmethod
    def head(url: str, params: Optional[Dict] = None,
             headers: Optional[Dict] = None, timeout: float = 10.0,
             retry_config: Optional[RetryConfig] = None,
             proxy: Optional[Dict[str, str]] = None,
             auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送HEAD请求"""
        return SimpleNetwork.request(
            'HEAD', url, params=params, headers=headers,
            timeout=timeout, retry_config=retry_config,
            proxy=proxy, auth=auth
        )

    @staticmethod
    def patch(url: str, data: Optional[Union[Dict, str, bytes]] = None,
              json_data: Optional[Any] = None, headers: Optional[Dict] = None,
              timeout: float = 10.0, retry_config: Optional[RetryConfig] = None,
              proxy: Optional[Dict[str, str]] = None,
              auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送PATCH请求"""
        return SimpleNetwork.request(
            'PATCH', url, data=data, json_data=json_data,
            headers=headers, timeout=timeout,
            retry_config=retry_config, proxy=proxy, auth=auth
        )

    @staticmethod
    def options(url: str, headers: Optional[Dict] = None,
                timeout: float = 10.0, retry_config: Optional[RetryConfig] = None,
                proxy: Optional[Dict[str, str]] = None,
                auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """发送OPTIONS请求"""
        return SimpleNetwork.request(
            'OPTIONS', url, headers=headers,
            timeout=timeout, retry_config=retry_config,
            proxy=proxy, auth=auth
        )

    @staticmethod
    def upload(url: str, files: Dict[str, Union[str, Tuple[str, bytes]]],
               headers: Optional[Dict] = None, timeout: float = 10.0,
               retry_config: Optional[RetryConfig] = None,
               proxy: Optional[Dict[str, str]] = None,
               auth: Optional[Tuple[str, str]] = None) -> HttpResponse:
        """上传文件"""
        return SimpleNetwork.request(
            'POST', url, files=files, headers=headers,
            timeout=timeout, retry_config=retry_config,
            proxy=proxy, auth=auth
        )

    @staticmethod
    def download_file(url: str, file_path: str, params: Optional[Dict] = None,
                     headers: Optional[Dict] = None, timeout: float = 30.0,
                     retry_config: Optional[RetryConfig] = None,
                     proxy: Optional[Dict[str, str]] = None,
                     auth: Optional[Tuple[str, str]] = None,
                     chunk_size: int = 8192, show_progress: bool = False) -> None:
        """
        下载文件到本地

        :param file_path: 保存路径
        :param show_progress: 是否显示进度信息
        """
        client = HttpClient(
            base_url=url.split('?')[0].rsplit('/', 1)[0],
            timeout=timeout,
            retry_config=retry_config,
            proxy=proxy,
            auth=auth
        )

        endpoint = '/' + url.split('?')[0].split('/', 3)[-1] if '/' in url[8:] else ''

        try:
            client.download(endpoint, file_path, params=params, headers=headers,
                          timeout=timeout, chunk_size=chunk_size,
                          show_progress=show_progress)
        finally:
            if hasattr(client, 'opener'):
                client.opener.close()


class AsyncHttpClient:
    """异步HTTP客户端(基于线程池实现)"""

    def __init__(self, max_workers: int = 4, **kwargs):
        """
        :param max_workers: 线程池大小
        :param kwargs: 同HttpClient的参数
        """
        from concurrent.futures import ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.sync_client = HttpClient(**kwargs)

    def request(self, method: str, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步请求"""
        return self.executor.submit(self.sync_client._request, method, endpoint, **kwargs)

    def get(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步GET请求"""
        return self.request('GET', endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步POST请求"""
        return self.request('POST', endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步PUT请求"""
        return self.request('PUT', endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步DELETE请求"""
        return self.request('DELETE', endpoint, **kwargs)

    def head(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步HEAD请求"""
        return self.request('HEAD', endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步PATCH请求"""
        return self.request('PATCH', endpoint, **kwargs)

    def options(self, endpoint: str, **kwargs) -> Future[HttpResponse]:
        """异步OPTIONS请求"""
        return self.request('OPTIONS', endpoint, **kwargs)

    def stream(self, endpoint: str, **kwargs) -> Future[Iterator[bytes]]:
        """异步流式下载"""
        return self.executor.submit(lambda: list(self.sync_client.stream(endpoint, **kwargs)))

    def download(self, endpoint: str, file_path: str, **kwargs) -> Future[None]:
        """异步下载文件"""
        return self.executor.submit(self.sync_client.download, endpoint, file_path, **kwargs)

    def upload(self, endpoint: str, files: Dict[str, Union[str, Tuple[str, bytes]]], **kwargs) -> Future[HttpResponse]:
        """异步上传文件"""
        return self.request('POST', endpoint, files=files, **kwargs)

    def close(self):
        """关闭客户端"""
        self.executor.shutdown(wait=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class HttpUtils:
    """HTTP实用工具类"""

    @staticmethod
    def parse_query_params(url: str) -> Dict[str, List[str]]:
        """解析URL查询参数"""
        parsed = urllib.parse.urlparse(url)
        return urllib.parse.parse_qs(parsed.query)

    @staticmethod
    def build_url(base_url: str, params: Dict) -> str:
        """构建带参数的URL"""
        query = urllib.parse.urlencode(params, doseq=True)
        return f"{base_url}?{query}" if query else base_url

    @staticmethod
    def encode_form_data(data: Dict) -> bytes:
        """编码表单数据"""
        return urllib.parse.urlencode(data).encode('utf-8')

    @staticmethod
    def get_content_type(filename: str) -> str:
        """根据文件名获取Content-Type"""
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

    @staticmethod
    def set_global_timeout(timeout: float):
        """设置urllib全局超时时间"""
        socket.setdefaulttimeout(timeout)

    @staticmethod
    def disable_ssl_verify():
        """禁用SSL验证(不推荐，仅用于测试)"""
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

    @staticmethod
    def format_headers(headers: Dict) -> str:
        """格式化请求头为字符串"""
        return '\n'.join(f'{k}: {v}' for k, v in headers.items())

    @staticmethod
    def parse_cookies(cookie_str: str) -> Dict[str, str]:
        """解析Cookie字符串为字典"""
        return dict(pair.split('=', 1) for pair in cookie_str.split('; '))

    @staticmethod
    def encode_url(url: str) -> str:
        """编码URL中的特殊字符"""
        return urllib.parse.quote(url, safe=':/?&=')