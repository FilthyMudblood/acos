# Auto Test Report

这个文档用于集中记录 `auto_test` 目录下测试的执行结果，便于回溯稳定性变化与回归风险。

## Latest Results

### 2026-05-02 09:22 (UTC+8)

- Command: `python3 auto_test/run_all.py`
- Result: PASS
- Details:
  - `auto_test.test_aegis_egress`: 4 passed
  - `auto_test.test_agent_os_runtime_egress_veto`: 1 passed
  - `auto_test.test_salami_slicing_benchmark`: 2 passed
  - Total: 7 passed, 0 failed

### 2026-05-02 09:26 (UTC+8)

- Command: `python3 auto_test/test_salami_slicing_benchmark.py --compare-profiles`
- Result: PASS
- Profile comparison:
  - strict: PASS, veto_step=2, veto_r_eff=1.310971, r_max=1.0
  - balanced: PASS, veto_step=4, veto_r_eff=7.220861, r_max=1.5
  - research: PASS, veto_step=4, veto_r_eff=3.862782, r_max=2.5

## Update Convention

- 只保存成功测试：仅在命令退出码为 `0` 时追加记录。
- 每次执行 `auto_test` 后，新增一个时间块（不要覆盖历史）。
- 至少记录：
  - 执行时间
  - 执行命令
  - 总体结果（PASS）
  - 关键输出摘要
- 若涉及基准测试（如 salami profile），附上关键指标（如 `veto_step`、`veto_r_eff`）。

## Quick Append Command

- 运行并自动记录（仅成功时写入）：
  - `python3 auto_test/save_success_report.py --cmd "python3 auto_test/run_all.py"`
  - `python3 auto_test/save_success_report.py --cmd "python3 auto_test/test_salami_slicing_benchmark.py --compare-profiles"`

### 2026-05-02 09:29 (UTC+8)

- Command: `python3 auto_test/test_salami_slicing_benchmark.py --compare-profiles`
- Result: PASS
- Details:
  - Profile: strict   | PASS: True  | veto_step: 2    | veto_r_eff: 1.311 | r_max: 1.00
  - Profile: balanced | PASS: True  | veto_step: 4    | veto_r_eff: 7.221 | r_max: 1.50
  - Profile: research | PASS: True  | veto_step: 4    | veto_r_eff: 3.863 | r_max: 2.50
