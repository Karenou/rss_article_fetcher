#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业微信 Webhook 测试脚本
用于诊断和测试企业微信机器人推送功能
"""

import sys
import os
import requests
import json
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class WeComWebhookTester:
    """企业微信 Webhook 测试器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()
        self.test_results = []
        
    def print_header(self, title: str):
        """打印测试标题"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
        
    def print_result(self, test_name: str, passed: bool, message: str):
        """打印测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status} | {test_name}")
        print(f"    {message}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        
    def test_url_format(self) -> bool:
        """测试 URL 格式是否正确"""
        self.print_header("测试 1: URL 格式验证")
        
        # 检查是否为空
        if not self.webhook_url:
            self.print_result("URL 非空检查", False, "Webhook URL 为空")
            return False
        
        self.print_result("URL 非空检查", True, f"URL 长度: {len(self.webhook_url)} 字符")
        
        # 检查是否包含必要的组件
        required_parts = [
            ("https://", "HTTPS 协议"),
            ("qyapi.weixin.qq.com", "企业微信域名"),
            ("/cgi-bin/webhook/send", "Webhook 路径"),
            ("key=", "Key 参数")
        ]
        
        all_passed = True
        for part, desc in required_parts:
            if part in self.webhook_url:
                self.print_result(f"包含 {desc}", True, f"找到: {part}")
            else:
                self.print_result(f"包含 {desc}", False, f"缺失: {part}")
                all_passed = False
                
        # 检查是否有多余的空格或换行
        if self.webhook_url != self.webhook_url.strip():
            self.print_result("空格检查", False, "URL 包含前后空格")
            all_passed = False
        else:
            self.print_result("空格检查", True, "无多余空格")
            
        # 提取并显示 Key
        if "key=" in self.webhook_url:
            key = self.webhook_url.split("key=")[-1]
            print(f"\n📌 提取的 Key: {key[:20]}...{key[-10:] if len(key) > 30 else ''}")
            print(f"   Key 长度: {len(key)} 字符")
            
        return all_passed
        
    def test_connectivity(self) -> Tuple[bool, Optional[Dict]]:
        """测试网络连通性"""
        self.print_header("测试 2: 网络连通性")
        
        try:
            # 发送一个简单的测试消息
            test_message = {
                "msgtype": "text",
                "text": {
                    "content": "🔍 Webhook 连通性测试\n这是一条测试消息，用于验证 Webhook 是否正常工作。"
                }
            }
            
            print(f"\n📤 发送测试消息到: {self.webhook_url[:50]}...")
            
            response = requests.post(
                self.webhook_url,
                json=test_message,
                timeout=10
            )
            
            print(f"📥 HTTP 状态码: {response.status_code}")
            
            try:
                result = response.json()
                print(f"📋 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            except:
                result = {"raw_response": response.text}
                print(f"📋 原始响应: {response.text}")
                
            # 判断是否成功
            if response.status_code == 200:
                if isinstance(result, dict) and result.get("errcode") == 0:
                    self.print_result("消息发送", True, "消息发送成功！")
                    return True, result
                else:
                    error_code = result.get("errcode", "unknown")
                    error_msg = result.get("errmsg", "unknown error")
                    self.print_result("消息发送", False, 
                                    f"API 返回错误 - 错误码: {error_code}, 错误信息: {error_msg}")
                    return False, result
            else:
                self.print_result("消息发送", False, 
                                f"HTTP 请求失败 - 状态码: {response.status_code}")
                return False, result
                
        except requests.exceptions.Timeout:
            self.print_result("网络连接", False, "请求超时 (10秒)")
            return False, None
        except requests.exceptions.ConnectionError as e:
            self.print_result("网络连接", False, f"连接失败: {str(e)}")
            return False, None
        except Exception as e:
            self.print_result("网络连接", False, f"未知错误: {str(e)}")
            return False, None
            
    def test_markdown_message(self) -> bool:
        """测试 Markdown 格式消息"""
        self.print_header("测试 3: Markdown 消息格式")
        
        try:
            markdown_message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": """## 📊 Webhook 功能测试
                    
> 测试时间: 2026-02-11

### ✅ 测试项目
- [x] 文本消息
- [x] Markdown 格式
- [x] 链接支持

**测试结论**: Webhook 工作正常"""
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=markdown_message,
                timeout=10
            )
            
            result = response.json()
            
            if response.status_code == 200 and result.get("errcode") == 0:
                self.print_result("Markdown 消息", True, "Markdown 格式消息发送成功")
                return True
            else:
                error_msg = result.get("errmsg", "unknown")
                self.print_result("Markdown 消息", False, f"发送失败: {error_msg}")
                return False
                
        except Exception as e:
            self.print_result("Markdown 消息", False, f"测试异常: {str(e)}")
            return False
            
    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试摘要")
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\n📊 总测试数: {total}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"📈 通过率: {passed/total*100:.1f}%")
        
        if failed > 0:
            print("\n❌ 失败的测试:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"   - {result['test']}: {result['message']}")
                    
    def print_diagnosis(self):
        """打印诊断建议"""
        self.print_header("诊断建议")
        
        # 检查是否有失败的测试
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        if not failed_tests:
            print("\n🎉 所有测试通过！Webhook 工作正常。")
            return
            
        print("\n🔍 根据测试结果，可能的问题和解决方案:\n")
        
        # 分析失败原因
        for result in failed_tests:
            if "URL 为空" in result["message"]:
                print("❌ 问题: Webhook URL 未配置")
                print("   解决: 在 config.yaml 中配置正确的 webhook_url")
                print()
                
            elif "缺失" in result["message"]:
                print("❌ 问题: URL 格式不正确")
                print("   解决: 检查 URL 是否完整，应该类似:")
                print("   https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY")
                print()
                
            elif "错误码: 93000" in result["message"]:
                print("❌ 问题: Webhook Key 已失效 (错误码 93000)")
                print("   原因: 机器人可能被删除、重置，或群聊已解散")
                print("   解决方案:")
                print("   1. 在企业微信群聊中重新创建机器人")
                print("   2. 获取新的 Webhook URL")
                print("   3. 更新 config.yaml 中的 webhook_url")
                print()
                
            elif "超时" in result["message"]:
                print("❌ 问题: 网络连接超时")
                print("   解决: 检查网络连接和防火墙设置")
                print()
                
            elif "连接失败" in result["message"]:
                print("❌ 问题: 无法连接到企业微信服务器")
                print("   解决: 检查网络连接，确认可以访问 qyapi.weixin.qq.com")
                print()
                
        print("\n📚 参考文档:")
        print("   - 企业微信机器人文档: https://developer.work.weixin.qq.com/document/path/91770")
        print("   - 错误码查询: https://open.work.weixin.qq.com/devtool/query")
        
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🚀" * 30)
        print("  企业微信 Webhook 诊断工具")
        print("🚀" * 30)
        
        # 测试 1: URL 格式
        format_ok = self.test_url_format()
        
        # 测试 2: 连通性（只有格式正确才测试）
        if format_ok:
            connectivity_ok, response = self.test_connectivity()
            
            # 测试 3: Markdown 消息（只有连通性正常才测试）
            if connectivity_ok:
                self.test_markdown_message()
        else:
            print("\n⚠️  由于 URL 格式错误，跳过后续测试")
            
        # 打印摘要和诊断
        self.print_summary()
        self.print_diagnosis()


def load_config() -> Optional[str]:
    """从配置文件加载 Webhook URL"""
    config_path = project_root / "config" / "config.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('wecom', {}).get('webhook_url', '')
    except Exception as e:
        print(f"❌ 无法读取配置文件: {e}")
        return None


def main():
    """主函数"""
    print("\n选择测试模式:")
    print("1. 从配置文件读取 Webhook URL (推荐)")
    print("2. 手动输入 Webhook URL")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        webhook_url = load_config()
        if not webhook_url:
            print("❌ 配置文件中未找到 webhook_url")
            return
        print(f"\n✅ 从配置文件加载 URL: {webhook_url[:50]}...")
    elif choice == "2":
        webhook_url = input("\n请输入 Webhook URL: ").strip()
    else:
        print("❌ 无效的选择")
        return
        
    # 运行测试
    tester = WeComWebhookTester(webhook_url)
    tester.run_all_tests()
    
    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
