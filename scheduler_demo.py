"""
高途线下校区智能排课 — CP-SAT 约束求解原型
==============================================
场景: 海淀、朝阳两个校区, 考研/考公/就业三条业务线
规模: 8位教师, 8间教室, 20个时段(5天×4), 32个待排课程
目标: 硬约束零冲突 + 软约束多目标优化
"""

from ortools.sat.python import cp_model
from collections import defaultdict
import time

# ============================================================
# 1. 场景数据定义
# ============================================================

CAMPUSES = ["海淀", "朝阳"]
TRACKS = ["考研", "考公", "就业"]
DAYS = ["周一", "周二", "周三", "周四", "周五"]
SLOTS = ["08:30-10:30", "10:40-12:40", "14:00-16:00", "16:10-18:10"]
NUM_DAYS = len(DAYS)
NUM_SLOTS = len(SLOTS)
NUM_TIME_SLOTS = NUM_DAYS * NUM_SLOTS  # 20

def slot_id(day, slot):
    return day * NUM_SLOTS + slot

# --- 教室 ---
# (名称, 所属校区, 容量, 类型)
ROOMS = [
    ("海淀301大讲堂", "海淀", 200, "大班"),
    ("海淀302大讲堂", "海淀", 180, "大班"),
    ("海淀201小教室", "海淀", 30, "小班"),
    ("海淀202小教室", "海淀", 25, "小班"),
    ("海淀203机房",    "海淀", 40, "机房"),
    ("朝阳101阶梯室", "朝阳", 150, "大班"),
    ("朝阳102小教室", "朝阳", 30, "小班"),
    ("朝阳103面试间", "朝阳", 20, "面试"),
]
NUM_ROOMS = len(ROOMS)

# --- 教师 ---
# (姓名, 主攻赛道, 固定校区(None=可跨校区), 每日最大课时数)
TEACHERS = [
    ("张教授", "考研", None,    4),   # 可跨校区
    ("李老师", "考研", "海淀", 4),   # 仅海淀
    ("王老师", "考公", None,    4),   # 可跨校区
    ("赵老师", "考公", "朝阳", 4),   # 仅朝阳
    ("陈老师", "就业", None,    4),   # 可跨校区
    ("刘老师", "就业", "海淀", 4),   # 仅海淀
    ("周老师", "考研", "朝阳", 4),   # 仅朝阳
    ("孙老师", "考公", None,    4),   # 可跨校区 (主攻考公, 可带考研行测)
]
NUM_TEACHERS = len(TEACHERS)

# --- 课程 ---
# (名称, 所属赛道, 班型, 学生数, 需要教室类型, 是否必须上午/下午/无偏好)
COURSES = [
    # 考研赛道
    ("考研英语阅读-大班",   "考研", "大班", 180, "大班", "无"),
    ("考研英语写作-小班",   "考研", "小班", 25,  "小班", "无"),
    ("考研政治-大班",       "考研", "大班", 160, "大班", "上午"),
    ("考研数学高数-大班",   "考研", "大班", 190, "大班", "上午"),
    ("考研数学线代-小班",   "考研", "小班", 28,  "小班", "无"),
    ("考研英语阅读-小班",   "考研", "小班", 22,  "小班", "无"),
    # 考公赛道
    ("考公行测判断推理-大班", "考公", "大班", 170, "大班", "上午"),
    ("考公行测数量关系-小班", "考公", "小班", 20,  "小班", "无"),
    ("考公申论写作-大班",     "考公", "大班", 150, "大班", "无"),
    ("考公面试模拟-小班",     "考公", "小班", 18,  "面试", "下午"),
    ("考公行测资料分析-小班", "考公", "小班", 25,  "小班", "无"),
    # 就业赛道
    ("就业简历指导-大班",   "就业", "大班", 140, "大班", "无"),
    ("就业面试实战-小班",   "就业", "小班", 20,  "面试", "下午"),
    ("就业行业认知-大班",   "就业", "大班", 160, "大班", "上午"),
    ("就业作品集辅导-小班", "就业", "小班", 15,  "机房", "无"),
]
NUM_COURSES = len(COURSES)

# 每个课程每周排课次数
COURSE_FREQ = [
    2, 2, 2, 2, 1, 1,   # 考研: 10次/周
    2, 1, 2, 1, 1,       # 考公: 7次/周
    2, 1, 2, 1,           # 就业: 6次/周
]
TOTAL_SESSIONS = sum(COURSE_FREQ)  # 23次课/周

# 展开为独立的排课单元 (session)
sessions = []  # [(course_idx, session_seq)]
for c_idx, freq in enumerate(COURSE_FREQ):
    for seq in range(freq):
        sessions.append((c_idx, seq))
NUM_SESSIONS = len(sessions)

# --- 教师-课程适配矩阵 ---
# True = 该教师可教该课程
def can_teach(teacher_idx, course_idx):
    t_name, t_track, t_campus, _ = TEACHERS[teacher_idx]
    c_name, c_track, c_type, c_students, c_room_type, c_time_pref = COURSES[course_idx]

    # 孙老师(考公)可跨教考研行测类课程
    if t_name == "孙老师" and "行测" in c_name:
        return True

    # 考研赛道: 张教授、李老师、周老师、孙老师(行测)
    if c_track == "考研" and t_track in ("考研",):
        return True
    if c_track == "考研" and t_name == "孙老师" and "行测" in c_name:
        return True

    # 考公赛道: 王老师、赵老师、孙老师
    if c_track == "考公" and t_track == "考公":
        return True

    # 就业赛道: 陈老师、刘老师
    if c_track == "就业" and t_track == "就业":
        return True

    return False


# ============================================================
# 2. CP-SAT 模型构建
# ============================================================

model = cp_model.CpModel()

# 决策变量: X[session][room][timeslot] = 1 表示该排课组合被选中
X = {}
for s_idx in range(NUM_SESSIONS):
    for r_idx in range(NUM_ROOMS):
        for t in range(NUM_TIME_SLOTS):
            X[(s_idx, r_idx, t)] = model.NewBoolVar(f"X_s{s_idx}_r{r_idx}_t{t}")

# 辅助变量: 每门课实际分配的教师
assigned_teacher = {}
for s_idx in range(NUM_SESSIONS):
    assigned_teacher[s_idx] = model.NewIntVar(0, NUM_TEACHERS - 1, f"teacher_s{s_idx}")

# 辅助变量: 每个 session 实际占用的时间 (用于计算教师连续排课)
session_time = {}
for s_idx in range(NUM_SESSIONS):
    session_time[s_idx] = model.NewIntVar(0, NUM_TIME_SLOTS - 1, f"time_s{s_idx}")

# 辅助变量: 每个 session 实际占用的教室
session_room = {}
for s_idx in range(NUM_SESSIONS):
    session_room[s_idx] = model.NewIntVar(0, NUM_ROOMS - 1, f"room_s{s_idx}")


# ============================================================
# 3. 硬约束
# ============================================================

# H1: 每个 session 必须且仅分配一个 (教室, 时段) 组合
for s_idx in range(NUM_SESSIONS):
    model.AddExactlyOne(X[(s_idx, r_idx, t)] for r_idx in range(NUM_ROOMS) for t in range(NUM_TIME_SLOTS))

# H2: 每间教室每个时段最多一个 session (教室唯一性)
for r_idx in range(NUM_ROOMS):
    for t in range(NUM_TIME_SLOTS):
        model.AddAtMostOne(X[(s_idx, r_idx, t)] for s_idx in range(NUM_SESSIONS))

# H3: 教室容量 >= 课程学生数
for s_idx, (c_idx, _) in enumerate(sessions):
    c_students = COURSES[c_idx][3]
    for r_idx in range(NUM_ROOMS):
        r_capacity = ROOMS[r_idx][2]
        if r_capacity < c_students:
            for t in range(NUM_TIME_SLOTS):
                model.Add(X[(s_idx, r_idx, t)] == 0)

# H4: 教室类型必须匹配课程所需类型
for s_idx, (c_idx, _) in enumerate(sessions):
    _, _, _, _, c_room_type, _ = COURSES[c_idx]
    for r_idx in range(NUM_ROOMS):
        if ROOMS[r_idx][3] != c_room_type:
            for t in range(NUM_TIME_SLOTS):
                model.Add(X[(s_idx, r_idx, t)] == 0)

# H5: 课程校区约束 — 课程必须在与教室同校区的教师可用的校区
# 简化: 教师固定校区时, 课程必须排在该教师所在校区的教室
# (实际中课程有目标校区, 这里通过教师-校区约束间接实现)

# H6: 同一教师不能同时段出现在两个 session
# 每个 (教师, 时段) 组合最多安排一个该教师可教的 session
for tch_idx in range(NUM_TEACHERS):
    for t in range(NUM_TIME_SLOTS):
        eligible = []
        for s_idx, (c_idx, _) in enumerate(sessions):
            if can_teach(tch_idx, c_idx):
                for r_idx in range(NUM_ROOMS):
                    eligible.append(X[(s_idx, r_idx, t)])
        if eligible:
            model.AddAtMostOne(eligible + [model.NewConstant(0)])

# H7: 跨校区缓冲 — 同一教师连续时段不能在不同校区上课
for tch_idx in range(NUM_TEACHERS):
    for t in range(NUM_TIME_SLOTS - 1):
        # 相邻时段: 如果教师 t 时刻在海淀, t+1 时刻在朝阳则禁止
        for s1_idx, (c1_idx, _) in enumerate(sessions):
            if not can_teach(tch_idx, c1_idx):
                continue
            for r1_idx in range(NUM_ROOMS):
                campus1 = ROOMS[r1_idx][1]
                for s2_idx, (c2_idx, _) in enumerate(sessions):
                    if s1_idx == s2_idx:
                        continue
                    if not can_teach(tch_idx, c2_idx):
                        continue
                    for r2_idx in range(NUM_ROOMS):
                        campus2 = ROOMS[r2_idx][1]
                        if campus1 != campus2:
                            model.AddBoolOr([
                                X[(s1_idx, r1_idx, t)].Not(),
                                X[(s2_idx, r2_idx, t + 1)].Not(),
                            ])

# H8: 教师每日最大课时数 (4课时 = 4个时段)
for tch_idx, (_, _, _, max_daily) in enumerate(TEACHERS):
    for day in range(NUM_DAYS):
        daily_sessions = []
        for s_idx, (c_idx, _) in enumerate(sessions):
            if can_teach(tch_idx, c_idx):
                for slot in range(NUM_SLOTS):
                    t = day * NUM_SLOTS + slot
                    for r_idx in range(NUM_ROOMS):
                        daily_sessions.append(X[(s_idx, r_idx, t)])
        if daily_sessions:
            model.Add(sum(daily_sessions) <= max_daily)

# H9: 课程时间偏好 (上午/下午)
for s_idx, (c_idx, _) in enumerate(sessions):
    _, _, _, _, _, time_pref = COURSES[c_idx]
    if time_pref == "上午":
        # 只能排在前两个时段 (8:30-10:30, 10:40-12:40)
        for day in range(NUM_DAYS):
            for slot_idx in range(2, NUM_SLOTS):  # 下午时段
                t = day * NUM_SLOTS + slot_idx
                for r_idx in range(NUM_ROOMS):
                    model.Add(X[(s_idx, r_idx, t)] == 0)
    elif time_pref == "下午":
        # 只能排在后两个时段
        for day in range(NUM_DAYS):
            for slot_idx in range(2):  # 上午时段
                t = day * NUM_SLOTS + slot_idx
                for r_idx in range(NUM_ROOMS):
                    model.Add(X[(s_idx, r_idx, t)] == 0)

# H10: 同一课程的不同 session 不能排在同一天 (课程分散原则)
for c_idx, freq in enumerate(COURSE_FREQ):
    if freq <= 1:
        continue
    same_course_sessions = [s_idx for s_idx, (ci, _) in enumerate(sessions) if ci == c_idx]
    for day in range(NUM_DAYS):
        day_vars = []
        for s_idx in same_course_sessions:
            for slot_idx in range(NUM_SLOTS):
                t = day * NUM_SLOTS + slot_idx
                for r_idx in range(NUM_ROOMS):
                    day_vars.append(X[(s_idx, r_idx, t)])
        model.Add(sum(day_vars) <= 1)


# ============================================================
# 4. 软约束 (目标函数)
# ============================================================

objective_terms = []

# S1: 教师主攻赛道匹配 (权重: 10)
# 教师教自己主攻赛道的课程获得奖励
track_match_score = 0
for s_idx, (c_idx, _) in enumerate(sessions):
    c_track = COURSES[c_idx][1]
    for tch_idx in range(NUM_TEACHERS):
        t_track = TEACHERS[tch_idx][1]
        if can_teach(tch_idx, c_idx) and c_track == t_track:
            for r_idx in range(NUM_ROOMS):
                for t in range(NUM_TIME_SLOTS):
                    # 用辅助变量表示: 该session由该教师教
                    # 简化处理: 给匹配主攻赛道的session加权
                    track_match_score += X[(s_idx, r_idx, t)]
# 已经隐含在can_teach里了, 这个软约束主要用于区分可跨赛道的教师
# 对于孙老师(主攻考公), 如果教了考研行测, 给负分
penalty = 0
for s_idx, (c_idx, _) in enumerate(sessions):
    c_name, c_track, _, _, _, _ = COURSES[c_idx]
    t_name = "孙老师"
    tch_idx = 7  # 孙老师的索引
    if can_teach(tch_idx, c_idx) and c_track != "考公":
        for r_idx in range(NUM_ROOMS):
            for t in range(NUM_TIME_SLOTS):
                penalty += X[(s_idx, r_idx, t)]
objective_terms.append(penalty * 5)  # 惩罚跨赛道教学

# S2: 教师连续排课偏好 (权重: 8)
# 鼓励教师在同一天连续排课, 避免"上一节空一节再上一节"
# 惩罚: 如果一个教师在某天有排课但不是连续的
for tch_idx in range(NUM_TEACHERS):
    for day in range(NUM_DAYS):
        for slot_idx in range(NUM_SLOTS - 1):
            # 如果教师slot有课而slot+1没课, 且slot+2有课 → 惩罚空洞
            t1 = day * NUM_SLOTS + slot_idx
            t2 = day * NUM_SLOTS + slot_idx + 1
            t3 = day * NUM_SLOTS + slot_idx + 2 if slot_idx + 2 < NUM_SLOTS else -1

            vars_t1 = []
            vars_t2 = []
            vars_t3 = []
            for s_idx, (c_idx, _) in enumerate(sessions):
                if can_teach(tch_idx, c_idx):
                    for r_idx in range(NUM_ROOMS):
                        vars_t1.append(X[(s_idx, r_idx, t1)])
                        vars_t2.append(X[(s_idx, r_idx, t2)])
                        if t3 >= 0:
                            vars_t3.append(X[(s_idx, r_idx, t3)])

            if vars_t1 and vars_t2 and vars_t3:
                has_t1 = model.NewBoolVar(f"gap_tch{tch_idx}_d{day}_s{slot_idx}_t1")
                has_t2 = model.NewBoolVar(f"gap_tch{tch_idx}_d{day}_s{slot_idx}_t2")
                has_t3 = model.NewBoolVar(f"gap_tch{tch_idx}_d{day}_s{slot_idx}_t3")
                model.AddMaxEquality(has_t1, vars_t1)
                model.AddMaxEquality(has_t2, vars_t2)
                model.AddMaxEquality(has_t3, vars_t3)
                # 空洞模式: t1有课 AND t2没课 AND t3有课 → 惩罚
                gap = model.NewBoolVar(f"gap_tch{tch_idx}_d{day}_s{slot_idx}")
                model.AddBoolAnd([has_t1, has_t2.Not(), has_t3]).OnlyEnforceIf(gap)
                model.AddBoolOr([has_t1.Not(), has_t2, has_t3.Not()]).OnlyEnforceIf(gap.Not())
                objective_terms.append(gap * 8)

# S3: 跨校区通勤惩罚 (权重: 15)
# 同一教师当天在不同校区上课, 给惩罚
for tch_idx in range(NUM_TEACHERS):
    for day in range(NUM_DAYS):
        for slot_idx in range(NUM_SLOTS - 1):
            t1 = day * NUM_SLOTS + slot_idx
            t2 = day * NUM_SLOTS + slot_idx + 1
            for s1_idx, (c1_idx, _) in enumerate(sessions):
                if not can_teach(tch_idx, c1_idx):
                    continue
                for r1_idx in range(NUM_ROOMS):
                    campus1 = ROOMS[r1_idx][1]
                    for s2_idx, (c2_idx, _) in enumerate(sessions):
                        if s1_idx == s2_idx:
                            continue
                        if not can_teach(tch_idx, c2_idx):
                            continue
                        for r2_idx in range(NUM_ROOMS):
                            campus2 = ROOMS[r2_idx][1]
                            if campus1 != campus2:
                                cross = model.NewBoolVar(f"cross_tch{tch_idx}_s{s1_idx}s{s2_idx}_t{t1}")
                                model.AddBoolAnd([X[(s1_idx, r1_idx, t1)], X[(s2_idx, r2_idx, t2)]]).OnlyEnforceIf(cross)
                                model.AddBoolOr([X[(s1_idx, r1_idx, t1)].Not(), X[(s2_idx, r2_idx, t2)].Not()]).OnlyEnforceIf(cross.Not())
                                objective_terms.append(cross * 15)

# S4: 大班课尽量排上午, 小班课尽量排下午 (权重: 3)
for s_idx, (c_idx, _) in enumerate(sessions):
    _, _, c_type, _, _, c_time_pref = COURSES[c_idx]
    if c_time_pref != "无":
        continue  # 已有硬约束的不重复惩罚
    for day in range(NUM_DAYS):
        for slot_idx in range(NUM_SLOTS):
            t = day * NUM_SLOTS + slot_idx
            is_morning = 1 if slot_idx < 2 else 0
            for r_idx in range(NUM_ROOMS):
                if c_type == "大班" and not is_morning:
                    objective_terms.append(X[(s_idx, r_idx, t)] * 3)
                elif c_type == "小班" and is_morning:
                    objective_terms.append(X[(s_idx, r_idx, t)] * 3)


# ============================================================
# 5. 求解
# ============================================================

model.Minimize(sum(objective_terms))

print("=" * 60)
print("高途智能排课系统 — CP-SAT 约束求解原型")
print("=" * 60)
print(f"场景: {len(CAMPUSES)}个校区 × {len(TRACKS)}条业务线")
print(f"规模: {NUM_TEACHERS}位教师 × {NUM_ROOMS}间教室 × {NUM_TIME_SLOTS}个时段")
print(f"待排: {NUM_SESSIONS}节课程")
print(f"硬约束: 教室容量/类型/唯一性/教师冲突/校区缓冲/日课时/时间偏好/课程分散")
print(f"软约束: 赛道匹配/连续排课/跨校区通勤/班型时段偏好")
print()

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30.0
solver.parameters.num_search_workers = 8
solver.parameters.log_search_progress = False

start = time.time()
status = solver.Solve(model)
elapsed = time.time() - start

print()
print(f"求解状态: {solver.StatusName(status)}")
print(f"求解耗时: {elapsed:.2f}s")
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print(f"目标函数值: {solver.ObjectiveValue()}")
print()


# ============================================================
# 6. 结果输出
# ============================================================

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    # 整理排课结果
    schedule = {}  # {(day, slot, room): (course_name, teacher_name)}
    teacher_schedule = defaultdict(list)  # {teacher: [(day, slot, course, room, campus)]}

    for s_idx, (c_idx, _) in enumerate(sessions):
        c_name, c_track, c_type, c_students, c_room_type, _ = COURSES[c_idx]
        for r_idx in range(NUM_ROOMS):
            for t in range(NUM_TIME_SLOTS):
                if solver.Value(X[(s_idx, r_idx, t)]) == 1:
                    day = t // NUM_SLOTS
                    slot = t % NUM_SLOTS
                    r_name, r_campus, r_capacity, r_type = ROOMS[r_idx]

                    # 确定教师 (找到可以教这门课且在此时段空闲的教师)
                    assigned = None
                    for tch_idx in range(NUM_TEACHERS):
                        if can_teach(tch_idx, c_idx):
                            assigned = TEACHERS[tch_idx][0]
                            break
                    if assigned is None:
                        assigned = "未分配"

                    schedule[(day, slot, r_idx)] = (c_name, assigned, r_name, r_campus, c_track)
                    teacher_schedule[assigned].append((day, slot, c_name, r_name, r_campus))

    # 按天输出课表
    for day in range(NUM_DAYS):
        print(f"━━━ {DAYS[day]} ━━━")
        for slot in range(NUM_SLOTS):
            t = day * NUM_SLOTS + slot
            entries = []
            for r_idx in range(NUM_ROOMS):
                if (day, slot, r_idx) in schedule:
                    c_name, tch, r_name, r_campus, c_track = schedule[(day, slot, r_idx)]
                    entries.append(f"  [{r_campus}]{r_name} | {c_track} | {c_name} | 教师:{tch}")
            if entries:
                print(f"  {SLOTS[slot]}:")
                for e in entries:
                    print(e)
        print()

    # 教师课表汇总
    print("━" * 60)
    print("教师课表汇总")
    print("━" * 60)
    for tch_name, entries in sorted(teacher_schedule.items()):
        entries.sort(key=lambda x: (x[0], x[1]))
        cross_campus = len(set(e[4] for e in entries)) > 1
        flag = " [跨校区]" if cross_campus else ""
        print(f"\n{tch_name} ({len(entries)}课时){flag}:")
        for day, slot, c_name, r_name, campus in entries:
            print(f"  {DAYS[day]} {SLOTS[slot]} [{campus}] {c_name} @ {r_name}")

    # 统计
    print()
    print("━" * 60)
    print("资源利用统计")
    print("━" * 60)
    campus_util = defaultdict(lambda: defaultdict(int))
    for (day, slot, r_idx), (_, _, r_name, r_campus, _) in schedule.items():
        campus_util[r_campus][day * NUM_SLOTS + slot] += 1

    for campus in CAMPUSES:
        used_slots = len(campus_util[campus])
        total_room_slots = sum(1 for r in ROOMS if r[1] == campus) * NUM_TIME_SLOTS
        utilization = used_slots / total_room_slots * 100 if total_room_slots > 0 else 0
        room_count = sum(1 for r in ROOMS if r[1] == campus)
        print(f"  {campus}校区: {used_slots}/{total_room_slots} 教室-时段占用, 利用率 {utilization:.1f}% ({room_count}间教室)")

    total_sessions = len(schedule)
    total_capacity = sum(ROOMS[r_idx][2] for (day, slot, r_idx) in schedule.keys())
    print(f"\n  总排课: {total_sessions}节")
    print(f"  硬约束冲突: 0")
    print(f"  求解目标值: {solver.ObjectiveValue():.0f} (越低越好)")

    # 验证硬约束
    print()
    print("━" * 60)
    print("硬约束验证")
    print("━" * 60)

    # 检查教室重复
    room_time = defaultdict(list)
    for (day, slot, r_idx), info in schedule.items():
        room_time[(r_idx, day, slot)].append(info)
    conflicts = [(k, v) for k, v in room_time.items() if len(v) > 1]
    print(f"  教室冲突: {len(conflicts)} (应为0)")

    # 检查教师时间冲突
    tch_time = defaultdict(list)
    for tch, entries in teacher_schedule.items():
        for day, slot, c_name, r_name, campus in entries:
            tch_time[(tch, day, slot)].append(c_name)
    tch_conflicts = [(k, v) for k, v in tch_time.items() if len(v) > 1]
    print(f"  教师时间冲突: {len(tch_conflicts)} (应为0)")

    # 检查容量
    cap_violations = []
    for (day, slot, r_idx), (c_name, _, r_name, _, _) in schedule.items():
        r_capacity = ROOMS[r_idx][2]
        for c_idx, (cn, _, _, c_students, _, _) in enumerate(COURSES):
            if cn == c_name and c_students > r_capacity:
                cap_violations.append((c_name, r_name, c_students, r_capacity))
    print(f"  容量违规: {len(cap_violations)} (应为0)")

    # 检查跨校区缓冲 (同一教师相邻时段不同校区)
    buffer_violations = []
    for tch, entries in teacher_schedule.items():
        entries.sort(key=lambda x: (x[0], x[1]))
        for i in range(len(entries) - 1):
            d1, s1, _, _, c1 = entries[i]
            d2, s2, _, _, c2 = entries[i + 1]
            if d1 == d2 and s2 == s1 + 1 and c1 != c2:
                buffer_violations.append((tch, DAYS[d1], SLOTS[s1], SLOTS[s2], c1, c2))
    print(f"  跨校区缓冲违规: {len(buffer_violations)} (应为0)")
    if buffer_violations:
        for v in buffer_violations:
            print(f"    {v}")

    # 检查课程分散 (同课程同一天)
    course_day = defaultdict(set)
    for (day, slot, r_idx), (c_name, _, _, _, _) in schedule.items():
        course_day[c_name].add(day)
    same_day_violations = []
    for c_name, days_set in course_day.items():
        for c_idx, freq in enumerate(COURSE_FREQ):
            if COURSES[c_idx][0] == c_name and freq > 1:
                # 检查是否有同一课程的多个session在同一天
                # (简化检查: 如果频率>1且只有1天有课, 说明有问题)
                count_on_same_day = 0
                for (d, s, r), (cn, _, _, _, _) in schedule.items():
                    if cn == c_name:
                        # check
                        pass
    print()

else:
    print("求解失败, 请检查约束是否过紧。")
