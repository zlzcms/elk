# -*- coding: utf-8 -*-
# @Author: zhujinlong
# @Date:   2025-11-27 20:59:21
# @Last Modified by:   zhujinlong
# @Last Modified time: 2025-11-28 02:12:44
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

from flask import Flask, Response, render_template, request

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PIPELINE = BASE_DIR / "pipeline" / "logstash.conf"

PIPELINE_PATH = Path(os.environ.get("LOGSTASH_PIPELINE_PATH", DEFAULT_PIPELINE))
BACKUP_DIR = Path(os.environ.get("LOGSTASH_BACKUP_DIR", PIPELINE_PATH.parent / "backups"))
# 重启命令示例：
# - systemd: sudo systemctl restart logstash
# - Docker: docker restart logstash (需要挂载 docker.sock 或使用 docker-compose exec)
# - Docker Compose: docker-compose restart logstash
RESTART_CMD = os.environ.get("LOGSTASH_RESTART_CMD", "")
# 测试命令示例（使用 {config} 作为占位符，会被自动替换为配置文件路径）：
# - 本地: /usr/share/logstash/bin/logstash --config.test_and_exit -f {config}
# - Docker: docker exec logstash /usr/share/logstash/bin/logstash --config.test_and_exit -f /usr/share/logstash/pipeline/logstash.conf
TEST_CMD = os.environ.get("LOGSTASH_TEST_CMD", "")
LOG_PATH = Path(os.environ.get("LOGSTASH_LOG_PATH", BASE_DIR / "logs" / "logstash-plain.log"))
LOG_MAX_BYTES = int(os.environ.get("LOGSTASH_LOG_MAX_BYTES", 200_000))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me")


def read_config() -> str:
    if PIPELINE_PATH.exists():
        return PIPELINE_PATH.read_text()
    return ""


def write_config(content: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"logstash.conf.{timestamp}.bak"
    if PIPELINE_PATH.exists():
        backup_path.write_text(PIPELINE_PATH.read_text())
    PIPELINE_PATH.write_text(content)
    return backup_path


def run_shell(command: str) -> Dict[str, str]:
    if not command or not command.strip():
        return {"status": "skipped", "output": "未配置命令，跳过执行。"}
    
    # 验证命令格式，避免执行无效命令
    command = command.strip()
    if command in [":", ";;", "&&", "||"] or len(command) < 2:
        return {"status": "failed (无效命令)", "output": f"命令格式无效：{command}\n\n请检查环境变量 LOGSTASH_TEST_CMD 或 LOGSTASH_RESTART_CMD 的配置。"}
    
    try:
        proc = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=60  # 60秒超时
        )
        status = "ok" if proc.returncode == 0 else f"failed ({proc.returncode})"
        # 合并 stdout 和 stderr，优先显示错误信息
        output_parts = []
        if proc.stderr.strip():
            output_parts.append(f"[错误输出]\n{proc.stderr.strip()}")
        if proc.stdout.strip():
            output_parts.append(f"[标准输出]\n{proc.stdout.strip()}")
        output = "\n\n".join(output_parts) if output_parts else "(无输出)"
        return {"status": status, "output": output}
    except subprocess.TimeoutExpired:
        return {"status": "failed (超时)", "output": "命令执行超时（超过60秒）"}
    except Exception as e:
        return {"status": "failed (异常)", "output": f"执行命令时发生异常：{str(e)}"}


def read_log_tail() -> str:
    """读取日志文件尾部内容，如果文件不存在则尝试查找其他可能的日志文件"""
    # 首先尝试指定的路径
    if LOG_PATH.exists():
        try:
            size = LOG_PATH.stat().st_size
            if size == 0:
                return "日志文件存在但为空。\n\n提示：Logstash 可能刚启动，还没有生成日志内容。"
            start = max(size - LOG_MAX_BYTES, 0)
            with LOG_PATH.open("rb") as fh:
                fh.seek(start)
                data = fh.read().decode(errors="replace")
            return data or "日志文件为空。"
        except Exception as e:
            return f"读取日志文件时出错：{e}"
    
    # 如果指定路径不存在，尝试查找同目录下的其他日志文件
    log_dir = LOG_PATH.parent
    if log_dir.exists():
        # 尝试查找常见的日志文件名
        possible_names = [
            "logstash-plain.log",
            "logstash.log",
            "logstash-plain.json",
            "logstash.json",
        ]
        for name in possible_names:
            possible_path = log_dir / name
            if possible_path.exists():
                try:
                    size = possible_path.stat().st_size
                    if size == 0:
                        return f"找到日志文件但为空：{possible_path}\n\n提示：Logstash 可能刚启动，还没有生成日志内容。"
                    start = max(size - LOG_MAX_BYTES, 0)
                    with possible_path.open("rb") as fh:
                        fh.seek(start)
                        data = fh.read().decode(errors="replace")
                    return f"注意：使用了备用日志文件 {possible_path}\n\n{data}"
                except Exception as e:
                    continue
        
        # 列出目录中的所有文件，帮助调试
        try:
            files = list(log_dir.iterdir())
            file_list = "\n".join([f"  - {f.name}" for f in files if f.is_file()])
            if file_list:
                return f"日志文件不存在：{LOG_PATH}\n\n目录 {log_dir} 中的文件：\n{file_list}\n\n提示：\n1. 请确认 Logstash 服务正在运行\n2. 检查 Logstash 的日志配置\n3. 如果 Logstash 刚启动，可能需要等待一段时间才会生成日志"
            else:
                return f"日志文件不存在：{LOG_PATH}\n\n目录 {log_dir} 为空。\n\n提示：\n1. 请确认 Logstash 服务正在运行\n2. 检查日志目录挂载是否正确\n3. 如果 Logstash 刚启动，可能需要等待一段时间才会生成日志"
        except Exception as e:
            return f"无法访问日志目录 {log_dir}：{e}"
    
    return f"日志文件不存在：{LOG_PATH}\n\n提示：\n1. 请确认 Logstash 服务正在运行\n2. 检查环境变量 LOGSTASH_LOG_PATH 是否正确\n3. 检查日志目录挂载是否正确\n4. 如果 Logstash 刚启动，可能需要等待一段时间才会生成日志"


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    error = ""
    validation = {}
    restart = {}
    content = read_config()

    if request.method == "POST":
        new_content = request.form.get("config", "")
        if not new_content.strip():
            error = "配置内容为空，未保存。"
        else:
            backup_path = write_config(new_content)
            content = new_content
            
            # 检查并执行测试命令
            if TEST_CMD and TEST_CMD.strip():
                try:
                    # 格式化命令，替换 {config} 占位符
                    test_command = TEST_CMD.strip().format(config=str(PIPELINE_PATH))
                    validation = run_shell(test_command)
                except KeyError as e:
                    # 如果命令中没有 {config} 占位符，直接使用原命令
                    validation = run_shell(TEST_CMD.strip())
                except Exception as e:
                    validation = {"status": "failed (格式错误)", "output": f"命令格式错误：{str(e)}\n\n请检查环境变量 LOGSTASH_TEST_CMD 的配置，确保格式正确。\n例如：/usr/share/logstash/bin/logstash --config.test_and_exit -f {{config}}"}
            else:
                validation = {"status": "skipped", "output": "未配置测试命令，跳过配置验证，直接保存。"}
            
            if validation.get("status", "").startswith("failed"):
                error = f"配置测试失败，已回滚到：{backup_path.name}"
                PIPELINE_PATH.write_text(Path(backup_path).read_text())
            else:
                # 配置测试通过或跳过，执行重启
                if RESTART_CMD and RESTART_CMD.strip():
                    restart = run_shell(RESTART_CMD.strip())
                    if restart.get("status", "").startswith("failed"):
                        error = "Logstash 重启失败，请检查日志。配置已保存，但需要手动重启 Logstash。"
                    else:
                        message = "配置保存并重启成功。"
                else:
                    # 没有配置重启命令，只保存配置
                    message = "配置保存成功。注意：未配置重启命令，请手动重启 Logstash 使配置生效。"

    last_modified = PIPELINE_PATH.stat().st_mtime if PIPELINE_PATH.exists() else None
    return render_template(
        "index.html",
        content=content,
        message=message,
        error=error,
        validation=validation,
        restart=restart,
        pipeline_path=str(PIPELINE_PATH),
        last_modified=last_modified,
        log_path=str(LOG_PATH),
    )


@app.get("/logs")
def logs():
    return Response(read_log_tail(), mimetype="text/plain")


@app.template_filter("datetimeformat")
def datetimeformat(value):
    if not value:
        return ""
    return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

