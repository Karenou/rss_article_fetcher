#!/usr/bin/env python3
"""
View Articles Tool
查看已抓取的RSS文章
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.storage import Storage
from src.logger import get_logger


def print_separator(char="=", length=80):
    """打印分隔线"""
    print(char * length)


def print_article(index, article_data):
    """打印单篇文章信息"""
    print(f"\n📰 文章 #{index}")
    print_separator("-", 80)
    
    # 基本信息
    print(f"📌 标题: {article_data.get('title', 'N/A')}")
    print(f"🔗 链接: {article_data.get('link', 'N/A')}")
    print(f"📅 发布时间: {article_data.get('published', 'N/A')}")
    print(f"📰 来源: {article_data.get('source', 'N/A')}")
    
    # 摘要
    summary = article_data.get('summary', '')
    if summary:
        print(f"\n📝 英文摘要:")
        print_separator("-", 80)
        # 格式化摘要，每行最多80字符
        words = summary.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 <= 78:
                line += word + " "
            else:
                print(f"  {line.strip()}")
                line = word + " "
        if line:
            print(f"  {line.strip()}")
    else:
        print(f"\n📝 英文摘要: (无)")
    
    # 原始描述
    description = article_data.get('description', '')
    if description and description != summary:
        print(f"\n📄 原始描述:")
        print_separator("-", 80)
        # 截取前200字符
        desc_preview = description[:200]
        if len(description) > 200:
            desc_preview += "..."
        print(f"  {desc_preview}")
    
    # 处理时间
    processed_at = article_data.get('processed_at', '')
    if processed_at:
        print(f"\n⏰ 处理时间: {processed_at}")


def view_all_articles(data_dir: str, limit: int = None, format: str = "text"):
    """查看所有文章
    
    Args:
        data_dir: 数据目录路径
        limit: 限制显示数量
        format: 输出格式 (text/json)
    """
    import sqlite3
    
    db_path = Path(data_dir) / "processed_articles.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 查询所有文章
        cursor.execute('''
            SELECT url, title, source, source_url, description, content, summary, published_at, processed_at
            FROM articles
            ORDER BY processed_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("❌ 没有找到任何文章")
            return
        
        # 限制数量
        if limit:
            rows = rows[:limit]
        
        total = len(rows)
        
        print_separator("=", 80)
        print(f"  📚 RSS文章查看器")
        print_separator("=", 80)
        print(f"\n总共有 {total} 篇文章")
        if limit and len(rows) < total:
            print(f"显示最新的 {len(rows)} 篇")
        print()
        
        if format == "json":
            # JSON格式输出
            output = []
            for row in rows:
                output.append({
                    "url": row[0],
                    "title": row[1],
                    "source": row[2],
                    "source_url": row[3],
                    "description": row[4],
                    "content": row[5],
                    "summary": row[6],
                    "published": row[7],
                    "processed_at": row[8]
                })
            print(json.dumps(output, indent=2, ensure_ascii=False))
        else:
            # 文本格式输出
            for i, row in enumerate(rows, 1):
                article_data = {
                    "url": row[0],
                    "title": row[1],
                    "link": row[0],
                    "source": row[2],
                    "source_url": row[3],
                    "description": row[4],
                    "content": row[5],
                    "summary": row[6],
                    "published": row[7],
                    "processed_at": row[8]
                }
                print_article(i, article_data)
            
            print("\n")
            print_separator("=", 80)
            print(f"  共显示 {len(rows)} 篇文章")
            print_separator("=", 80)
    
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        import traceback
        traceback.print_exc()


def view_latest_articles(data_dir: str, count: int = 5):
    """查看最新的N篇文章"""
    view_all_articles(data_dir, limit=count, format="text")


def view_article_by_keyword(data_dir: str, keyword: str):
    """根据关键词搜索文章"""
    import sqlite3
    
    db_path = Path(data_dir) / "processed_articles.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 搜索匹配的文章
        keyword_pattern = f"%{keyword}%"
        cursor.execute('''
            SELECT url, title, source, source_url, description, content, summary, published_at, processed_at
            FROM articles
            WHERE title LIKE ? OR source LIKE ? OR summary LIKE ? OR description LIKE ?
            ORDER BY processed_at DESC
        ''', (keyword_pattern, keyword_pattern, keyword_pattern, keyword_pattern))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print(f"❌ 没有找到包含关键词 '{keyword}' 的文章")
            return
        
        print_separator("=", 80)
        print(f"  🔍 搜索结果: '{keyword}'")
        print_separator("=", 80)
        print(f"\n找到 {len(rows)} 篇相关文章\n")
        
        for i, row in enumerate(rows, 1):
            article_data = {
                "url": row[0],
                "title": row[1],
                "link": row[0],
                "source": row[2],
                "source_url": row[3],
                "description": row[4],
                "content": row[5],
                "summary": row[6],
                "published": row[7],
                "processed_at": row[8]
            }
            print_article(i, article_data)
        
        print("\n")
        print_separator("=", 80)
        print(f"  共找到 {len(rows)} 篇文章")
        print_separator("=", 80)
    
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


def export_to_json(data_dir: str, output_file: str):
    """导出文章到JSON文件"""
    import sqlite3
    
    db_path = Path(data_dir) / "processed_articles.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url, title, source, source_url, description, content, summary, published_at, processed_at
            FROM articles
            ORDER BY processed_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("❌ 没有找到任何文章")
            return
        
        # 转换为列表格式
        output = []
        for row in rows:
            output.append({
                "url": row[0],
                "title": row[1],
                "source": row[2],
                "source_url": row[3],
                "description": row[4],
                "content": row[5],
                "summary": row[6],
                "published": row[7],
                "processed_at": row[8]
            })
        
        # 写入文件
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已导出 {len(output)} 篇文章到: {output_path}")
        print(f"   文件大小: {output_path.stat().st_size} bytes")
    
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()


def show_statistics(data_dir: str):
    """显示统计信息"""
    import sqlite3
    
    db_path = Path(data_dir) / "processed_articles.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 总文章数
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("❌ 没有找到任何文章")
            conn.close()
            return
        
        # 按来源统计
        cursor.execute('''
            SELECT source, COUNT(*) as count
            FROM articles
            GROUP BY source
            ORDER BY count DESC
        ''')
        sources = cursor.fetchall()
        
        # 按日期统计
        cursor.execute('''
            SELECT DATE(processed_at) as date, COUNT(*) as count
            FROM articles
            GROUP BY DATE(processed_at)
            ORDER BY date DESC
            LIMIT 10
        ''')
        dates = cursor.fetchall()
        
        conn.close()
        
        print_separator("=", 80)
        print(f"  📊 文章统计信息")
        print_separator("=", 80)
        
        print(f"\n📚 总文章数: {total}")
        
        print(f"\n📰 按来源统计:")
        print_separator("-", 80)
        for source, count in sources:
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {source:30s} {count:3d} 篇 ({percentage:5.1f}%) {bar}")
        
        print(f"\n📅 按日期统计 (最近10天):")
        print_separator("-", 80)
        for date, count in dates:
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 2)
            print(f"  {date:12s} {count:3d} 篇 ({percentage:5.1f}%) {bar}")
        
        print()
        print_separator("=", 80)
    
    except Exception as e:
        print(f"❌ 统计失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="查看已抓取的RSS文章",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看最新的5篇文章
  python3 view_articles.py
  
  # 查看最新的10篇文章
  python3 view_articles.py --latest 10
  
  # 查看所有文章
  python3 view_articles.py --all
  
  # 搜索包含关键词的文章
  python3 view_articles.py --search "AI"
  
  # 导出所有文章到JSON
  python3 view_articles.py --export articles.json
  
  # 显示统计信息
  python3 view_articles.py --stats
  
  # 以JSON格式输出
  python3 view_articles.py --all --format json
        """
    )
    
    parser.add_argument(
        '--data-dir',
        default='/Users/karenou/Desktop/AI/rss_article_fetcher/data',
        help='数据目录路径'
    )
    
    parser.add_argument(
        '--latest',
        type=int,
        metavar='N',
        help='查看最新的N篇文章 (默认: 5)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='查看所有文章'
    )
    
    parser.add_argument(
        '--search',
        metavar='KEYWORD',
        help='搜索包含关键词的文章'
    )
    
    parser.add_argument(
        '--export',
        metavar='FILE',
        help='导出文章到JSON文件'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示统计信息'
    )
    
    parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='输出格式 (默认: text)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.stats:
            show_statistics(args.data_dir)
        elif args.export:
            export_to_json(args.data_dir, args.export)
        elif args.search:
            view_article_by_keyword(args.data_dir, args.search)
        elif args.all:
            view_all_articles(args.data_dir, limit=None, format=args.format)
        else:
            # 默认显示最新的5篇
            count = args.latest if args.latest else 5
            view_latest_articles(args.data_dir, count)
    
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
