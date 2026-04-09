#!/usr/bin/env python3
"""测试文章保存到数据库功能"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.history_utils import add_history_record
from utils.database import Database

def test_article_save():
    """测试保存文章到数据库"""
    
    # 测试数据
    test_username = "admin"
    test_topic = "测试文章标题"
    test_content = "这是一篇测试文章的内容。\n\n包含多个段落。"
    
    print("🧪 开始测试文章保存功能...")
    print(f"   用户名: {test_username}")
    print(f"   标题: {test_topic}")
    
    # 1. 保存文章
    try:
        record = add_history_record(
            username=test_username,
            topic=test_topic,
            article_content=test_content,
            summary="测试摘要",
            model_type="deepseek",
            model_name="deepseek-chat",
            write_type="detailed",
            spider_num=5,
            custom_style="专业风格",
            tags="测试,文章",
            article_topic="测试主题"
        )
        print(f"\n✅ 文章保存成功!")
        print(f"   本地记录ID: {record.get('id')}")
        if 'db_id' in record:
            print(f"   数据库ID: {record.get('db_id')}")
        else:
            print("   ⚠️  未获取到数据库ID")
    except Exception as e:
        print(f"\n❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 验证数据库中的记录
    print("\n🔍 验证数据库记录...")
    try:
        with Database.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, username, topic, summary, model_type, created_at
                FROM articles
                WHERE username = %s
                ORDER BY created_at DESC
                LIMIT 5
            """, (test_username,))
            
            articles = cursor.fetchall()
            
            if articles:
                print(f"\n📊 找到 {len(articles)} 篇文章:")
                for i, article in enumerate(articles, 1):
                    print(f"\n   {i}. ID: {article['id']}")
                    print(f"      标题: {article['topic']}")
                    print(f"      摘要: {article['summary']}")
                    print(f"      模型: {article['model_type']}")
                    print(f"      创建时间: {article['created_at']}")
                
                # 检查是否包含刚才保存的文章
                if any(a['topic'] == test_topic for a in articles):
                    print(f"\n✅ 确认找到测试文章!")
                    return True
                else:
                    print(f"\n⚠️  未找到测试文章")
                    return False
            else:
                print(f"\n❌ 数据库中没有找到任何文章")
                return False
                
    except Exception as e:
        print(f"\n❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_article_save()
    sys.exit(0 if success else 1)
