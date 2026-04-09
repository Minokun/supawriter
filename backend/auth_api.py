"""
FastAPI 认证 API
提供 JWT Token 验证和用户管理接口
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = FastAPI(title="SupaWriter Auth API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 天


# Pydantic 模型
class User(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None


class TokenData(BaseModel):
    user: User
    exp: Optional[datetime] = None


class LoginRequest(BaseModel):
    google_token: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: User


# JWT Token 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="无效的 Token")


async def get_current_user(authorization: Optional[str] = Header(None)) -> User:
    """从请求头获取当前用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的认证方案")
        
        payload = verify_token(token)
        user_data = payload.get("user")
        if not user_data:
            raise HTTPException(status_code=401, detail="无效的 Token")
        
        return User(**user_data)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的 Authorization 头")


# API 路由
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Google OAuth 登录
    前端通过 NextAuth 获取 Google Token，后端验证并生成 JWT
    """
    # 这里应该验证 Google Token 的有效性
    # 简化实现：直接从 NextAuth 传递的用户信息创建 JWT
    
    # 实际生产环境应该：
    # 1. 验证 Google Token
    # 2. 从数据库获取或创建用户
    # 3. 生成 JWT Token
    
    # 示例用户数据（实际应从 Google Token 解析）
    user = User(
        id="google_user_id",
        email="user@example.com",
        name="User Name",
        picture="https://example.com/avatar.jpg"
    )
    
    # 创建 JWT Token
    access_token = create_access_token(
        data={"user": user.dict()},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


@app.post("/api/auth/verify")
async def verify_token_endpoint(authorization: Optional[str] = Header(None)):
    """验证 Token 是否有效"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的认证方案")
        
        payload = verify_token(token)
        return {"valid": True, "user": payload.get("user")}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "SupaWriter Auth API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
