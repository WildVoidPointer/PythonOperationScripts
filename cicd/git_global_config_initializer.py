#!/usr/bin/env python3
"""
Git 全局配置初始化脚本 - 跨平台版本
支持 Windows / macOS / Linux
"""
from datetime import datetime
from pathlib import Path
from enum import StrEnum
import subprocess
import platform
import argparse
import shutil
import sys
import os


class PlatformType(StrEnum):
    WINDOWS = "windows"
    MACOS = "darwin"
    LINUX = "linux"


class GitConfigInitializerUtils:
    class LoggingLevel(StrEnum):
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"

    @staticmethod
    def logging_println(level: LoggingLevel, message: str):
        """统一日志输出格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} - [{level}] - {message}")


class GitConfigInitializer:
    def __init__(self, interactive: bool = True):
        self.interactive = interactive
        self.system = platform.system().lower()
        self.home = Path.home()
        self.gitconfig_backup = self.home / '.gitconfig.backup'
        self.global_gitignore = self.home / '.gitignore_global'

    def check_command_exists(self, cmd: str) -> bool:
        """检查命令是否存在于系统中"""
        code, _, _ = self.run_command(
            ['where', cmd] 
            if self.system == PlatformType.WINDOWS else ['which', cmd]
        )
        return code == 0
        
    def run_command(self, cmd: list[str], check: bool = False) -> tuple[int, str, str]:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=check,
                encoding='utf-8'
            )
            return result.returncode, result.stdout, result.stderr
        except FileNotFoundError:
            return 127, '', f"Command not found: {cmd[0]}"
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
    
    def check_git_installed(self) -> bool:
        """检查 Git 是否已安装"""
        is_exists: bool = self.check_command_exists('git')
        if not is_exists:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.ERROR, 
                f"Git is not installed or is not in the PATH"
            )
            return False
            
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Git is installed and available in the PATH"
        )
        return True
    
    def backup_global_gitconfig(self) -> bool:
        """备份现有的 .gitconfig"""
        gitconfig_path = self.home / '.gitconfig'
        if gitconfig_path.exists():
            if self.interactive:
                response = input(
                    f"If the existing configuration file {gitconfig_path} "
                    "is found, should it be backed up? [y/N]"
                ).lower()
                if response != 'y':
                    return True
            
            try:
                shutil.copy2(gitconfig_path, self.gitconfig_backup)
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.INFO,
                    "The globally ignored configuration file has been "
                    f"backed up to:  {self.gitconfig_backup}"
                )
                return True
            except Exception as e:
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.WARNING,
                    f"Failed to backup .gitconfig: {e}"
                )

                if self.interactive:
                    response = input("Shall we continue? [y/N] ").lower()
                    return response == 'y'
                return False
        return True
    
    def get_user_input(self, prompt: str, default: str = "") -> str:
        """获取用户输入"""
        if not self.interactive:
            return default
        
        if default:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        value = input(prompt).strip()
        return value if value else default
    
    def set_git_config(self, key: str, value: str) -> bool:
        """设置 Git 配置"""
        code, _, stderr = self.run_command(
            ['git', 'config', '--global', key, value]
        )
        if code == 0:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                f"Configuration has been completed: {key} = {value}"
            )
            return True
        else:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.ERROR,
                f"Configuration write failed {key}: {stderr}"
            )
            return False
    
    def configure_basic_identity(self):
        """配置用户身份信息"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Configure user identity information"
        )
        
        name = self.get_user_input(
            "Please enter your name", 
            os.environ.get('GIT_AUTHOR_NAME', '')
        )
        email = self.get_user_input(
            "Please enter your email", 
            os.environ.get('GIT_AUTHOR_EMAIL', '')
        )
        
        if name:
            self.set_git_config('user.name', name)
        if email:
            self.set_git_config('user.email', email)
    
    def configure_line_endings(self):
        """配置行尾符 (跨平台关键)"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Configure line tail character processing"
        )
        
        if self.system == PlatformType.WINDOWS:
            # Windows: 提交时转LF，检出时转CRLF
            autocrlf = 'true'
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                "The line break behavior is being set for the Windows system"
            )
        else:
            # macOS/Linux: 提交时转LF，检出时不转
            autocrlf = 'input'
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                f"The line break behavior is being set for the {platform.system()} system"
            )
        
        self.set_git_config('core.autocrlf', autocrlf)
        
        # 大小写敏感处理
        if self.system == PlatformType.MACOS:  # macOS
            self.set_git_config('core.precomposeunicode', 'true')
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                "Unicode filename support is being enabled for the macOS system"
            )
        
        # 默认关闭大小写不敏感
        self.set_git_config('core.ignorecase', 'false')
    
    def configure_default_editor(self):
        """配置默认编辑器"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Configure default editor"
        )
        
        # 尝试检测常见编辑器
        editors = []
        
        if self.system == PlatformType.WINDOWS:
            editors: list[tuple[str, str]] = [
                ('code', 'VS Code'),
                ('notepad', '记事本'),
                ('vim', 'Vim')
            ]
        elif self.system == PlatformType.MACOS:  # macOS
            editors: list[tuple[str, str]] = [
                ('code', 'VS Code'),
                ('vim', 'Vim'),
                ('nano', 'Nano')
            ]
        else:  # Linux
            editors: list[tuple[str, str]] = [
                ('code', 'VS Code'),
                ('vim', 'Vim'),
                ('nano', 'Nano'),
                ('emacs', 'Emacs')
            ]
        
        # 检测已安装的编辑器
        available: list[tuple[str, str]] = []
        for cmd, name in editors:
            if cmd.startswith('code'):
                # 检查 VS Code 是否在 PATH 中
                is_exists: bool = self.check_command_exists('code')
                if is_exists:
                    available.append((cmd, name))
            else:
                # 检查其他编辑器
                is_exists: bool = self.check_command_exists(cmd.split()[0])
                if is_exists or cmd in ['vim', 'nano', 'emacs']:
                    available.append((cmd, name))
        
        if available:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                "The following text editor has been detected"
            )

            for i, (_, name) in enumerate(available, 1):
                print(f"    {i}. {name}")
            
            if self.interactive:
                choice = self.get_user_input(
                    "Select the text editor (input the order)", 
                    "1"
                )
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(available):
                        editor_cmd = available[idx][0]
                        self.set_git_config('core.editor', editor_cmd)
                except ValueError:
                    self.set_git_config('core.editor', available[0][0])
            else:
                self.set_git_config('core.editor', available[0][0])
        else:
            # 默认编辑器
            default_editor: str = 'vim' if self.system != 'windows' else 'notepad'
            self.set_git_config('core.editor', default_editor)
    

    def configure_aliases(self):
        """配置常用别名"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Configure common aliases"
        )
        
        aliases: dict[str, str] = {
            'co': 'checkout',
            'br': 'branch',
            'ci': 'commit',
            'st': 'status -s',
            'lg': "log --graph --pretty=format:'%Cred%h%Creset -%C(yellow)%d"
                "%Creset %s %Cgreen(%cr) %C(bold blue)<%an>%Creset' "
                "--abbrev-commit",
            'unstage': 'reset HEAD --',
            'last': 'log -1 HEAD',
            'tree': 'log --graph --oneline --all',
            'df': 'diff',
            'dfs': 'diff --staged'
        }
        
        if self.interactive:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                "The following aliases will be configured:"
            )
            for alias, cmd in aliases.items():
                print(f"    git {alias} -> git {cmd}")

            response = self.get_user_input(
                "Whether to configure the above aliases? [Y/n]", "Y")
            
            if response.lower() == 'n':
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.INFO,
                    "Skipping alias configuration"
                )
                return
        
        for alias, cmd in aliases.items():
            self.set_git_config(f'alias.{alias}', cmd)
    
    def configure_optimizations(self):
        """配置工作流优化选项"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Configure workflow optimizations"
        )
        
        # 默认分支名称
        default_branch = self.get_user_input(
            "Please enter the default branch name", 
            "main"
        )
        self.set_git_config('init.defaultBranch', default_branch)
        
        # push.autoSetupRemote
        self.set_git_config('push.autoSetupRemote', 'true')
        
        # pull.rebase
        self.set_git_config('pull.rebase', 'true')
        
        # 颜色输出
        self.set_git_config('color.ui', 'auto')
        
        # 中文文件名显示
        self.set_git_config('core.quotepath', 'false')
        
        # 帮助自动纠正
        self.set_git_config('help.autocorrect', '1')
    
    def create_global_gitignore(self):
        """创建全局 .gitignore"""
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Create global .gitignore file"
        )
        
        if not self.global_gitignore.exists():
            ignore_content = """# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
*.swp
*.swo
*~
desktop.ini

# IDE files
.vscode/
.idea/
*.suo
*.user
*.sln.docstates

# Logs and databases
*.log
*.sql
*.sqlite
"""
            try:
                self.global_gitignore.write_text(ignore_content, encoding='utf-8')
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.INFO,
                    f"Create global .gitignore file: {self.global_gitignore}"
                )
            except Exception as e:
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.ERROR,
                    f"Failed to create global .gitignore file: {e}"
                )
                return
        
        self.set_git_config('core.excludesfile', str(self.global_gitignore))
    
    def show_config_summary(self):
        """显示最终配置摘要"""
        print("\n" + "="*60)
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Show final configuration summary"
        )
        print("="*60)
        
        # 获取关键配置
        configs = [
            'user.name',
            'user.email',
            'core.autocrlf',
            'core.editor',
            'init.defaultBranch',
            'push.autoSetupRemote',
            'pull.rebase',
            'color.ui',
            'core.quotepath'
        ]
        
        for key in configs:
            code, stdout, _ = self.run_command(
                ['git', 'config', '--global', '--get', key]
            )
            if code == 0 and stdout.strip():
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.INFO,
                    f"  {key}: {stdout.strip()}"
                )
            else:
                GitConfigInitializerUtils.logging_println(
                    GitConfigInitializerUtils.LoggingLevel.INFO,
                    f"  {key}: Not set"
                )
        
        # 显示别名
        code, stdout, _ = self.run_command(
            ['git', 'config', '--global', '--get-regexp', '^alias\\.']
        )
        if code == 0 and stdout:
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                "Git alias has been configured as follows:"
            )
            for line in stdout.strip().split('\n'):
                alias, cmd = line.split(' ', 1)
                print(f"    {alias.replace('alias.', 'git ')} = {cmd}")
    
    def run(self):
        """主执行流程"""
        print("="*60)
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Starting Git global configuration initialization"
        )
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            f"Operating system detected: {platform.system()}"
        )
        print("="*60)
        
        # 1. 检查环境
        if not self.check_git_installed():
            return False
        
        # 2. 备份现有配置
        if not self.backup_global_gitconfig():
            return False
        
        # 3. 执行各项配置
        self.configure_basic_identity()
        self.configure_line_endings()
        self.configure_default_editor()
        self.configure_aliases()
        self.configure_optimizations()
        self.create_global_gitignore()
        
        # 4. 显示摘要
        self.show_config_summary()
        
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            "Git configuration completed!"
        )
        GitConfigInitializerUtils.logging_println(
            GitConfigInitializerUtils.LoggingLevel.INFO,
            f"Configuration file location: {self.home / '.gitconfig'}"
        )
        if self.gitconfig_backup.exists():
            GitConfigInitializerUtils.logging_println(
                GitConfigInitializerUtils.LoggingLevel.INFO,
                f"Backup file location: {self.gitconfig_backup}"
            )
        
        return True


def main():
    """入口函数: 简单 GNU 风格命令行参数解析"""
    
    parser = argparse.ArgumentParser(description='Git 全局配置初始化脚本')
    parser.add_argument(
        '--non-interactive', 
        action='store_true', 
        help='非交互模式 (使用默认值)'
    )
    parser.add_argument('--name', type=str, help='用户名')
    parser.add_argument('--email', type=str, help='用户邮箱')
    
    args = parser.parse_args()
    
    # 设置环境变量供脚本读取
    if args.name:
        os.environ['GIT_AUTHOR_NAME'] = args.name
    if args.email:
        os.environ['GIT_AUTHOR_EMAIL'] = args.email
    
    initializer = GitConfigInitializer(interactive=not args.non_interactive)
    success = initializer.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
