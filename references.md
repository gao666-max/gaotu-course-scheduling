# 参考资料清单

> 队伍: 皇帝不吃辣 | 命题: 高途智能排课系统

## 学术文献

1. Gu X, Krish M, Sohail S, et al. From Integer Programming to Machine Learning: A Technical Review on Solving University Timetabling Problems[J]. *Computation*, 2025, 13(1): 10.
   — 综述 1990-2023 年间 95 篇整数规划排课文献, 结论: 整数规划实现率 98%, 远超元启发式 34%; 呼吁 ML+IP 混合方案

2. Moreira E J B, de Freitas S A A. A CP-SAT Approach for Academic Resource Timetabling in Higher Education Institutions: A Case Study at a Major Public University[C]. *IEEE ITHET 2024*, Paris.
   — 巴西利亚大学基于 OR-Tools CP-SAT 在 11 个真实排课场景中全部成功求解, 获最佳论文奖

3. Jabbar et al. Hybrid Genetic Algorithm and CP-SAT for Course Timetabling[J]. *INOVTEK Polbeng*, 2026.
   — 提出 GA + CP-SAT 两阶段混合法, 先遗传算法生成初始解再 CP-SAT 精修, 零冲突输出

4. COS301-SE-2026. UMTAS: University-agnostic Core-and-Adapter Platform[EB/OL]. *GitHub*, 2026.
   — 基于 OR-Tools CP-SAT 的大学排课平台, 支持 20,000 并发学生, 异步冲突检测与重排

## 行业报告

5. 华为云社区. 从人工协调到Agent自动化处理, 2026教务排课与学员管理如何高效——教培的数智化破局[EB/OL]. 2026-07.
   — 指出 65% 教培企业仍依赖"系统+Excel+微信群", AI Agent 处于爆发前夜; 实在Agent 可将季度调课周期从 3 天缩短至 1 小时

6. Global Info Research. Global AI Course Scheduling Software Market Report 2026-2032[R]. 2026.
   — 2025 年全球市场规模约 17.7 亿美元, 预计 2032 年达 38.9 亿美元, CAGR 11.8%

7. QY Research. 中国AI排课软件市场现状及未来趋势报告2026[R]. 2026.
   — 中国 2032 年预计市场规模 38.4 亿美元, CAGR 12.1%, 亚太为增长最快区域

8. HTF Market Intelligence. Global AI Course Scheduling Software Market Share Analysis 2026-2033[R]. 2026.
   — 头部厂商包括 Untis, TimeTabler, CourseKey 等欧美企业, 均未实现自然语言交互功能

## 行业案例与评述

9. 中国教育报. 深读: 充满生命力的课程表如何编排[N]. 2026.
   — 一线教务人员真实反馈: 排课软件"冲突已解决"但实际教室重了; 教务成年累月手动打补丁

10. 新东方合肥学校. 智能排课系统部署案例[EB/OL]. 安徽新闻网, 2026.
    — 新东方引入智能排课后运营效率提升 20%+, 验证算法排课在教培赛道的 ROI

11. 华中科技大学. 多目标驱动, 智能排课赋能高校公共课教学管理[EB/OL]. 2026.
    — 基于多目标优化算法, 数十秒输出零冲突完整排课方案

12. 山东大学(威海). 基于时空约束的高校排课模式动态调整策略研究[J]. 2025.
    — 提出二级排课模式与混合排课方法, 灵活优化教室和教师资源利用率

## 政策与趋势

13. 教育部. 关于推进教育新型基础设施建设构建高质量教育支撑体系的指导意见[EB/OL]. 2021.
    — 明确提出推动智慧校园建设, AI 排课为教务管理数字化核心工具

## 技术文档

14. Google OR-Tools. CP-SAT Solver Documentation[EB/OL]. https://developers.google.com/optimization
    — 本方案核心技术选型, Google 开源维护的约束求解器
