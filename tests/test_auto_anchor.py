"""CD 锚定(auto_anchor)逻辑测试:守卫条件、排程、失败重试、验证重读。

不真正发起 codex exec:_fire_anchor / refresh 被猴补为记录器;
stderr 日志静音。
"""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import codex_pet.codex_client as cc
from codex_pet.codex_client import CodexClient
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QApplication

cc.CodexClient._anchor_log = staticmethod(lambda msg: None)
app = QApplication.instance() or QApplication(sys.argv)

results = []


def check(name, cond):
    results.append((name, cond))
    print(("PASS " if cond else "FAIL ") + name)


def make_client(auto_anchor=True):
    cc.load_config = lambda: {"auto_anchor": auto_anchor}
    client = CodexClient()
    client._codex_exe = "/usr/bin/true"   # 守卫检查用,不真正执行
    client._codex_args = []
    fired, refreshed = [], []

    def _fire():
        fired.append(time.time())
        client._anchor_attempts += 1      # 与真实 _fire_anchor 行为一致
    client._fire_anchor = _fire
    client.refresh = lambda: refreshed.append(time.time())
    return client, fired, refreshed


def feed(client, remaining, resets_at):
    """模拟一次配额响应到达(_handle_response 的状态记录 + 排程)。"""
    client._last_remaining = remaining
    client._last_resets_at = resets_at
    client._schedule_anchor()


# 场景1:重置在未来 + 开关开 → 排程定时器
c, fired, refreshed = make_client(True)
future = time.time() + 3600
feed(c, 0, future)
check("未来重置 → 定时器已排程", c._anchor_timer.isActive())
check("排程时刻 ≈ resets_at+5min",
      abs(c._anchor_timer.remainingTime() / 1000 - (future + 300 - time.time())) < 2)

# 场景2:未用完 → 也排程(每次刷新都锚定,窗口节奏钉死在 5h 网格)
c2, f2, r2 = make_client(True)
feed(c2, 45, future)
check("未用完 → 也排程", c2._anchor_timer.isActive())

# 场景3:开关关 → 不排程
c3, f3, r3 = make_client(False)
feed(c3, 0, future)
check("开关关 → 不排程", not c3._anchor_timer.isActive())

# 场景4:重置时刻已过 → 不排程(退回兜底轮询)
c4, f4, r4 = make_client(True)
feed(c4, 0, time.time() - 60)
check("重置已过 → 不排程", not c4._anchor_timer.isActive())

# 场景5:锚定时刻到(+5 分钟) → 发起
c5, f5, r5 = make_client(True)
c5._last_remaining = 0
c5._last_resets_at = time.time() - 301    # 刚到 +5 分钟触发点
c5._maybe_anchor()
check("到 +5 分钟触发点 → 发起锚定", len(f5) == 1 and c5._anchor_attempts == 1)

# 场景6:错过太久(睡眠)→ 放弃
c6, f6, r6 = make_client(True)
c6._last_remaining = 0
c6._last_resets_at = time.time() - 700    # 错过 ~11.7 分钟
c6._maybe_anchor()
check("错过 >10 分钟 → 放弃锚定", len(f6) == 0)

# 场景7:未用完 → 也发起(不再要求耗尽)
c7, f7, r7 = make_client(True)
c7._last_remaining = 60
c7._last_resets_at = time.time() - 2
c7._maybe_anchor()
check("未用完 → 也发起", len(f7) == 1)

# 场景8:exec 成功 → 5s 后读新窗口(而非立即读)
c8, f8, r8 = make_client(True)
c8._last_remaining = 0
c8._last_resets_at = time.time() - 2
proc = QProcess(c8)
c8._anchor_proc = proc
c8._on_anchor_finished(0, QProcess.ExitStatus.NormalExit)
check("exec 成功 → 排定延迟读取", c8._anchor_read_timer.isActive()
      and len(r8) == 0 and c8._anchor_proc is None)
c8._post_anchor_read()
check("延迟读取触发 refresh", len(r8) == 1)

# 场景9:exec 失败 → 30s 重试定时器,且重试能再次发起
c9, f9, r9 = make_client(True)
c9._last_remaining = 0
c9._last_resets_at = time.time() - 2
c9._maybe_anchor()                          # 第 1 次
proc9 = QProcess(c9)
c9._anchor_proc = proc9
c9._on_anchor_finished(1, QProcess.ExitStatus.NormalExit)   # 失败
check("exec 失败 → 重试定时器", c9._anchor_retry_timer.isActive())
c9._maybe_anchor()                          # 重试时刻到
check("重试再次发起(第 2 次)", len(f9) == 2 and c9._anchor_attempts == 2)

# 场景10:尝试次数用尽 → 不再发起
c10, f10, r10 = make_client(True)
c10._last_remaining = 0
c10._last_resets_at = time.time() - 2
c10._anchor_attempts = 3
c10._maybe_anchor()
check("尝试 3 次用尽 → 不再发起", len(f10) == 0)

# 场景11:锚定后读回旧窗口 → 验证重读排程
c11, f11, r11 = make_client(True)
old_resets = time.time() - 5
c11._last_remaining = 0
c11._last_resets_at = old_resets
c11._anchor_verify = (old_resets, True, 0)
c11._schedule_anchor()
check("读回旧窗口 → 30s 重读", c11._anchor_verify_timer.isActive()
      and c11._anchor_verify == (old_resets, True, 1))

# 场景12:读到新窗口 → 验证清除并正常排程新锚点
c12, f12, r12 = make_client(True)
new_resets = time.time() + 3600
c12._last_resets_at = new_resets
c12._anchor_verify = (old_resets, True, 1)
c12._schedule_anchor()
check("读到新窗口 → 验证清除", c12._anchor_verify is None)
check("新窗口 → 锚定排程指向新重置点", c12._anchor_timer.isActive())

print("\nRESULT:", "PASS" if all(cond for _, cond in results) else "FAIL")
sys.exit(0 if all(cond for _, cond in results) else 1)
