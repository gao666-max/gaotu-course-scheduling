# 课枢 CourseHub — 高途智能排课系统原型验证

> 2026 AI先锋未来人才大赛 | 高途命题
> 队伍: 皇帝不吃辣

## 一句话概述

构建一套「会思考」的智能排课系统——以 OR-Tools CP-SAT 约束求解器为计算引擎，融合自然语言交互与经验持续沉淀机制，解决高途线下校区多业务线并行、跨校区调度及冲刺季需求爆发的排课难题。

## 原型验证结果

对以下场景进行 CP-SAT 约束求解验证:

| 指标 | 结果 |
|------|------|
| 场景规模 | 2 校区 x 3 业务线 x 8 位教师 x 8 间教室 x 20 个时段 |
| 待排课程 | 23 节/周 |
| 硬约束类型 | 8 类 (教室容量/类型/唯一性/教师冲突/校区缓冲/日课时/时间偏好/课程分散) |
| 求解状态 | **OPTIMAL** |
| 求解耗时 | **< 3 秒** |
| 硬约束冲突 | **0** |
| 软约束目标值 | **0** (全部满足) |

## 技术栈

- **约束求解**: Google OR-Tools CP-SAT (9.15)
- **语言**: Python 3

## 项目结构

```
gaotu-scheduling-demo/
├── scheduler_demo.py    # CP-SAT 约束求解原型 (2校区, 8教师, 8教室, 23节课)
└── README.md            # 本文件
```

## 快速运行

```bash
pip install ortools
python scheduler_demo.py
```

## 方案架构

```
┌─────────────────────────────────────────────┐
│              交互层: NL排课助手               │
│  口语化指令 → 意图识别 → 结构化排课请求       │
├─────────────────────────────────────────────┤
│              决策层: 约束求解引擎             │
│  CP-SAT 硬约束满足 + 软约束多目标优化         │
├─────────────────────────────────────────────┤
│              知识层: 教务经验图谱             │
│  隐性知识结构化 → "调整即学习" → 权重更新     │
├─────────────────────────────────────────────┤
│              感知层: 异常检测与响应           │
│  教师请假/教室故障 → 增量重排 → 推送通知     │
└─────────────────────────────────────────────┘
```

## 约束建模能力

**硬约束 (必须满足)**:
- 教室容量 >= 课程学生数
- 教室类型与课程类型匹配
- 同一教室同时段唯一使用
- 同一教师同时段不冲突
- 跨校区连续时段缓冲 (不允许相邻时段跨校区)
- 教师每日最大课时限制
- 课程时间偏好 (上午/下午限制)
- 同一课程不同 session 分散到不同天

**软约束 (多目标优化)**:
- 教师主攻赛道匹配偏好
- 避免教师课表空洞 (连续排课偏好)
- 跨校区通勤惩罚
- 大班课上午/小班课下午偏好

## 关键参考文献

1. Gu X, et al. From Integer Programming to Machine Learning: A Technical Review on Solving University Timetabling Problems. *Computation*, 2025, 13(1): 10.
2. Moreira E J B, de Freitas S A A. A CP-SAT Approach for Academic Resource Timetabling in Higher Education Institutions. IEEE ITHET 2024, Paris. (Best Paper Award)
3. 华为云社区. 从人工协调到Agent自动化处理, 2026教务排课与学员管理如何高效. 2026-07.
4. Global Info Research. Global AI Course Scheduling Software Market Report 2026-2032. 2026.
5. Jabbar et al. Hybrid Genetic Algorithm and CP-SAT for Course Timetabling. INOVTEK Polbeng, 2026.
