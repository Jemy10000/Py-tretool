from ..src.tretool.httplib import *

client = HttpClient(base_url="https://jsonplaceholder.typicode.com")
client.set_default_header("X-Custom-Header", "value")

try:
    # 获取TODO列表
    response = client.get("/todos")
    todos = response.json()
    print(f"获取到 {len(todos)} 条TODO")
    
    # 创建新TODO
    new_todo = {
        "userId": 1,
        "title": "学习Python网络编程",
        "completed": False
    }
    response = client.post("/todos", json_data=new_todo)
    created_todo = response.json()
    print(f"创建的新TODO ID: {created_todo['id']}")
    
    # 更新TODO
    update_data = {"title": "学习Python urllib模块"}
    response = client.put(f"/todos/{created_todo['id']}", json_data=update_data)
    updated_todo = response.json()
    print(f"更新后的标题: {updated_todo['title']}")
    
    # 删除TODO
    response = client.delete(f"/todos/{created_todo['id']}")
    print(f"删除状态码: {response.status_code}")

except NetworkError as e:
    print(f"网络请求出错: {e}")

# 示例2: 使用SimpleNetwork (适合简单的一次性请求)
try:
    # 获取GitHub用户信息
    response = SimpleNetwork.get("https://api.github.com/users/octocat")
    print(f"GitHub用户信息: {response.json()}")
    
    # 发送POST请求到测试API
    test_data = {"name": "测试数据", "value": 123}
    response = SimpleNetwork.post(
        "https://httpbin.org/post",
        json_data=test_data
    )
    print(f"测试API响应: {response.json()}")
    
except NetworkError as e:
    print(f"网络请求出错: {e}")