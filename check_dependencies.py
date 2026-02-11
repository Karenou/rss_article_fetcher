#!/usr/bin/env python3
"""Check if all required dependencies are installed."""

import sys

# Define required packages with their import names
REQUIRED_PACKAGES = {
    'feedparser': 'feedparser',
    'requests': 'requests',
    'beautifulsoup4': 'bs4',
    'pyyaml': 'yaml',
    'python-dateutil': 'dateutil',
    'google-generativeai': 'google.generativeai',
    'langdetect': 'langdetect',
    'APScheduler': 'apscheduler',
    'newspaper3k': 'newspaper',
    'lxml': 'lxml',
    'pytz': 'pytz'
}

def check_package(package_name, import_name):
    """Check if a package is installed."""
    try:
        __import__(import_name)
        return True, None
    except ImportError as e:
        return False, str(e)

def main():
    """Main function to check all dependencies."""
    print("=" * 60)
    print("检查 RSS Article Fetcher 依赖包安装状态")
    print("=" * 60)
    print()
    
    installed = []
    missing = []
    
    for package_name, import_name in REQUIRED_PACKAGES.items():
        status, error = check_package(package_name, import_name)
        
        if status:
            installed.append(package_name)
            print(f"✓ {package_name:25s} - 已安装")
        else:
            missing.append(package_name)
            print(f"✗ {package_name:25s} - 未安装")
    
    print()
    print("=" * 60)
    print(f"总计: {len(REQUIRED_PACKAGES)} 个依赖包")
    print(f"已安装: {len(installed)} 个")
    print(f"未安装: {len(missing)} 个")
    print("=" * 60)
    
    if missing:
        print()
        print("❌ 发现缺失的依赖包！")
        print()
        print("请运行以下命令安装缺失的依赖包：")
        print()
        print("  python3 -m pip install -r requirements.txt")
        print()
        print("或者单独安装缺失的包：")
        print()
        print(f"  python3 -m pip install {' '.join(missing)}")
        print()
        return 1
    else:
        print()
        print("✅ 所有依赖包已正确安装！")
        print()
        print("您可以运行以下命令开始使用：")
        print()
        print("  python3 main.py --help")
        print()
        return 0

if __name__ == "__main__":
    sys.exit(main())
