  这种方案最实用，不需要额外的服务器或Redis，纯文件状态通信即可。

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  📁 文件结构

  my_skill/
  ├── SKILL.md                    # Skill说明文档
  ├── task_manager.py             # 任务管理器（核心）
  ├── long_task.py                # 你的长时间任务
  └── tasks/                      # 状态文件存放目录（自动创建）
      └── task_xxx.status.json

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  1. task_manager.py - 核心调度器

  """
  长时间任务管理器 - 支持后台运行、进度监控、自动回调
  """

  import subprocess
  import json
  import time
  import os
  import signal
  import sys
  from datetime import datetime
  from pathlib import Path
  from typing import Callable, Optional, Dict, Any

  # 状态文件目录
  TASKS_DIR = Path(__file__).parent / "tasks"
  TASKS_DIR.mkdir(exist_ok=True)


  class TaskManager:
      def __init__(self):
          self.tasks_dir = TASKS_DIR
          self.active_monitors = {}  # 记录正在监控的任务

      def _get_status_file(self, task_id: str) -> Path:
          """获取任务状态文件路径"""
          return self.tasks_dir / f"{task_id}.status.json"

      def _get_pid_file(self, task_id: str) -> Path:
          """获取任务PID文件路径"""
          return self.tasks_dir / f"{task_id}.pid"

      def start_task(self, task_id: str, script_path: str, *args) -> Dict[str, Any]:
          """
          启动一个长时间任务

          Args:
              task_id: 任务唯一标识
              script_path: 要执行的Python脚本路径
              *args: 传递给脚本的参数

          Returns:
              任务初始状态
          """
          status_file = self._get_status_file(task_id)
          pid_file = self._get_pid_file(task_id)

          # 如果任务已存在且在运行，返回状态
          if self.is_running(task_id):
              return self.get_status(task_id)

          # 初始化状态文件
          initial_status = {
              "task_id": task_id,
              "status": "starting",  # starting / running / completed / failed / cancelled
              "progress": 0,
              "message": "任务启动中...",
              "result": None,
              "error": None,
              "created_at": datetime.now().isoformat(),
              "updated_at": datetime.now().isoformat(),
              "script": script_path,
              "args": list(args)
          }
          self._save_status(task_id, initial_status)

          # 构建命令
          cmd = [sys.executable, script_path, task_id, *map(str, args)]

          # 后台启动进程
          # Windows下用creationflags，Linux/Mac用preexec_fn
          kwargs = {}
          if os.name == 'nt':  # Windows
              kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
          else:  # Linux/Mac
              kwargs['start_new_session'] = True

          process = subprocess.Popen(
              cmd,
              stdout=subprocess.PIPE,
              stderr=subprocess.PIPE,
              **kwargs
          )

          # 记录PID
          pid_file.write_text(str(process.pid))

          # 更新状态为运行中
          self._update_status(task_id, {
              "status": "running",
              "message": "任务运行中",
              "pid": process.pid
          })

          print(f"[{task_id}] 任务已启动，PID: {process.pid}")
          return self.get_status(task_id)

      def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
          """获取任务状态"""
          status_file = self._get_status_file(task_id)
          if not status_file.exists():
              return None
          try:
              with open(status_file, 'r', encoding='utf-8') as f:
                  return json.load(f)
          except Exception as e:
              return {"task_id": task_id, "status": "error", "error": str(e)}

      def is_running(self, task_id: str) -> bool:
          """检查任务是否正在运行"""
          status = self.get_status(task_id)
          if not status:
              return False
          return status.get("status") in ["starting", "running"]

      def is_completed(self, task_id: str) -> bool:
          """检查任务是否已完成"""
          status = self.get_status(task_id)
          if not status:
              return False
          return status.get("status") in ["completed", "failed", "cancelled"]

      def _save_status(self, task_id: str, status: Dict):
          """保存任务状态到文件"""
          status_file = self._get_status_file(task_id)
          with open(status_file, 'w', encoding='utf-8') as f:
              json.dump(status, f, ensure_ascii=False, indent=2)

      def _update_status(self, task_id: str, updates: Dict):
          """更新任务状态"""
          status = self.get_status(task_id) or {}
          status.update(updates)
          status["updated_at"] = datetime.now().isoformat()
          self._save_status(task_id, status)

      def wait_for_completion(
          self,
          task_id: str,
          check_interval: int = 5,
          progress_callback: Optional[Callable[[Dict], None]] = None,
          timeout: Optional[int] = None
      ) -> Dict[str, Any]:
          """
          阻塞等待任务完成，定期报告进度

          Args:
              task_id: 任务ID
              check_interval: 检查间隔（秒）
              progress_callback: 进度回调函数，接收状态字典
              timeout: 超时时间（秒），None表示不超时

          Returns:
              最终状态
          """
          start_time = time.time()

          print(f"[{task_id}] 开始监控任务...")

          while True:
              status = self.get_status(task_id)

              if not status:
                  raise RuntimeError(f"任务 {task_id} 不存在")

              # 报告进度
              if progress_callback:
                  progress_callback(status)
              else:
                  # 默认打印进度
                  progress = status.get("progress", 0)
                  message = status.get("message", "")
                  print(f"[{task_id}] {progress}% - {message}")

              # 检查是否完成
              if status.get("status") in ["completed", "failed", "cancelled"]:
                  if status["status"] == "completed":
                      print(f"[{task_id}] ✅ 任务完成！")
                  elif status["status"] == "failed":
                      print(f"[{task_id}] ❌ 任务失败: {status.get('error')}")
                  else:
                      print(f"[{task_id}] ⚠️ 任务已取消")
                  return status

              # 检查超时
              if timeout and (time.time() - start_time) > timeout:
                  raise TimeoutError(f"任务 {task_id} 执行超时")

              time.sleep(check_interval)

      def cancel_task(self, task_id: str) -> bool:
          """取消正在运行的任务"""
          status = self.get_status(task_id)
          if not status or status.get("status") != "running":
              return False

          pid = status.get("pid")
          if pid:
              try:
                  if os.name == 'nt':  # Windows
                      os.kill(pid, signal.CTRL_BREAK_EVENT)
                  else:
                      os.kill(pid, signal.SIGTERM)
              except ProcessLookupError:
                  pass

          self._update_status(task_id, {
              "status": "cancelled",
              "message": "任务已被取消"
          })
          print(f"[{task_id}] 任务已取消")
          return True

      def list_tasks(self) -> list:
          """列出所有任务"""
          tasks = []
          for f in self.tasks_dir.glob("*.status.json"):
              task_id = f.stem.replace(".status", "")
              status = self.get_status(task_id)
              if status:
                  tasks.append(status)
          return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)

      def cleanup_old_tasks(self, days: int = 7):
          """清理旧任务文件"""
          cutoff = time.time() - (days * 24 * 60 * 60)
          for f in self.tasks_dir.glob("*"):
              if f.stat().st_mtime < cutoff:
                  f.unlink()
                  print(f"已清理旧文件: {f.name}")


  # ============ AI 交互便捷函数 ============

  def run_and_monitor(
      task_id: str,
      script_path: str,
      *args,
      check_interval: int = 5,
      auto_continue: Optional[Callable[[Dict], None]] = None
  ) -> Dict[str, Any]:
      """
      一站式函数：启动任务并监控到完成

      这是给AI/Skill用的主要接口

      Args:
          task_id: 任务唯一ID
          script_path: 要执行的脚本
          *args: 脚本参数
          check_interval: 检查间隔（秒）
          auto_continue: 任务完成后自动执行的回调函数

      Returns:
          任务最终状态
      """
      manager = TaskManager()

      # 启动任务
      status = manager.start_task(task_id, script_path, *args)

      if status.get("status") == "running" and status.get("progress", 0) > 0:
          print(f"任务 {task_id} 已在运行中，继续监控...")

      # 监控直到完成
      final_status = manager.wait_for_completion(
          task_id,
          check_interval=check_interval,
          progress_callback=lambda s: print(
              f"⏳ [{task_id}] 进度: {s.get('progress', 0)}% | {s.get('message', '处理中...')}"
          )
      )

      # 自动执行下一步
      if auto_continue and final_status.get("status") == "completed":
          print(f"\n🚀 任务完成，执行下一步...")
          auto_continue(final_status.get("result"))

      return final_status


  if __name__ == "__main__":
      # 测试用法
      manager = TaskManager()

      # 示例：启动任务
      # manager.start_task("test_001", "long_task.py", "arg1", "arg2")

      # 示例：查看状态
      print(manager.list_tasks())

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  2. long_task.py - 长时间任务模板

  #!/usr/bin/env python3
  """
  长时间任务示例 - 需要能够被task_manager管理
  """

  import sys
  import time
  import json
  from pathlib import Path

  # 导入状态管理（可选，也可以自己实现简单的状态写入）
  TASKS_DIR = Path(__file__).parent / "tasks"


  def update_progress(task_id: str, progress: int, message: str, result=None):
      """更新任务进度"""
      status_file = TASKS_DIR / f"{task_id}.status.json"

      status = {
          "task_id": task_id,
          "status": "running" if progress < 100 else "completed",
          "progress": progress,
          "message": message,
          "result": result,
          "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
      }

      if progress >= 100:
          status["status"] = "completed"
          status["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

      TASKS_DIR.mkdir(exist_ok=True)
      with open(status_file, 'w', encoding='utf-8') as f:
          json.dump(status, f, ensure_ascii=False, indent=2)


  def main():
      if len(sys.argv) < 2:
          print("用法: python long_task.py <task_id> [其他参数...]")
          sys.exit(1)

      task_id = sys.argv[1]
      other_args = sys.argv[2:]  # 其他传入的参数

      print(f"[{task_id}] 任务开始，参数: {other_args}")

      try:
          # ========== 你的实际任务逻辑 ==========

          # 回测分阶段处理
          stages = [
              (10, "正在初始化...", None),
              (25, "正在加载数据...", None),
              (40, "正在处理数据第一部分...", None),
              (60, "正在执行核心计算...", None),
              (80, "正在生成报告...", None),
              (95, "正在保存结果...", None),
              (100, "任务完成！", {"output_file": f"result_{task_id}.csv", "rows": 1000})
          ]

          for progress, message, result in stages:
              update_progress(task_id, progress, message)
              print(f"[{task_id}] {progress}% - {message}")
              time.sleep(3)  # 回测长时间工作

          # ========== 任务结束 ==========

          print(f"[{task_id}] ✅ 全部完成！")

      except Exception as e:
          # 错误处理
          status_file = TASKS_DIR / f"{task_id}.status.json"
          error_status = {
              "task_id": task_id,
              "status": "failed",
              "progress": 0,
              "message": f"错误: {str(e)}",
              "error": str(e),
              "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")
          }
          with open(status_file, 'w', encoding='utf-8') as f:
              json.dump(error_status, f, ensure_ascii=False, indent=2)
          print(f"[{task_id}] ❌ 失败: {e}")
          sys.exit(1)


  if __name__ == "__main__":
      main()

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  3. 在Skill中使用

  # your_skill.py
  from task_manager import run_and_monitor, TaskManager

  def step1_prepare():
      """步骤1：准备工作"""
      print("步骤1: 准备数据...")
      return {"ready": True}

  def step3_analyze(result):
      """步骤3：分析结果（任务完成后自动调用）"""
      print(f"步骤3: 分析任务结果: {result}")
      # 你的后续逻辑...

  def run_full_workflow():
      """完整工作流"""

      # 步骤1
      data = step1_prepare()

      # 步骤2: 启动长时间任务并等待完成
      # AI会在这里实时看到进度，任务完成后自动调用step3
      final_status = run_and_monitor(
          task_id="data_processing_001",
          script_path="long_task.py",
          "arg1", "arg2",  # 传递给你的脚本的参数
          check_interval=5,  # 每5秒检查一次进度
          auto_continue=step3_analyze  # 完成后自动执行
      )

      if final_status["status"] != "completed":
          print("任务失败，停止后续步骤")
          return

      # 如果不用auto_continue，也可以在这里手动调用
      # step3_analyze(final_status["result"])

      print("全部流程完成！")

  # 其他便捷用法

  def check_task_status(task_id):
      """查看某个任务的状态"""
      manager = TaskManager()
      status = manager.get_status(task_id)
      print(f"任务状态: {status}")

  def list_all_tasks():
      """列出所有历史任务"""
      manager = TaskManager()
      tasks = manager.list_tasks()
      for t in tasks:
          print(f"{t['task_id']}: {t['status']} ({t.get('progress', 0)}%)")

  def continue_existing_task(task_id):
      """继续监控一个已启动的任务"""
      manager = TaskManager()

      if not manager.is_running(task_id):
          print(f"任务 {task_id} 未在运行")
          return manager.get_status(task_id)

      final_status = manager.wait_for_completion(
          task_id,
          progress_callback=lambda s: print(f"进度: {s['progress']}%")
      )

      if final_status["status"] == "completed":
          step3_analyze(final_status["result"])

      return final_status

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  4. SKILL.md 写法示例

  # My Long Task Skill

  ## 功能
  执行长时间数据处理任务，并自动进行后续分析

  ## 用法

  ### 启动完整流程
  ```python
  from your_skill import run_full_workflow
  run_full_workflow()
  ```

  ### 只启动后台任务（不等待）
  ```python
  from task_manager import TaskManager
  manager = TaskManager()
  manager.start_task("my_task", "long_task.py", "arg1")
  # 任务在后台运行，AI可以去做其他事情
  ```

  ### 稍后继续监控
  ```python
  from your_skill import continue_existing_task
  continue_existing_task("my_task")
  ```

  ### 查看所有任务
  ```python
  from task_manager import TaskManager
  TaskManager().list_tasks()
  ```

  ## 工作流程

  1. **准备阶段** - AI执行
  2. **长时间任务** - 后台运行，自动报告进度
  3. **自动后续** - 任务完成后AI自动执行分析
  4. **结果汇总** - AI报告最终结果

  ## 状态说明

  - `starting` - 任务启动中
  - `running` - 正在运行
  - `completed` - 成功完成 ✅
  - `failed` - 执行失败 ❌
  - `cancelled` - 已取消 ⚠️

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  5. AI交互示例

  用户在对话中可以这样使用：

  用户: 帮我处理这个大数据文件
  AI: 好的，启动长时间任务...

  [data_001] 任务已启动，PID: 12345
  ⏳ [data_001] 进度: 10% | 正在初始化...
  ⏳ [data_001] 进度: 25% | 正在加载数据...
  ...（等待中，AI可以回答其他问题）...
  ⏳ [data_001] 进度: 100% | 任务完成！

  🚀 任务完成，执行下一步...
  步骤3: 分析任务结果: {'output_file': 'result_data_001.csv', 'rows': 1000}
  全部流程完成！

  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  这个方案的优势：

  • ✅ 纯Python，无外部依赖（除标准库）
  • ✅ 支持Windows/Linux/Mac
  • ✅ 任务状态持久化，可随时查看
  • ✅ 支持中断和恢复监控
  • ✅ AI可以"离开"去做其他事，回来继续监控

    ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
    6. 最新实践（2026-02，brain-enhance-template 已落地）

    下面是已经在线上 skill 中验证过的更稳方案，重点是“后台启动 + 可查询状态 + 日志落盘 + 超时后先看产物”。

    ### 6.1 单入口参数约定

    建议在入口脚本（例如 `scripts/run.py`）增加：

    - `--detached`：后台启动后立即返回
    - `--task-id`：可选，允许外部指定任务ID
    - `--tasks-dir`：任务根目录，默认 `outputs/tasks`
    - `--status <task_id>`：只查询任务状态并退出
    - `--tail-lines N`：查询状态时输出日志尾部行数

    ### 6.2 任务目录结构（推荐）

    ```
    outputs/
        tasks/
            <task_id>/
                meta.json
                stdout.log
                stderr.log
    ```

    `meta.json` 建议字段：

    - `task_id`
    - `pid`
    - `status`（初始可写 `running`）
    - `started_at`
    - `mode`（single/cross 等）
    - `command`
    - `cwd`
    - `stdout_log` / `stderr_log`

    ### 6.3 后台启动实现要点

    - Windows：`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`
    - Linux/Mac：`start_new_session=True`
    - stdout/stderr 不走管道，直接重定向到日志文件，避免宿主会话退出后丢失输出。

    ### 6.4 状态查询实现要点

    - `--status` 分支应尽早返回，不要求读取业务配置（例如 API Key）。
    - 通过 `meta.json` 的 `pid` 做存活判断（例如 `os.kill(pid, 0)`）。
    - 查询输出建议包含：
        - task_id / pid / state(running|exited) / started_at
        - stdout.log、stderr.log 路径
        - stdout/stderr 尾部日志（默认最后40行）

    ### 6.5 超时语义（避免误杀有效任务）

    对前台/监控层 timeout，建议采用“证据优先”判定：

    1. 先检查关键产物是否已生成或仍在更新
    2. 再结合进程是否仍存活
    3. 最后才判定失败

    可用判定：

    - `completed`：关键产物存在且内容有效
    - `running/unknown`：进程仍在、日志短暂静默
    - `failed`：进程退出且无可用产物

    ### 6.6 推荐命令模板（PowerShell）

    ```powershell
    # 1) 后台启动
    python scripts/run.py --config configs/config.json --idea-json "<idea_json_path>" --data-type MATRIX --detached

    # 2) 查询状态（含日志尾部）
    python scripts/run.py --status "<task_id>" --tail-lines 60

    # 3) 持续看日志
    Get-Content "outputs/tasks/<task_id>/stdout.log" -Wait
    ```

    ### 6.7 对 Skill 文档的最低要求

    在 `SKILL.md` 中明确：

    - 长任务默认后台启动（`--detached`）
    - 报告中必须给出 `task_id`
    - 超时不等于失败，先查产物再下结论
    - 给出一条标准状态查询命令（`--status`）