"""
auth 子包 —— 账号登录、注册、注销相关功能。

模块说明：
  - account_io.py  : 账号文件读写（acounts.json 的增删查改）
  - session.py     : 登录/注册/注销等会话管理逻辑
"""

from .session import bind_auth

__all__ = ["bind_auth"]
