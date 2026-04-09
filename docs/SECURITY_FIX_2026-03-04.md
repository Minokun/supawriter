# 安全修复记录

> **日期**: 2026-03-04
> **修复人**: Claude Code
> **风险级别**: 🔴 Critical

---

## 修复摘要

修复了 `batch.py` 中权限验证无效的安全漏洞。

### 问题描述

`batch.py` 中的 `verify_job_ownership()` 函数依赖 `batch_service.get_job_status()` 返回的任务状态来验证用户权限。但 `get_job_status()` 返回的字典**不包含 `user_id` 字段**，导致权限检查实际上从未生效：

```python
# batch.py 第116行 - 原代码
if job_status.get('user_id') and job_status['user_id'] != user_id:
    raise HTTPException(status_code=403, detail="Not authorized to access this job")
```

由于 `job_status.get('user_id')` 始终返回 `None`，条件永远不成立，任何用户都可以访问任意批量任务。

### 影响范围

| 端点 | 风险 | 状态 |
|------|------|------|
| `GET /batch/jobs/{job_id}` | 可查看他人任务 | ✅ 已修复 |
| `POST /batch/jobs/{job_id}/retry` | 可重试他人任务 | ✅ 已修复 |
| `POST /batch/jobs/{job_id}/cancel` | 可取消他人任务 | ✅ 已修复 |
| `GET /batch/jobs/{job_id}/download` | 可下载他人ZIP | ✅ 已修复 |

### 修复方案

在 `batch_service.py` 的 `get_job_status()` 方法返回字典中添加 `user_id` 字段：

```python
# backend/api/services/batch_service.py 第154行
return {
    'id': str(job.id),
    'user_id': job.user_id,  # <-- 添加此行
    'name': job.name,
    # ... 其他字段
}
```

### 验证结果

```
✅ 测试1通过: 正确的用户通过验证
✅ 测试2通过: 未授权用户被拒绝（返回403）
✅ 测试3通过: 不存在的任务返回404
```

---

## 修复文件

| 文件 | 变更 | 行号 |
|------|------|------|
| `backend/api/services/batch_service.py` | 添加 `user_id` 到返回字典 | 第155行 |

---

## 后续建议

1. **代码审查**: 检查其他 Service 的 `get_*` 方法是否也存在类似问题
2. **集成测试**: 添加针对权限验证的自动化集成测试
3. **安全审计**: 定期进行安全代码审查
4. **速率限制**: 考虑添加 API 速率限制防止暴力破解

---

*修复完成时间: 2026-03-04*
