"""Generate 500 QA pairs for RAG evaluation dataset."""
from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(42)

# ── Templates per category ────────────────────────────────────────────

MAINTENANCE_TEMPLATES = [
    {
        "question": "{equip}的{part}需要多久保养一次?",
        "context": "根据设备维护手册, {equip}的{part}建议每{interval}进行一次预防性保养。包括: 检查磨损情况、清洁滤网、紧固连接件、更换润滑油。保养记录需存档备查。",
        "answer_kw": "preventive",
    },
    {
        "question": "如何更换{equip}的{part}?",
        "context": "更换{equip}{part}的步骤: 1.断电并挂牌上锁; 2.拆卸固定螺丝; 3.断开电气连接; 4.取出旧部件; 5.安装新部件并校准; 6.恢复供电并测试运行。",
        "answer_kw": "replace",
    },
    {
        "question": "{equip}运行中异响怎么处理?",
        "context": "{equip}异响排查流程: 1.记录异响类型(轴承声/振动声/摩擦声); 2.检查地脚螺栓紧固状态; 3.检查轴承润滑状况; 4.检查叶轮/转子平衡; 5.必要时停机检修。",
        "answer_kw": "fault",
    },
    {
        "question": "{equip}的{part}标准运行参数是多少?",
        "context": "{equip}{part}标准参数: 温度范围{temp_range}, 压力{pressure}, 振动幅度<{vib}mm/s。超出范围应触发告警并安排检修。",
        "answer_kw": "param",
    },
    {
        "question": "{equip}的{part}故障代码{code}是什么意思?",
        "context": "故障代码{code}表示{equip}{part}异常。处理方法: 1.记录当前运行参数; 2.检查传感器读数; 3.确认供电电压正常; 4.复位故障码; 5.若持续出现需联系厂家。",
        "answer_kw": "fault_code",
    },
    {
        "question": "{equip}启动前需要做哪些检查?",
        "context": "{equip}启动前检查清单: 1.确认电源电压正常; 2.检查油位/液位; 3.确认阀门状态正确; 4.检查冷却系统; 5.确认无异物进入; 6.点动测试转向。",
        "answer_kw": "startup",
    },
    {
        "question": "{equip}的润滑油应该用什么牌号?",
        "context": "{equip}推荐润滑油牌号: 齿轮箱使用{gear_oil}, 轴承使用{bearing_oil}。换油周期为{interval}或运行{hours}小时。油质检测指标: 粘度变化<10%, 水分<0.1%。",
        "answer_kw": "lubrication",
    },
    {
        "question": "{equip}的{part}寿命周期是多长?",
        "context": "{equip}{part}设计寿命为{years}年或{hours}运行小时。实际寿命取决于使用环境和维护质量。建议每{inspect_interval}年进行一次健康评估。",
        "answer_kw": "lifecycle",
    },
    {
        "question": "如何校准{equip}的{part}传感器?",
        "context": "{equip}{part}传感器校准流程: 1.使用标准源注入已知值; 2.记录传感器读数; 3.调整偏移和增益; 4.重复至误差<1%; 5.填写校准记录表。",
        "answer_kw": "calibration",
    },
    {
        "question": "{equip}的{part}异常振动如何排查?",
        "context": "{equip}{part}振动异常排查: 1.测量振动频谱; 2.分析频率成分(1X/2X/高频); 3.检查不对中/不平衡/松动; 4.检查基础刚度; 5.必要时做动平衡。",
        "answer_kw": "vibration",
    },
    {
        "question": "{equip}停机维护后如何恢复运行?",
        "context": "{equip}恢复运行步骤: 1.确认所有维护工作已完成; 2.移除锁定挂牌; 3.恢复安全措施; 4.检查各系统状态; 5.点动试车; 6.逐步加载至额定工况; 7.监控运行参数。",
        "answer_kw": "restart",
    },
    {
        "question": "{equip}的{part}需要定期更换吗?",
        "context": "{equip}{part}建议每{interval}或运行{hours}小时更换一次。包括: 滤芯、密封件、皮带、轴承等易损件。更换时应使用原厂配件。",
        "answer_kw": "replacement",
    },
    {
        "question": "如何判断{equip}的{part}需要维修?",
        "context": "{equip}{part}需维修的判断标准: 1.运行参数超出正常范围; 2.出现异常噪声或振动; 3.效率明显下降; 4.能耗异常升高; 5.维护记录显示频繁故障。",
        "answer_kw": "repair",
    },
    {
        "question": "{equip}的日常点检项目有哪些?",
        "context": "{equip}日常点检项目: 1.运行声音是否正常; 2.温度是否正常; 3.油位/液位; 4.振动情况; 5.压力表读数; 6.有无泄漏; 7.指示灯状态。发现异常及时上报。",
        "answer_kw": "inspection",
    },
    {
        "question": "{equip}的{part}清洁频率是多久?",
        "context": "{equip}{part}建议{freq}清洁一次。清洁方法: 使用压缩空气吹扫或软毛刷清理, 禁止使用腐蚀性溶剂。清洁后检查无残留物。",
        "answer_kw": "cleaning",
    },
    {
        "question": "{equip}在低温环境下如何维护?",
        "context": "{equip}低温维护要点: 1.启用伴热系统; 2.检查防冻液浓度; 3.缩短润滑油更换周期; 4.启动前预热; 5.监控冷凝水排放。",
        "answer_kw": "cold",
    },
    {
        "question": "{equip}的{part}安装注意事项有哪些?",
        "context": "{equip}{part}安装注意事项: 1.基础水平度<1mm/m; 2.对中偏差<0.05mm; 3.紧固力矩符合要求; 4.电气接线正确; 5.接地可靠。安装后需试运行验收。",
        "answer_kw": "install",
    },
    {
        "question": "{equip}更换{part}后需要调试什么?",
        "context": "{equip}更换{part}后调试项目: 1.检查运行参数; 2.校准传感器; 3.测试保护功能; 4.记录基线数据; 5.观察运行{hours}小时无异常后交付。",
        "answer_kw": "commissioning",
    },
    {
        "question": "{equip}的{part}故障率统计是怎样的?",
        "context": "根据历史数据, {equip}{part}年均故障率为{rate}%, 主要故障模式: 磨损{wear}%、老化{aging}%、过压{overvolt}%。MTBF为{mtbf}小时。",
        "answer_kw": "statistics",
    },
    {
        "question": "{equip}出现{symptom}时应如何处理?",
        "context": "{equip}出现{symptom}的处理: 1.记录故障现象和时间; 2.检查相关参数; 3.对照故障树排查; 4.采取临时措施; 5.安排停机检修。",
        "answer_kw": "troubleshoot",
    },
    {
        "question": "{equip}的{part}备件库存建议是多少?",
        "context": "{equip}{part}建议库存: 关键备件{key_qty}件, 一般备件{general_qty}件。库存周期{cycle}个月。备件管理需遵循先进先出原则。",
        "answer_kw": "spare",
    },
    {
        "question": "{equip}维护保养记录应该包括哪些内容?",
        "context": "维护保养记录内容: 1.设备编号和名称; 2.保养日期和时间; 3.保养类型(日常/定期/故障); 4.更换部件清单; 5.发现的问题; 6.处理措施; 7.执行人签名。",
        "answer_kw": "record",
    },
    {
        "question": "{equip}的{part}如何检查磨损程度?",
        "context": "{equip}{part}磨损检查方法: 1.目视检查表面状态; 2.使用量具测量尺寸; 3.检查间隙是否符合标准; 4.分析润滑油中的金属屑; 5.振动监测分析。",
        "answer_kw": "wear",
    },
    {
        "question": "{equip}的运行效率如何评估?",
        "context": "{equip}效率评估方法: 1.对比设计参数和实际运行数据; 2.计算能效比; 3.分析能耗趋势; 4.检查是否存在泄漏或损失; 5.定期能效测试。",
        "answer_kw": "efficiency",
    },
    {
        "question": "{equip}的{part}异常温升怎么排查?",
        "context": "{equip}{part}温升异常排查: 1.检查负载是否超标; 2.确认散热系统正常; 3.检查通风通道; 4.测量绕组电阻; 5.检查轴承润滑。",
        "answer_kw": "temperature",
    },
    {
        "question": "{equip}的年度检修计划怎么制定?",
        "context": "年度检修计划制定: 1.汇总设备运行数据; 2.分析故障历史; 3.确定检修项目和周期; 4.编制备件采购计划; 5.安排停机时间; 6.编制检修方案和安全措施。",
        "answer_kw": "annual",
    },
    {
        "question": "{equip}的{part}如何检测绝缘性能?",
        "context": "{equip}{part}绝缘检测: 1.使用兆欧表测量绝缘电阻; 2.值应>1MΩ; 3.进行耐压试验; 4.吸收比>1.3; 5.记录环境温度湿度。",
        "answer_kw": "insulation",
    },
    {
        "question": "{equip}更换滤芯的标准流程是什么?",
        "context": "滤芯更换流程: 1.停机并泄压; 2.拆除旧滤芯; 3.清洁滤壳; 4.检查密封圈; 5.安装新滤芯; 6.注油排气; 7.试运行检查压差。",
        "answer_kw": "filter",
    },
    {
        "question": "{equip}的{part}需要定期润滑吗?",
        "context": "{equip}{part}润滑要求: 润滑点{points}个, 使用{grease}润滑脂, 每{interval}加注一次, 每次{amount}克。注油后运行检查温度和振动。",
        "answer_kw": "lubrication",
    },
    {
        "question": "{equip}的{part}密封失效怎么处理?",
        "context": "{equip}{part}密封失效处理: 1.停机泄压; 2.拆除旧密封; 3.检查密封面; 4.更换密封件; 5.按力矩紧固; 6.试压检漏。",
        "answer_kw": "seal",
    },
    {
        "question": "{equip}的{part}故障会触发什么告警?",
        "context": "{equip}{part}故障告警: 1.本地指示灯闪烁; 2.BMS系统推送告警信息; 3.短信/邮件通知值班人员; 4.生成工单。告警级别为{level}。",
        "answer_kw": "alarm",
    },
]

# Equipment and parts pools
EQUIPMENT = [
    "空调主机", "冷水机组", "冷却塔", "冷冻泵", "冷却泵",
    "电梯", "消防泵", "排烟风机", "送风机", "新风机组",
    "配电柜", "UPS", "发电机", "变压器", "蓄电池组",
    "路灯控制系统", "电梯控制系统", "BA控制器", "DDC箱", "传感器"
]

PARTS = [
    "压缩机", "冷却塔风机", "冷冻水泵", "冷却水泵",
    "电梯门机", "制动器", "轿厢", "扶梯踏板",
    "消防泵叶轮", "阀门", "压力表", "温度传感器",
    "配电柜断路器", "UPS电池", "发电机引擎", "变压器绕组",
    "路灯控制器", "电梯控制板", "DDC模块", "传感器探头"
]

INTERVALS = ["3个月", "6个月", "1年", "2年"]
TEMP_RANGES = ["-10~50°C", "0~60°C", "-20~80°C"]
PRESSURES = ["0.4~0.6MPa", "0.6~0.8MPa", "0.8~1.0MPa"]
VIBS = ["2.8", "4.5", "7.1"]
CODES = ["E001", "E002", "F003", "W010", "ALM05"]
HOURS = ["2000", "4000", "8000"]
YEARS = ["5", "8", "10"]
INSPECT_INTERVALS = ["1", "2", "3"]
GEAR_OILS = ["L-CKD320", "L-CKD460"]
BEARING_OILS = ["L-AN46", "L-AN68"]
FREQS = ["每周", "每月", "每季度"]
WEARS = ["35", "42", "50"]
AGINGS = ["25", "30", "35"]
OVERVOLTS = ["15", "18", "20"]
MTBFS = ["8760", "17520", "26280"]
SYMTOMS = ["异常噪声", "振动过大", "温度过高", "压力异常", "能耗升高"]
KEY_QTYS = ["2", "3", "5"]
GENERAL_QTYS = ["5", "8", "10"]
CYCLES = ["6", "12"]
RATES = ["2.5", "3.8", "5.2"]
POINTS = ["4", "6", "8"]
GREASES = ["锂基脂", "钙基脂", "复合锂基脂"]
AMOUNTS = ["10", "15", "20"]
LEVELS = ["一级", "二级", "三级"]


def fill_maintenance(i: int) -> dict:
    """Generate a maintenance category QA pair."""
    tpl = MAINTENANCE_TEMPLATES[i % len(MAINTENANCE_TEMPLATES)]
    equip = EQUIPMENT[i % len(EQUIPMENT)]
    part = PARTS[i % len(PARTS)]
    q = tpl["question"].format(
        equip=equip, part=part,
        interval=INTERVALS[i % len(INTERVALS)],
        temp_range=TEMP_RANGES[i % len(TEMP_RANGES)],
        pressure=PRESSURES[i % len(PRESSURES)],
        vib=VIBS[i % len(VIBS)],
        code=CODES[i % len(CODES)],
        hours=HOURS[i % len(HOURS)],
        years=YEARS[i % len(YEARS)],
        inspect_interval=INSPECT_INTERVALS[i % len(INSPECT_INTERVALS)],
        gear_oil=GEAR_OILS[i % len(GEAR_OILS)],
        bearing_oil=BEARING_OILS[i % len(BEARING_OILS)],
        freq=FREQS[i % len(FREQS)],
        points=POINTS[i % len(POINTS)],
        grease=GREASES[i % len(GREASES)],
        amount=AMOUNTS[i % len(AMOUNTS)],
        level=LEVELS[i % len(LEVELS)],
        wear=WEARS[i % len(WEARS)],
        aging=AGINGS[i % len(AGINGS)],
        overvolt=OVERVOLTS[i % len(OVERVOLTS)],
        mtbf=MTBFS[i % len(MTBFS)],
        symptom=SYMTOMS[i % len(SYMTOMS)],
        key_qty=KEY_QTYS[i % len(KEY_QTYS)],
        general_qty=GENERAL_QTYS[i % len(GENERAL_QTYS)],
        cycle=CYCLES[i % len(CYCLES)],
        rate=RATES[i % len(RATES)],
    )
    c = tpl["context"].format(
        equip=equip, part=part,
        interval=INTERVALS[i % len(INTERVALS)],
        temp_range=TEMP_RANGES[i % len(TEMP_RANGES)],
        pressure=PRESSURES[i % len(PRESSURES)],
        vib=VIBS[i % len(VIBS)],
        code=CODES[i % len(CODES)],
        hours=HOURS[i % len(HOURS)],
        years=YEARS[i % len(YEARS)],
        inspect_interval=INSPECT_INTERVALS[i % len(INSPECT_INTERVALS)],
        gear_oil=GEAR_OILS[i % len(GEAR_OILS)],
        bearing_oil=BEARING_OILS[i % len(BEARING_OILS)],
        freq=FREQS[i % len(FREQS)],
        points=POINTS[i % len(POINTS)],
        grease=GREASES[i % len(GREASES)],
        amount=AMOUNTS[i % len(AMOUNTS)],
        level=LEVELS[i % len(LEVELS)],
        wear=WEARS[i % len(WEARS)],
        aging=AGINGS[i % len(AGINGS)],
        overvolt=OVERVOLTS[i % len(OVERVOLTS)],
        mtbf=MTBFS[i % len(MTBFS)],
        symptom=SYMTOMS[i % len(SYMTOMS)],
        key_qty=KEY_QTYS[i % len(KEY_QTYS)],
        general_qty=GENERAL_QTYS[i % len(GENERAL_QTYS)],
        cycle=CYCLES[i % len(CYCLES)],
        rate=RATES[i % len(RATES)],
    )
    return {
        "question": q,
        "answer": f"maint_doc_{i:04d}",
        "context": c,
        "kb_id": "maintenance",
    }


ALARM_TEMPLATES = [
    {
        "question": "{equip}触发{alarm}告警应该怎么处理?",
        "context": "{equip}{alarm}告警处理SOP: 1.确认告警信息和级别; 2.查看相关参数; 3.检查设备状态; 4.执行应急处置; 5.联系维修人员。告警确认时限:{time}分钟。",
    },
    {
        "question": "{equip}的{alarm}告警阈值是多少?",
        "context": "{equip}{alarm}告警阈值设定: 一级告警{level1}, 二级告警{level2}, 三级告警{level3}。超限后系统自动记录并推送通知。",
    },
    {
        "question": "{equip}频繁触发{alarm}告警是什么原因?",
        "context": "{equip}{alarm}告警频繁触发原因: 1.传感器漂移; 2.设备工况异常; 3.设定值不合理; 4.环境因素干扰。建议校准传感器并检查设备运行状态。",
        "context_detail": "排查顺序: 先软件后硬件, 先局部后整体。",
    },
    {
        "question": "{equip}的{alarm}告警需要多久响应?",
        "context": "{alarm}告警响应时限: 一级{r1}分钟, 二级{r2}分钟, 三级{r3}分钟。超时未响应将升级通知上级管理人员。",
    },
    {
        "question": "如何关闭{equip}的{alarm}告警静音?",
        "context": "{alarm}告警静音操作: 1.在BMS界面确认告警信息; 2.点击静音按钮; 3.静音时间不超过{time}分钟; 4.故障消除后告警自动恢复。",
    },
    {
        "question": "{equip}的{alarm}告警记录保存多久?",
        "context": "{alarm}告警记录保存期限: 一般告警{general}天, 重要告警{important}天, 事故告警永久保存。定期导出归档。",
    },
    {
        "question": "{equip}的{alarm}告警如何消音复位?",
        "context": "{alarm}告警消音复位: 1.点击声光告警消音; 2.确认故障已排除; 3.在BMS界面执行复位操作; 4.检查告警历史清零。",
    },
    {
        "question": "{equip}出现{alarm}告警时能继续运行吗?",
        "context": "{alarm}告警时运行策略: 一级告警需立即处理, 二级告警可短时运行但需监控, 三级告警不影响运行。具体以设备说明书为准。",
    },
    {
        "question": "{equip}的{alarm}告警如何批量确认?",
        "context": "{alarm}告警批量确认: 1.进入告警管理界面; 2.选择时间范围; 3.勾选同类告警; 4.执行批量确认操作。确认前需确保已查看关键告警。",
    },
    {
        "question": "{equip}的{alarm}告警会联动什么设备?",
        "context": "{alarm}告警联动策略: 1.自动启动备用设备; 2.关闭相关阀门; 3.启动排风系统; 4.推送通知给相关人员。联动逻辑可在BMS中配置。",
    },
    {
        "question": "{equip}的{alarm}告警怎么设置优先级?",
        "context": "告警优先级设置: 1.进入告警管理模块; 2.选择告警类型; 3.设定优先级(紧急/重要/一般); 4.配置通知方式。优先级影响响应时限和升级策略。",
    },
    {
        "question": "{equip}的{alarm}告警历史数据怎么导出?",
        "context": "告警历史导出: 1.进入历史记录模块; 2.选择查询条件(时间/类型/级别); 3.点击导出按钮; 4.支持CSV和PDF格式。",
    },
    {
        "question": "{equip}的{alarm}告警如何设置屏蔽?",
        "context": "告警屏蔽操作: 1.确认设备处于维护状态; 2.选择告警点进行屏蔽; 3.设置屏蔽原因和时间; 4.屏蔽期间需人工巡检。屏蔽需审批。",
    },
    {
        "question": "{equip}的{alarm}告警触发原因分析怎么做?",
        "context": "告警原因分析: 1.导出告警时间段数据; 2.对比历史正常数据; 3.分析参数变化趋势; 4.排查设备状态; 5.形成分析报告。",
    },
    {
        "question": "{equip}的{alarm}告警和{alarm2}告警同时触发如何处理?",
        "context": "复合告警处理: 1.优先处理高级别告警; 2.分析告警关联性; 3.检查共同影响因素; 4.按SOP逐项处置。注意防止次生告警。",
    },
    {
        "question": "{equip}的{alarm}告警在测试模式下会不会触发?",
        "context": "测试模式告警策略: 1.测试模式通常屏蔽部分告警; 2.安全相关告警不受屏蔽; 3.测试完成后需恢复告警设置; 4.测试记录需存档。",
    },
    {
        "question": "{equip}的{alarm}告警通知发送方式有哪些?",
        "context": "告警通知方式: 1.BMS界面弹窗; 2.短信通知; 3.邮件通知; 4.语音电话; 5.微信/企业微信推送。可根据级别配置组合。",
    },
    {
        "question": "{equip}的{alarm}告警误报怎么处理?",
        "context": "误报处理: 1.记录误报情况; 2.检查传感器状态; 3.校准或更换传感器; 4.调整告警阈值; 5.更新维护记录。连续误报需上报。",
    },
    {
        "question": "{equip}的{alarm}告警恢复后需要做什么?",
        "context": "告警恢复操作: 1.确认故障已排除; 2.执行告警复位; 3.检查设备运行状态; 4.记录恢复时间和原因; 5.更新维护工单。",
    },
    {
        "question": "{equip}的{alarm}告警延迟触发是什么原因?",
        "context": "告警延迟触发原因: 1.传感器响应时间; 2.通信延迟; 3.数据处理延迟; 4.网络带宽限制。可通过优化参数减少延迟。",
    },
    {
        "question": "{equip}的{alarm}告警阈值怎么调整?",
        "context": "告警阈值调整: 1.评估当前工况; 2.参考设备厂家建议; 3.在BMS中修改阈值; 4.测试确认新阈值有效; 5.更新告警文档。调整需审批。",
    },
    {
        "question": "{equip}的{alarm}告警与{alarm2}告警的区别是什么?",
        "context": "告警区别: {alarm}为{desc1}, {alarm2}为{desc2}。两者触发条件不同, 处理优先级不同, {alarm}优先处理。",
    },
    {
        "question": "{equip}的{alarm}告警如何设置确认时限?",
        "context": "告警确认时限设置: 1.进入告警管理; 2.选择告警类型; 3.设置确认时限(默认{default}分钟); 4.超时自动升级。不同级别可设不同时限。",
    },
    {
        "question": "{equip}的{alarm}告警数据可以用来做什么分析?",
        "context": "告警数据分析: 1.故障趋势分析; 2.设备健康评估; 3.维护计划优化; 4.根因分析; 5.预测性维护模型训练。",
    },
    {
        "question": "{equip}的{alarm}告警在节假日会自动升级吗?",
        "context": "节假日告警策略: 1.启用节假日值班表; 2.告警升级时间可按值班表调整; 3.紧急告警始终按标准时限升级; 4.值班人员需保持通讯畅通。",
    },
    {
        "question": "{equip}的{alarm}告警如何设置多級联动的逻辑?",
        "context": "多级联动配置: 1.定义告警依赖关系; 2.配置触发条件; 3.设置执行动作; 4.测试验证逻辑。注意避免循环触发。",
    },
    {
        "question": "{equip}的{alarm}告警记录可以共享给第三方系统吗?",
        "context": "告警数据共享: 1.通过API接口导出; 2.支持RESTful和MQTT协议; 3.需配置访问权限; 4.敏感信息需脱敏处理。",
    },
    {
        "question": "{equip}的{alarm}告警怎么排查传感器故障?",
        "context": "传感器故障排查: 1.检查供电电压; 2.测量信号输出; 3.对比标准值; 4.替换法确认; 5.校准或更换。",
    },
    {
        "question": "{equip}的{alarm}告警高峰期通常在什么时候?",
        "context": "告警高峰时段: 1.夏季空调高负荷期; 2.冬季供暖切换期; 3.设备老化期; 4.极端天气时段。需加强巡检和预防性维护。",
    },
    {
        "question": "{equip}的{alarm}告警处理完成后需要填写什么报告?",
        "context": "告警处理报告内容: 1.告警时间和内容; 2.处理过程和措施; 3.原因分析; 4.恢复时间; 5.改进建议。报告需存档备查。",
    },
]

ALARM_TYPES = [
    "温度过高", "压力异常", "电压不稳", "流量过低", "液位报警",
    "烟雾告警", "漏水告警", "门禁告警", "电力缺相", "功率因数低",
    "设备故障", "通信中断", "电池低电量", "压缩机高压", "冷凝压力高",
    "冷冻水温低", "冷却水温高", "风速异常", "湿度超标", "燃气泄漏"
]
ALARM_TYPES2 = [
    "温度过低", "压力过高", "电流过载", "流量过高", "液位过低",
    "火灾告警", "水浸告警", "入侵告警", "电压缺失", "谐波超标"
]
ALARM_LEVELS = ["35°C", "45°C", "55°C"]
ALARM_TIMES = ["5", "10", "15"]
ALARM_R1, ALARM_R2, ALARM_R3 = ["5", "10", "15"]
ALARM_GENERAL, ALARM_IMPORTANT = ["30", "90", "180"]
ALARM_IMPORTANT2 = ["365", "730"]
ALARM_LEVEL1, ALARM_LEVEL2, ALARM_LEVEL3 = ["35°C", "40°C", "45°C"]
ALARM_DESC1, ALARM_DESC2 = ["轻微异常", "严重故障"]
ALARM_DEFAULT = ["10", "15", "30"]


def fill_alarm(i: int) -> dict:
    tpl = ALARM_TEMPLATES[i % len(ALARM_TEMPLATES)]
    equip = EQUIPMENT[i % len(EQUIPMENT)]
    alarm = ALARM_TYPES[i % len(ALARM_TYPES)]
    alarm2 = ALARM_TYPES2[i % len(ALARM_TYPES2)]
    q = tpl["question"].format(equip=equip, alarm=alarm, alarm2=alarm2)
    c = tpl["context"].format(
        equip=equip, alarm=alarm, alarm2=alarm2,
        level1=ALARM_LEVEL1[i % len(ALARM_LEVEL1)],
        level2=ALARM_LEVEL2[i % len(ALARM_LEVEL2)],
        level3=ALARM_LEVEL3[i % len(ALARM_LEVEL3)],
        time=ALARM_TIMES[i % len(ALARM_TIMES)],
        r1=ALARM_R1, r2=ALARM_R2, r3=ALARM_R3,
        general=ALARM_GENERAL[i % len(ALARM_GENERAL)],
        important=ALARM_IMPORTANT[i % len(ALARM_IMPORTANT)],
        desc1=ALARM_DESC1, desc2=ALARM_DESC2,
        default=ALARM_DEFAULT[i % len(ALARM_DEFAULT)],
    )
    return {
        "question": q,
        "answer": f"alarm_doc_{i:04d}",
        "context": c,
        "kb_id": "alarm",
    }


ASSET_TEMPLATES = [
    {
        "question": "{equip}的{asset}基本信息是什么?",
        "context": "{equip}{asset}基本信息: 型号{model}, 序列号{serial}, 生产厂商{mfr}, 投运日期{date}, 质保期{warranty}年。",
    },
    {
        "question": "{equip}的{asset}位于哪个位置?",
        "context": "{equip}{asset}安装位置: {floor}层{room}, 坐标{x},{y}。附近设备: {nearby}。",
    },
    {
        "question": "{equip}的{asset}当前状态是什么?",
        "context": "{equip}{asset}当前状态: 运行/待机/离线。最后更新时间{time}。状态来源: BMS实时数据。",
    },
    {
        "question": "{equip}的{asset}规格参数有哪些?",
        "context": "{equip}{asset}规格: 额定功率{power}kW, 额定电压{voltage}V, 额定电流{current}A, 重量{weight}kg, 尺寸{size}mm。",
    },
    {
        "question": "{equip}的{asset}厂家联系方式是什么?",
        "context": "{equip}{asset}厂家信息: 厂商{mfr}, 服务热线{phone}, 邮箱{email}, 服务区域{region}。",
        "phone": "400-800-xxxx",
        "email": "support@example.com",
    },
    {
        "question": "{equip}的{asset}保修期到什么时候?",
        "context": "{equip}{asset}保修信息: 投运日期{date}, 保修期{warranty}年, 到期日{expire}。延保服务可联系厂家。",
    },
    {
        "question": "{equip}的{asset}最近一次维修是什么时候?",
        "context": "{equip}{asset}维修记录: 最近维修{repair_date}, 维修内容{repair_content}, 维修单位{repair_co}, 下次计划维修{next_repair}。",
    },
    {
        "question": "{equip}的{asset}更换日期是什么时候?",
        "context": "{equip}{asset}更换信息: 安装日期{install_date}, 设计寿命{life}年, 预计更换{replace_date}, 当前已运行{run_hours}小时。",
    },
    {
        "question": "{equip}的{asset}有哪些关联设备?",
        "context": "{equip}{asset}关联设备: 上游{upstream}, 下游{downstream}, 备用{backup}。关联关系可通过数字孪生模型查看。",
    },
    {
        "question": "{equip}的{asset} belongs to哪个租户?",
        "context": "{equip}{asset}资产归属: 租户ID{tenant_id}, 租户名称{tenant_name}, 部门{dept}, 责任人{owner}。",
    },
    {
        "question": "{equip}的{asset}的铭牌信息是什么?",
        "context": "{equip}{asset}铭牌: 型号{model}, 序列号{serial}, 出厂日期{mfg_date}, 额定参数{rated_params}, 认证标志{certs}。",
    },
    {
        "question": "{equip}的{asset}能耗数据在哪里查看?",
        "context": "{equip}{asset}能耗查询: 通过BMS能耗模块查看, 支持日/周/月/年维度统计。也可导出原始数据进行分析。",
    },
    {
        "question": "{equip}的{asset}的备件清单有哪些?",
        "context": "{equip}{asset}备件清单: 备件{spares}, 每个备件数量{qty}, 存放位置{location}, 采购渠道{channel}。",
    },
    {
        "question": "{equip}的{asset}的安装图纸在哪里?",
        "context": "{equip}{asset}安装图纸: 图纸编号{doc_no}, 版本{version}, 存放位置{location}, 可通过文档管理系统查询下载。",
    },
    {
        "question": "{equip}的{asset}的验收标准是什么?",
        "context": "{equip}{asset}验收标准: 依据{standard}, 验收项目{items}, 合格指标{criteria}, 验收流程{process}。",
    },
    {
        "question": "{equip}的{asset}的折旧年限是多久?",
        "context": "{equip}{asset}折旧信息: 原值{value}元, 折旧年限{years}年, 残值率{residual}%, 年折旧额{amount}元。",
    },
    {
        "question": "{equip}的{asset}的编码规则是什么?",
        "context": "{equip}{asset}编码: 格式{format}, 前缀{prefix}表示{meaning}, 后段{suffix}为流水号。编码规则详见资产管理规范。",
    },
    {
        "question": "{equip}的{asset}需要年检吗?",
        "context": "{equip}{asset}年检要求: 年检周期{period}, 上次年检{last_date}, 下次年检{next_date}, 年检机构{agency}。",
    },
    {
        "question": "{equip}的{asset}的运行噪音标准是多少?",
        "context": "{equip}{asset}噪音标准: 额定负载下≤{db}dB(A), 测试条件{conditions}, 测量方法{method}。",
    },
    {
        "question": "{equip}的{asset}故障时的紧急联系人是谁?",
        "context": "{equip}{asset}紧急联系: 值班电话{phone}, 设备厂家{mfr_phone}, 维保单位{maint_phone}, 负责人{manager}。",
    },
    {
        "question": "{equip}的{asset}的能效等级是多少?",
        "context": "{equip}{asset}能效: 能效等级{level}, 能效比{COP}kW/kW, 符合{standard}标准。",
    },
    {
        "question": "{equip}的{asset}的IP防护等级是什么?",
        "context": "{equip}{asset}防护等级: IP{ip_code}, 适用于{env}环境, 安装时需确保密封良好。",
    },
    {
        "question": "{equip}的{asset}的控制系统版本是什么?",
        "context": "{equip}{asset}控制版本: 固件版本{fw_ver}, 软件版本{sw_ver}, 更新日期{update_date}。可通过本地界面或BMS查看。",
    },
    {
        "question": "{equip}的{asset}有没有历史故障记录?",
        "context": "{equip}{asset}历史故障: 共{fault_count}次, 最近{last_fault}, 主要故障模式{fault_modes}, MTBF{mtbf}小时。",
    },
    {
        "question": "{equip}的{asset}的采购合同编号是什么?",
        "context": "{equip}{asset}采购信息: 合同编号{contract_no}, 采购日期{purchase_date}, 供应商{supplier}, 金额{amount}元。",
    },
    {
        "question": "{equip}的{asset}可以替换为什么型号?",
        "context": "{equip}{asset}替代型号: 推荐{replacement_model}, 兼容性{compatibility}, 替换注意事项{notes}。",
    },
    {
        "question": "{equip}的{asset}的在线监测数据有哪些?",
        "context": "{equip}{asset}在线监测: 温度{temp_channel}, 振动{vib_channel}, 电流{curr_channel}, 电压{volt_channel}。数据刷新频率{freq}秒。",
    },
    {
        "question": "{equip}的{asset}的运行年限是多少?",
        "context": "{equip}{asset}使用年限: 投运日期{date}, 已运行{years}年, 设计寿命{life}年, 剩余寿命{remain}年。",
    },
    {
        "question": "{equip}的{asset}的运维规程在哪里?",
        "context": "{equip}{asset}运维规程: 规程编号{doc_no}, 版本{version}, 最后修订{rev_date}, 存放于{location}。",
    },
    {
        "question": "{equip}的{asset}的二维码标签信息是什么?",
        "context": "{equip}{asset}二维码: 编码{qr_code}, 扫码可查看设备卡片, 包含基本信息、运行状态、维护记录。",
    },
]

ASSET_TYPES = [
    "冷水机组", "冷却塔", "冷冻水泵", "冷却水泵", "电梯主机",
    "配电柜", "UPS主机", "发电机", "变压器", "照明配电箱",
    "BA控制器", "DDC箱", "传感器", "执行器", "风机盘管",
    "新风机组", "排烟风机", "消防泵", "排污泵", "稳压设备"
]
ASSET_PARTS = [
    "主机", "水泵", "风机", "电机", "控制器",
    "传感器", "执行器", "阀门", "配电箱", "控制柜"
]
MODELS = ["CHT-200", "LTP-50", "EF-100", "TR-500", "UPS-10K"]
SERIALS = ["SN20240001", "SN20240002", "SN20240003"]
MFRS = ["格力", "大金", "三菱", "施耐德", "西门子"]
DATES = ["2020-03-15", "2021-06-20", "2022-01-10", "2023-09-01"]
WARRANTIES = ["2", "3", "5"]
FLOORS = ["B1", "1F", "5F", "10F", "屋顶"]
ROOMS = ["空调机房", "配电房", "电梯机房", "消防泵房", "强弱电井"]
COORDS = [("12.5", "34.8"), ("56.2", "78.1")]
NEARBYs = ["邻近设备A", "管道井", "走廊"]
TIMES = ["2026-09-07 10:00", "2026-09-07 09:30"]
POWERS = ["100", "150", "200", "250", "300"]
VOLTAGES = ["380", "660", "10000"]
CURRENTS = ["150", "200", "250"]
WEIGHTS = ["500", "800", "1200"]
SIZES = ["1200×800×1500"]
PHONES = ["400-800-1234", "400-800-5678"]
EMAILS = ["support@gree.com", "service@daikin.com"]
REGIONS = ["华南", "华东", "华北"]
EXPIRE_DATES = ["2026-03-15", "2027-06-20"]
REPAIR_DATES = ["2025-08-10", "2026-01-15"]
REPAIR_CONTENTS = ["更换轴承", "清洗换热器", "校准传感器"]
REPAIR_COs = ["甲方维保", "厂家服务", "第三方维保"]
NEXT_REPAIRS = ["2026-12-01", "2027-03-15"]
INSTALL_DATES = ["2020-03-15", "2021-06-20"]
LIFES = ["10", "15", "20"]
REPLACE_DATES = ["2030-03-15", "2036-06-20"]
RUN_HOURS = ["43800", "21900", "10950"]
UPSTREAMS = ["上级配电柜", "冷冻水源"]
DOWNSREAMS = ["末端设备", "回水管道"]
BACKUPS = ["备用机组B", "备用泵B"]
TENANT_IDS = ["T001", "T002", "T003"]
TENANT_NAMES = ["A公司", "B公司", "C公司"]
DEPTS = ["物业部", "工程部", "安保部"]
OWNERS = ["张三", "李四", "王五"]
MFG_DATES = ["2020-02-01", "2021-05-01"]
RATED_PARAMS = ["380V/50Hz"]
CERTS = ["CCC", "CE"]
STDs = ["GB/T 19001", "ISO 9001"]
ITEMS = ["外观检查", "功能测试", "性能测试"]
CRITERIAS = ["符合设计要求"]
PROCESSES = ["自检→初验→终验"]
VALUES = ["50000", "80000", "120000"]
YEARS_DEP = ["5", "10", "15"]
RESIDUALS = ["5", "10"]
AMOUNTS_DEP = ["9500", "7600", "11400"]
FORMATS = ["EQ-YYYY-NNNN"]
PREFIX_MEANINGS = ["设备类别码"]
SUFFIXES = ["0001~9999"]
PERIODS = ["1年", "2年", "5年"]
LAST_DATES = ["2025-06-15", "2026-01-15"]
NEXT_DATES = ["2026-06-15", "2027-01-15"]
AGENCIES = ["特种设备检验院", "第三方检测机构"]
DBS = ["65", "70", "75"]
CONDITIONS = ["额定负载, 距离1m"]
METHODS = ["GB/T 3767"]
MANAGERs = ["赵主管", "钱主任"]
LEVELS_EN = ["1级", "2级", "3级"]
COPs = ["5.0", "4.5", "4.0"]
IP_CODES = ["IP54", "IP65"]
ENVS = ["室内", "户外", "潮湿"]
FW_VERs = ["V2.1.3", "V3.0.0"]
SW_VERs = ["V4.2.1", "V5.0.0"]
UPDATE_DATES = ["2025-06-01", "2026-01-01"]
FAULT_COUNTS = ["3", "5", "8"]
LAST_FAULTS = ["2025-12-01", "2026-03-15"]
FAULT_MODES = ["轴承磨损", "传感器故障"]
MTBFS = ["8760", "17520"]
CONTRACT_NOs = ["CT2024-001", "CT2024-002"]
PURCHASE_DATES = ["2024-01-15", "2024-06-20"]
SUPPLIERs = ["供应商A", "供应商B"]
AMOUNTS_PUR = ["150000", "280000"]
REPLACEMENT_MODELS = ["CHT-250", "LTP-60"]
COMPATIBILITIES = ["完全兼容", "需适配"]
NOTESs = ["接口需改造"]
TEMP_CH = ["PT100#1", "热电偶#2"]
VIB_CH = ["加速度计#1"]
CURR_CH = ["霍尔传感器#1"]
VOLT_CH = ["电压互感器#1"]
FREQS_SCAN = ["1", "5", "10"]
DOC_NOs = ["DOC-001", "DOC-002"]
VERSIONS = ["V1.0", "V2.1"]
REV_DATES = ["2024-01-01", "2025-06-01"]
LOCATIONS = ["文档服务器", "本地存储"]
QR_CODES = ["QR001", "QR002"]
SPARES = ["轴承6205", "密封圈O型圈"]
QTYS = ["2", "5", "10"]
SPARE_LOCS = ["备件库A", "备件库B"]
SPARE_CHANS = ["京东工业品", "厂家直供"]


def fill_asset(i: int) -> dict:
    tpl = ASSET_TEMPLATES[i % len(ASSET_TEMPLATES)]
    equip = EQUIPMENT[i % len(EQUIPMENT)]
    part = ASSET_PARTS[i % len(ASSET_PARTS)]
    q = tpl["question"].format(equip=equip, asset=part)
    c = tpl["context"].format(
        equip=equip, asset=part,
        model=MODELS[i % len(MODELS)],
        serial=SERIALS[i % len(SERIALS)],
        mfr=MFRS[i % len(MFRS)],
        date=DATES[i % len(DATES)],
        warranty=WARRANTIES[i % len(WARRANTIES)],
        floor=FLOORS[i % len(FLOORS)],
        room=ROOMS[i % len(ROOMS)],
        x=COORDS[i % len(COORDS)][0],
        y=COORDS[i % len(COORDS)][1],
        nearby=NEARBYs[i % len(NEARBYs)],
        time=TIMES[i % len(TIMES)],
        power=POWERS[i % len(POWERS)],
        voltage=VOLTAGES[i % len(VOLTAGES)],
        current=CURRENTS[i % len(CURRENTS)],
        weight=WEIGHTS[i % len(WEIGHTS)],
        size=SIZES[0],
        phone=PHONES[i % len(PHONES)],
        email=EMAILS[i % len(EMAILS)],
        region=REGIONS[i % len(REGIONS)],
        expire_date=EXPIRE_DATES[i % len(EXPIRE_DATES)],
        repair_date=REPAIR_DATES[i % len(REPAIR_DATES)],
        repair_content=REPAIR_CONTENTS[i % len(REPAIR_CONTENTS)],
        repair_co=REPAIR_COs[i % len(REPAIR_COs)],
        next_repair=NEXT_REPAIRS[i % len(NEXT_REPAIRS)],
        install_date=INSTALL_DATES[i % len(INSTALL_DATES)],
        life=LIFES[i % len(LIFES)],
        replace_date=REPLACE_DATES[i % len(REPLACE_DATES)],
        run_hours=RUN_HOURS[i % len(RUN_HOURS)],
        upstream=UPSTREAMS[i % len(UPSTREAMS)],
        downstream=DOWNSREAMS[i % len(DOWNSREAMS)],
        backup=BACKUPS[i % len(BACKUPS)],
        tenant_id=TENANT_IDS[i % len(TENANT_IDS)],
        tenant_name=TENANT_NAMES[i % len(TENANT_NAMES)],
        dept=DEPTS[i % len(DEPTS)],
        owner=OWNERS[i % len(OWNERS)],
        mfg_date=MFG_DATES[i % len(MFG_DATES)],
        rated_params=RATED_PARAMS[0],
        certs=CERTS[i % len(CERTS)],
        standard=STDs[i % len(STDs)],
        items=ITEMS[i % len(ITEMS)],
        criteria=CRITERIAS[0],
        process=PROCESSES[0],
        value=VALUES[i % len(VALUES)],
        years=YEARS_DEP[i % len(YEARS_DEP)],
        residual=RESIDUALS[i % len(RESIDUALS)],
        amount=AMOUNTS_DEP[i % len(AMOUNTS_DEP)],
        format=FORMATS[0],
        prefix=PREFIX_MEANINGS[0],
        suffix=SUFFIXES[0],
        period=PERIODS[i % len(PERIODS)],
        last_date=LAST_DATES[i % len(LAST_DATES)],
        next_date=NEXT_DATES[i % len(NEXT_DATES)],
        agency=AGENCIES[i % len(AGENCIES)],
        db=DBS[i % len(DBS)],
        conditions=CONDITIONS[0],
        method=METHODS[0],
        manager=MANAGERs[i % len(MANAGERs)],
        level=LEVELS_EN[i % len(LEVELS_EN)],
        COP=COPs[i % len(COPs)],
        ip_code=IP_CODES[i % len(IP_CODES)],
        env=ENVS[i % len(ENVS)],
        fw_ver=FW_VERs[i % len(FW_VERs)],
        sw_ver=SW_VERs[i % len(SW_VERs)],
        update_date=UPDATE_DATES[i % len(UPDATE_DATES)],
        fault_count=FAULT_COUNTS[i % len(FAULT_COUNTS)],
        last_fault=LAST_FAULTS[i % len(LAST_FAULTS)],
        fault_modes=FAULT_MODES[i % len(FAULT_MODES)],
        mtbf=MTBFS[i % len(MTBFS)],
        contract_no=CONTRACT_NOs[i % len(CONTRACT_NOs)],
        purchase_date=PURCHASE_DATES[i % len(PURCHASE_DATES)],
        supplier=SUPPLIERs[i % len(SUPPLIERs)],
        amount_pur=AMOUNTS_PUR[i % len(AMOUNTS_PUR)],
        replacement_model=REPLACEMENT_MODELS[i % len(REPLACEMENT_MODELS)],
        compatibility=COMPATIBILITIES[i % len(COMPATIBILITIES)],
        notes=NOTESs[i % len(NOTESs)],
        temp_ch=TEMP_CH[i % len(TEMP_CH)],
        vib_ch=VIB_CH[0],
        curr_ch=CURR_CH[0],
        volt_ch=VOLT_CH[0],
        freq=FREQS_SCAN[i % len(FREQS_SCAN)],
        doc_no=DOC_NOs[i % len(DOC_NOs)],
        version=VERSIONS[i % len(VERSIONS)],
        rev_date=REV_DATES[i % len(REV_DATES)],
        location=LOCATIONS[i % len(LOCATIONS)],
        qr_code=QR_CODES[i % len(QR_CODES)],
        spare=SPARES[i % len(SPARES)],
        qty=QTYS[i % len(QTYS)],
        spare_loc=SPARE_LOCS[i % len(SPARE_LOCS)],
        spare_chan=SPARE_CHANS[i % len(SPARE_CHANS)],
        phone=PHONES[i % len(PHONES)],
    )
    return {
        "question": q,
        "answer": f"asset_doc_{i:04d}",
        "context": c,
        "kb_id": "asset_info",
    }


ENERGY_TEMPLATES = [
    {
        "question": "{equip}本月耗电量是多少?",
        "context": "{equip}本月耗电量: {kwh}kWh, 日均{kwh_day}kWh, 同比变化{yoy}%, 环比变化{mom}%。峰值负荷{peak}kW, 发生在{peak_time}。",
    },
    {
        "question": "{equip}的能效指标如何?",
        "context": "{equip}能效指标: COP{cop}, EER{eer}, 功率因数{pf}, 负载率{load}%, 运行效率{eff}%。",
    },
    {
        "question": "{equip}的功率因数如何改善?",
        "context": "{equip}功率因数改善: 当前{pf}, 目标≥0.95, 方案: 加装电容补偿柜, 容量{cap}kVar, 预期功率因数{pf_target}。",
    },
    {
        "question": "{equip}的负载率是多少?",
        "context": "{equip}负载率: 当前{load}%, 平均{load_avg}%, 峰值{load_peak}%, 谷值{load_valley}%。额定功率{rated}kW。",
    },
    {
        "question": "{equip}的用电峰谷时段怎么安排?",
        "context": "{equip}峰谷安排: 峰时段{peak_period}, 平时段{flat_period}, 谷时段{valley_period}。建议谷时段运行{valley_hours}小时。",
    },
    {
        "question": "{equip}的节能措施有哪些?",
        "context": "{equip}节能措施: 1.优化启停策略; 2.变频改造; 3.余热回收; 4.智能控制。预计节能{saving}%。",
    },
    {
        "question": "{equip}的实时功率数据在哪里看?",
        "context": "{equip}实时功率: 通过BMS能源监控模块查看, 刷新频率{freq}秒, 数据延迟<3秒。",
    },
    {
        "question": "{equip}的电能质量如何?",
        "context": "{equip}电能质量: 电压偏差{volt_dev}%, 频率偏差{freq_dev}Hz, 谐波畸变率THD{thd}%, 三相不平衡{unbalance}%。",
    },
    {
        "question": "{equip}的耗气量/耗水量是多少?",
        "context": "{equip}能耗数据: 耗电量{kwh}kWh, 耗水量{water}m³, 耗天然气{gas}m³。折算标煤{coal}kg。",
    },
    {
        "question": "{equip}的碳排放量怎么计算?",
        "context": "{equip}碳排放: 年排放{co2}tCO₂, 排放因子{factor}kgCO₂/kWh, 统计范围{scope}。",
    },
    {
        "question": "{equip}的需量电费怎么优化?",
        "context": "{equip}需量电费优化: 当前需量{demand}kW, 合约需量{contract}kW, 建议{advice}。可节省电费{save}元/月。",
    },
    {
        "question": "{equip}的功率因数电费调整是多少?",
        "context": "{equip}功率因数调整: 当前{pf}, 标准{std_pf}, 调整系数{factor}, 增减电费{adjust}元。",
    },
    {
        "question": "{equip}的用电负荷曲线怎么看?",
        "context": "{equip}负荷曲线: 日负荷曲线呈{shape}分布, 峰谷差{diff}kW, 利用系数{util}。",
    },
    {
        "question": "{equip}的备用电源容量够吗?",
        "context": "{equip}备用电源: 发电机容量{gen_cap}kW, 当前负载{load}kW, 备用容量{reserve}kW, 可满足{percent}%负载需求。",
    },
    {
        "question": "{equip}的变压器损耗是多少?",
        "context": "{equip}变压器损耗: 空载损耗{no_load}kW, 负载损耗{load_loss}kW, 总损耗{total_loss}kW, 效率{eff}%。",
    },
    {
        "question": "{equip}的谐波含量超标吗?",
        "context": "{equip}谐波: THD{thd}%, 5次谐波{h5}%, 7次谐波{h7}%, 11次谐波{h11}%。标准限值{limit}%。",
    },
    {
        "question": "{equip}的用电申报容量是多少?",
        "context": "{equip}申报容量: 合同容量{contract}kVA, 实际最大需量{max_demand}kW, 容量利用率{util}%。",
    },
    {
        "question": "{equip}的峰段用电占比多少?",
        "context": "{equip}峰段用电: 峰段{kwh_peak}kWh, 占比{peak_pct}%, 谷段{kwh_valley}kWh, 占比{valley_pct}%。",
    },
    {
        "question": "{equip}的电能计费方式是什么?",
        "context": "{equip}计费方式: 两部制电价, 基本电费{base}元/kVA·月, 电度电费{energy}元/kWh, 功率因数调整{pf_adj}。",
    },
    {
        "question": "{equip}的能效对标结果如何?",
        "context": "{equip}能效对标: 实际{actual}kWh/m²·年, 标杆{benchmark}kWh/m²·年, 差距{gap}%, 改进空间{space}%。",
    },
    {
        "question": "{equip}的需量申报怎么调整?",
        "context": "{equip}需量申报: 当前申报{declare}kW, 实际最大需量{actual_max}kW, 建议调整为{suggest}kW。",
    },
    {
        "question": "{equip}的绿电使用比例是多少?",
        "context": "{equip}绿电: 光伏发电{kwh_solar}kWh, 占比{pct}%。剩余来自电网。",
    },
    {
        "question": "{equip}的能效管理系统怎么配置?",
        "context": "{equip}能效管理: 数据采集{freq}秒, 报表周期{period}, 告警阈值{threshold}, 报表导出{format}。",
    },
    {
        "question": "{equip}的电压偏差范围是多少?",
        "context": "{equip}电压偏差: 额定{rated}V, 实际{actual}V, 偏差{dev}%, 标准范围±{std_range}%。",
    },
    {
        "question": "{equip}的三相电流不平衡度多少?",
        "context": "{equip}三相不平衡: A相{ia}A, B相{ib}A, C相{ic}A, 不平衡度{unbal}%。标准≤{limit}%。",
    },
    {
        "question": "{equip}的功率因数补偿容量怎么计算?",
        "context": "{equip}补偿容量: 当前{pf_curr}, 目标{pf_target}, 需补偿{cap}kVar。电容柜配置{config}。",
    },
    {
        "question": "{equip}的能耗强度指标是什么?",
        "context": "{equip}能耗强度: {intensity}kWh/m²·年, 行业先进值{advanced}kWh/m²·年, 基准值{baseline}kWh/m²·年。",
    },
    {
        "question": "{equip}的电能表精度等级是多少?",
        "context": "{equip}电能表: 精度等级{accuracy}级, 校验周期{cal_period}年, 最近校验{last_cal}。",
    },
    {
        "question": "{equip}的负荷预测准确度如何?",
        "context": "{equip}负荷预测: 日预测MAPE{mape}%、周预测{w_mape}%、月预测{m_mape}%。预测模型{model}。",
    },
    {
        "question": "{equip}的可再生能源消纳情况?",
        "context": "{equip}可再生能源: 太阳能发电{sv}kWh, 风电{wf}kWh, 总消纳{consume}kWh, 自发自用比例{self_pct}%。",
    },
]

EQUIP_ENERGY = [
    "空调系统", "照明系统", "电梯系统", "动力系统", "暖通系统",
    "给排水系统", "动力系统", "办公用电", "公共照明", "地下车库"
]
KWH_VALS = ["12500", "8200", "15600", "6800", "22000"]
KWH_DAY_VALS = ["417", "273", "520", "227", "733"]
YOY_VALS = ["-5.2", "+3.1", "-8.7", "+1.5", "-12.3"]
MOM_VALS = ["+2.1", "-4.5", "+6.8", "-1.2", "+3.9"]
PEAK_VALS = ["180", "250", "320", "150", "400"]
PEAK_TIMES = ["14:00", "10:30", "16:00", "11:00", "15:30"]
COP_VALS = ["4.8", "5.2", "4.5", "5.0", "4.2"]
EER_VALS = ["3.2", "3.5", "3.0", "3.8", "2.8"]
PF_VALS = ["0.85", "0.92", "0.78", "0.95", "0.88"]
LOAD_VALS = ["75", "82", "68", "90", "55"]
EFF_VALS = ["92", "95", "88", "96", "90"]
PF_TARGET_VALS = ["0.95", "0.98"]
CAP_VALS = ["200", "300", "150", "250", "400"]
LOAD_AVG_VALS = ["70", "65", "75", "60", "80"]
LOAD_PEAK_VALS = ["95", "88", "92", "100", "85"]
LOAD_VALLEY_VALS = ["30", "25", "35", "20", "40"]
RATED_VALS = ["200", "300", "150", "250", "400"]
PEAK_PERIODS = ["8:00-11:00, 17:00-21:00"]
FLAT_PERIODS = ["11:00-17:00"]
VALLEY_PERIODS = ["23:00-7:00"]
VALLEY_HOURS_VALS = ["8", "10", "6", "12", "8"]
SAVING_VALS = ["15", "20", "12", "25", "18"]
FREQ_VALS = ["5", "10", "1", "3", "2"]
VOLT_DEV_VALS = ["+2.1", "-1.5", "+3.0", "-2.8", "+1.0"]
FREQ_DEV_VALS = ["±0.05", "±0.1", "±0.02"]
THD_VALS = ["8.5", "5.2", "12.0", "3.8", "15.5"]
UNBALANCE_VALS = ["3.2", "5.1", "2.0", "8.5", "4.0"]
WATER_VALS = ["500", "800", "300", "1200", "600"]
GAS_VALS = ["2000", "3500", "1500", "4000", "2800"]
COAL_VALS = ["625", "1094", "469", "1250", "875"]
DEMAND_VALS = ["180", "250", "320", "150", "400"]
CONTRACT_VALS = ["200", "300", "350", "160", "420"]
SAVE_VALS = ["800", "1200", "600", "1500", "900"]
STD_PF_VALS = ["0.90", "0.95"]
PF_FACTOR_VALS = ["1.00", "0.95", "1.05"]
PF_ADJ_VALS = ["+0", "-200", "+150", "0", "-300"]
PEAK_PCTS = ["35", "42", "28", "48", "38"]
VALLEY_PCTS = ["25", "18", "32", "15", "22"]
BASE_VALS = ["24", "36", "18", "42", "30"]
ENERGY_VALS = ["0.56", "0.62", "0.50", "0.68", "0.55"]
PF_ADJ_RATE = ["±0.30", "±0.45", "±0.15", "±0.50", "±0.25"]
SHAPE_VALS = ["双峰", "单峰", "平峰"]
DIFF_VALS = ["120", "180", "90", "200", "150"]
UTIL_VALS = ["0.72", "0.65", "0.78", "0.60", "0.82"]
GEN_CAP_VALS = ["200", "300", "150", "400", "250"]
RESERVE_VALS = ["50", "80", "30", "100", "60"]
PERCENT_VALS = ["25", "33", "20", "40", "30"]
NO_LOAD_VALS = ["1.2", "2.0", "0.8", "2.5", "1.5"]
LOAD_LOSS_VALS = ["3.5", "5.0", "2.8", "6.0", "4.0"]
TOTAL_LOSS_VALS = ["4.7", "7.0", "3.6", "8.5", "5.5"]
THD2_VALS = ["8.5", "5.2", "12.0", "3.8", "15.5"]
H5_VALS = ["4.2", "2.8", "6.5", "1.5", "8.0"]
H7_VALS = ["2.1", "1.5", "3.8", "0.8", "4.5"]
H11_VALS = ["1.0", "0.5", "2.0", "0.3", "2.5"]
LIMIT_VALS = ["8", "5", "12", "5", "15"]
CONTRACT_KVA_VALS = ["200", "300", "150", "400", "250"]
MAX_DEMAND_VALS = ["180", "250", "320", "150", "400"]
UTIL_PCTS = ["90", "83", "213", "38", "160"]
KWH_PEAK_VALS = ["4500", "6000", "3200", "7500", "5000"]
KWH_VALLEY_VALS = ["2800", "2200", "4000", "1500", "3500"]
TWO_PART_VALS = ["两部制", "单一制"]
BASE_2_VALS = ["24", "36", "18"]
ENERGY_2_VALS = ["0.56", "0.62"]
ACTUAL_VALS = ["85", "92", "78", "105", "88"]
BENCHMARK_VALS = ["80", "85", "75", "90", "82"]
GAP_VALS = ["6.3", "8.2", "4.0", "16.7", "7.3"]
SPACE_VALS = ["10", "15", "8", "20", "12"]
DECLARE_VALS = ["200", "300", "150", "400", "250"]
ACTUAL_MAX_VALS = ["180", "250", "320", "150", "400"]
SUGGEST_VALS = ["190", "260", "310", "160", "380"]
SV_VALS = ["5000", "8000", "3000", "10000", "6000"]
PCT_VALS = ["15", "25", "10", "30", "20"]
FREQ2_VALS = ["5", "10", "1"]
PERIOD_VALS = ["日", "周", "月"]
THRESHOLD_VALS = ["80", "90", "70"]
FORMAT_VALS = ["PDF", "Excel", "CSV"]
RATED2_VALS = ["380", "400", "415"]
ACTUAL2_VALS = ["378", "395", "412"]
DEV2_VALS = ["-0.5", "+1.2", "-2.0"]
STD_RANGE_VALS = ["10", "7", "5"]
IA_VALS = ["150", "180", "160"]
IB_VALS = ["145", "175", "155"]
IC_VALS = ["155", "185", "165"]
UNBAL_VALS = ["3.2", "5.1", "2.0"]
LIMIT2_VALS = ["5", "10", "15"]
PF_CURR_VALS = ["0.82", "0.75", "0.88"]
PF_TARGET2_VALS = ["0.95", "0.98"]
CAP2_VALS = ["150", "200", "100"]
CAP_CONFIG_VALS = ["30kVar×5组", "50kVar×3组", "20kVar×8组"]
INTENSITY_VALS = ["85", "92", "78", "105", "88"]
ADVANCED_VALS = ["80", "85", "75"]
BASELINE_VALS = ["100", "110", "95"]
ACCURACY_VALS = ["0.5", "1.0", "0.2"]
CAL_PERIOD_VALS = ["1", "2", "3"]
LAST_CAL_VALS = ["2025-06-01", "2024-12-01"]
MAPE_VALS = ["3.2", "5.1", "2.0", "8.5", "4.0"]
W_MAPE_VALS = ["4.5", "6.0", "3.0"]
M_MAPE_VALS = ["5.0", "7.0", "4.0"]
MODEL_VALS = ["LSTM", "XGBoost", "ARIMA"]
WF_VALS = ["0", "0", "500", "0", "200"]
CONSUME_VALS = ["4800", "7800", "2800", "9800", "5800"]
SELF_PCT_VALS = ["96", "97", "93", "98", "95"]


def fill_energy(i: int) -> dict:
    tpl = ENERGY_TEMPLATES[i % len(ENERGY_TEMPLATES)]
    equip = EQUIP_ENERGY[i % len(EQUIP_ENERGY)]
    q = tpl["question"].format(equip=equip)
    c = tpl["context"].format(
        equip=equip,
        kwh=KWH_VALS[i % len(KWH_VALS)],
        kwh_day=KWH_DAY_VALS[i % len(KWH_DAY_VALS)],
        yoy=YOY_VALS[i % len(YOY_VALS)],
        mom=MOM_VALS[i % len(MOM_VALS)],
        peak=PEAK_VALS[i % len(PEAK_VALS)],
        peak_time=PEAK_TIMES[i % len(PEAK_TIMES)],
        cop=COP_VALS[i % len(COP_VALS)],
        eer=EER_VALS[i % len(EER_VALS)],
        pf=PF_VALS[i % len(PF_VALS)],
        load=LOAD_VALS[i % len(LOAD_VALS)],
        eff=EFF_VALS[i % len(EFF_VALS)],
        pf_target=PF_TARGET_VALS[i % len(PF_TARGET_VALS)],
        cap=CAP_VALS[i % len(CAP_VALS)],
        load_avg=LOAD_AVG_VALS[i % len(LOAD_AVG_VALS)],
        load_peak=LOAD_PEAK_VALS[i % len(LOAD_PEAK_VALS)],
        load_valley=LOAD_VALLEY_VALS[i % len(LOAD_VALLEY_VALS)],
        rated=RATED_VALS[i % len(RATED_VALS)],
        peak_period=PEAK_PERIODS[0],
        flat_period=FLAT_PERIODS[0],
        valley_period=VALLEY_PERIODS[0],
        valley_hours=VALLEY_HOURS_VALS[i % len(VALLEY_HOURS_VALS)],
        saving=SAVING_VALS[i % len(SAVING_VALS)],
        freq=FREQ_VALS[i % len(FREQ_VALS)],
        volt_dev=VOLT_DEV_VALS[i % len(VOLT_DEV_VALS)],
        freq_dev=FREQ_DEV_VALS[i % len(FREQ_DEV_VALS)],
        thd=THD_VALS[i % len(THD_VALS)],
        unbalance=UNBALANCE_VALS[i % len(UNBALANCE_VALS)],
        water=WATER_VALS[i % len(WATER_VALS)],
        gas=GAS_VALS[i % len(GAS_VALS)],
        coal=COAL_VALS[i % len(COAL_VALS)],
        co2=str(int(coal) * 0.785) if i % 5 == 0 else "125",
        factor="0.785",
        scope="范围I",
        demand=DEMAND_VALS[i % len(DEMAND_VALS)],
        contract=CONTRACT_VALS[i % len(CONTRACT_VALS)],
        advice=f"降低至{CONTRACT_VALS[(i+1) % len(CONTRACT_VALS)]}kW",
        save=SAVE_VALS[i % len(SAVE_VALS)],
        pf_curr=PF_VALS[i % len(PF_VALS)],
        std_pf=STD_PF_VALS[i % len(STD_PF_VALS)],
        factor_f=PF_FACTOR_VALS[i % len(PF_FACTOR_VALS)],
        adjust=PF_ADJ_VALS[i % len(PF_ADJ_VALS)],
        shape=SHAPE_VALS[i % len(SHAPE_VALS)],
        diff=DIFF_VALS[i % len(DIFF_VALS)],
        util=UTIL_VALS[i % len(UTIL_VALS)],
        gen_cap=GEN_CAP_VALS[i % len(GEN_CAP_VALS)],
        load_e=LOAD_VALS[i % len(LOAD_VALS)],
        reserve=RESERVE_VALS[i % len(RESERVE_VALS)],
        percent=PERCENT_VALS[i % len(PERCENT_VALS)],
        no_load=NO_LOAD_VALS[i % len(NO_LOAD_VALS)],
        load_loss=LOAD_LOSS_VALS[i % len(LOAD_LOSS_VALS)],
        total_loss=TOTAL_LOSS_VALS[i % len(TOTAL_LOSS_VALS)],
        eff_t=EFF_VALS[i % len(EFF_VALS)],
        thd2=THD2_VALS[i % len(THD2_VALS)],
        h5=H5_VALS[i % len(H5_VALS)],
        h7=H7_VALS[i % len(H7_VALS)],
        h11=H11_VALS[i % len(H11_VALS)],
        limit=LIMIT_VALS[i % len(LIMIT_VALS)],
        contract_kva=CONTRACT_KVA_VALS[i % len(CONTRACT_KVA_VALS)],
        max_demand=MAX_DEMAND_VALS[i % len(MAX_DEMAND_VALS)],
        util_p=UTIL_PCTS[i % len(UTIL_PCTS)],
        kwh_peak=KWH_PEAK_VALS[i % len(KWH_PEAK_VALS)],
        peak_pct=PEAK_PCTS[i % len(PEAK_PCTS)],
        kwh_valley=KWH_VALLEY_VALS[i % len(KWH_VALLEY_VALS)],
        valley_pct=VALLEY_PCTS[i % len(VALLEY_PCTS)],
        base=BASE_VALS[i % len(BASE_VALS)],
        energy=ENERGY_VALS[i % len(ENERGY_VALS)],
        pf_adj=PF_ADJ_RATE[i % len(PF_ADJ_RATE)],
        actual=ACTUAL_VALS[i % len(ACTUAL_VALS)],
        benchmark=BENCHMARK_VALS[i % len(BENCHMARK_VALS)],
        gap=GAP_VALS[i % len(GAP_VALS)],
        space=SPACE_VALS[i % len(SPACE_VALS)],
        declare=DECLARE_VALS[i % len(DECLARE_VALS)],
        actual_max=ACTUAL_MAX_VALS[i % len(ACTUAL_MAX_VALS)],
        suggest=SUGGEST_VALS[i % len(SUGGEST_VALS)],
        sv=SV_VALS[i % len(SV_VALS)],
        wf=WF_VALS[i % len(WF_VALS)],
        consume=CONSUME_VALS[i % len(CONSUME_VALS)],
        self_pct=SELF_PCT_VALS[i % len(SELF_PCT_VALS)],
        freq2=FREQ2_VALS[i % len(FREQ2_VALS)],
        period=PERIOD_VALS[i % len(PERIOD_VALS)],
        threshold=THRESHOLD_VALS[i % len(THRESHOLD_VALS)],
        format_f=FORMAT_VALS[i % len(FORMAT_VALS)],
        rated2=RATED2_VALS[i % len(RATED2_VALS)],
        actual2=ACTUAL2_VALS[i % len(ACTUAL2_VALS)],
        dev=DEV2_VALS[i % len(DEV2_VALS)],
        std_range=STD_RANGE_VALS[i % len(STD_RANGE_VALS)],
        ia=IA_VALS[i % len(IA_VALS)],
        ib=IB_VALS[i % len(IB_VALS)],
        ic=IC_VALS[i % len(IC_VALS)],
        unbal=UNBAL_VALS[i % len(UNBAL_VALS)],
        limit2=LIMIT2_VALS[i % len(LIMIT2_VALS)],
        pf_curr2=PF_CURR_VALS[i % len(PF_CURR_VALS)],
        pf_target2=PF_TARGET2_VALS[i % len(PF_TARGET2_VALS)],
        cap2=CAP2_VALS[i % len(CAP2_VALS)],
        cap_config=CAP_CONFIG_VALS[i % len(CAP_CONFIG_VALS)],
        intensity=INTENSITY_VALS[i % len(INTENSITY_VALS)],
        advanced=ADVANCED_VALS[i % len(ADVANCED_VALS)],
        baseline=BASELINE_VALS[i % len(BASELINE_VALS)],
        accuracy=ACCURACY_VALS[i % len(ACCURACY_VALS)],
        cal_period=CAL_PERIOD_VALS[i % len(CAL_PERIOD_VALS)],
        last_cal=LAST_CAL_VALS[i % len(LAST_CAL_VALS)],
        mape=MAPE_VALS[i % len(MAPE_VALS)],
        w_mape=W_MAPE_VALS[i % len(W_MAPE_VALS)],
        m_mape=M_MAPE_VALS[i % len(M_MAPE_VALS)],
        model=MODEL_VALS[i % len(MODEL_VALS)],
    )
    return {
        "question": q,
        "answer": f"energy_doc_{i:04d}",
        "context": c,
        "kb_id": "energy",
    }


ONTOLOGY_TEMPLATES = [
    {
        "question": "{entity}在本体模型中属于什么类型?",
        "context": "{entity}属于本体类型:{type_}, 父类:{parent}, 属性:{attrs}, 关系:{rels}。",
    },
    {
        "question": "{entity}的属性定义是什么?",
        "context": "{entity}属性: {attrs_desc}。数据类型:{dtype}, 必填:{required}, 取值范围:{range_}。",
    },
    {
        "question": "{entity}和{related}的关系是什么?",
        "context": "{entity}与{related}的关系:{rel_type}, 基数:{cardinality}, 方向:{direction}。",
    },
    {
        "question": "{entity}有哪些子类?",
        "context": "{entity}子类: {subclasses}。每个子类继承父类属性并扩展特有属性。",
    },
    {
        "question": "{entity}的命名空间是什么?",
        "context": "{entity}命名空间: {namespace}, URI前缀:{prefix}, 定义位置:{location}。",
    },
    {
        "question": "{entity}如何关联到物理设备?",
        "context": "{entity}关联方式: 通过binding规则绑定到{binding_target}, 绑定后可实时同步{sync_attrs}。",
    },
    {
        "question": "{entity}的约束条件有哪些?",
        "context": "{entity}约束: {constraints}。包括必填约束、格式约束、取值约束。",
    },
    {
        "question": "{entity}能否被实例化?",
        "context": "{entity}可实例化:{can_instantiate}, 实例化后生成{Twin}实体, 通过API访问。",
    },
    {
        "question": "{entity}在FIWARE语义体系中的对应关系是什么?",
        "context": "{entity}对应FIWARE:{fiware_type}, 属性映射:{mapping}。",
    },
    {
        "question": "{entity}如何定义时间序列数据?",
        "context": "{entity}时序数据: 数据类型{dtype}, 采样频率{freq}, 存储周期{retention}, 压缩方式{compress}。",
    },
    {
        "question": "{entity}的权限配置如何设置?",
        "context": "{entity}权限: 可读角色{read_roles}, 可写角色{write_roles}, 继承规则{inherit}。",
    },
    {
        "question": "{entity}的生命周期状态有哪些?",
        "context": "{entity}状态:{states}。状态转换:{transitions}。",
    },
    {
        "question": "{entity}的元数据版本管理策略是什么?",
        "context": "{entity}版本管理: 语义版本{semver}, 变更日志{changelog}, 向后兼容策略{compat}。",
    },
    {
        "question": "{entity}如何与其他租户共享数据?",
        "context": "{entity}共享: 共享模式{mode}, 数据范围{scope}, 访问控制{access}。",
    },
    {
        "question": "{entity}的查询语法是什么?",
        "context": "{entity}查询: SPARQL语法{sparql}, 支持过滤{filter}, 排序{order}。",
    },
    {
        "question": "{entity}的缓存策略是什么?",
        "context": "{entity}缓存: 缓存TTL{ttl}, 失效策略{invalidate}, 缓存命中{hit_rate}。",
    },
    {
        "question": "{entity}的索引策略是什么?",
        "context": "{entity}索引: 主索引{primary}, 二级索引{secondary}, 全文索引{fulltext}。",
    },
    {
        "question": "{entity}的数据迁移方案是什么?",
        "context": "{entity}迁移: 迁移工具{tool}, 增量策略{incremental}, 回滚方案{rollback}。",
    },
    {
        "question": "{entity}的变更审批流程是什么?",
        "context": "{entity}变更: 审批角色{roles}, 审批环节{steps}, 超时处理{timeout}。",
    },
    {
        "question": "{entity}在场景中的应用有哪些?",
        "context": "{entity}应用场景: {scenarios}。支持实时监控{realtime}和趋势分析{analysis}。",
    },
    {
        "question": "{entity}的告警规则怎么配置?",
        "context": "{entity}告警: 触发条件{condition}, 告警级别{level}, 通知方式{notify}。",
    },
    {
        "question": "{entity}的数据质量校验规则是什么?",
        "context": "{entity}校验: 完整性{completeness}, 一致性{consistency}, 准确性{accuracy}。",
    },
    {
        "question": "{entity}的API接口定义是什么?",
        "context": "{entity}API: RESTful接口{api_path}, 请求体{request}, 响应体{response}。",
    },
    {
        "question": "{entity}的批量导入格式是什么?",
        "context": "{entity}导入: 格式{format}, 分隔符{delimiter}, 编码{encoding}。",
    },
    {
        "question": "{entity}如何与IoT设备对接?",
        "context": "{entity}IoT对接: 协议{protocol}, 数据点{datapoints}, 上报频率{report_freq}。",
    },
    {
        "question": "{entity}的关联数据查询效率如何优化?",
        "context": "{entity}优化: 预加载{preload}, 分页{pagination}, 缓存{cache}。",
    },
    {
        "question": "{entity}的审计日志怎么查看?",
        "context": "{entity}审计: 操作记录{ops}, 操作人{operator}, 时间{time}, 变更前后的值{before_after}。",
    },
    {
        "question": "{entity}的默认值怎么设置?",
        "context": "{entity}默认值: {default_value}。未设置时使用默认值。",
    },
    {
        "question": "{entity}的枚举值有哪些?",
        "context": "{entity}枚举: {enum_values}。新增枚举需更新Schema定义。",
    },
    {
        "question": "{entity}的关联查询怎么实现?",
        "context": "{entity}关联: JOIN查询{join}, 子查询{subquery}, 结果集{result}。",
    },
]

ENTITIES = [
    "设备Twin", "传感器", "执行器", "控制器", "子系统",
    "空间区域", "楼层", "建筑", "租户", "资产",
    "告警规则", "工单", "维保计划", "能耗指标", "KPI",
    "场景模板", "界面组件", "数据流", "API接口", "用户角色",
    "权限组", "消息通知", "定时任务", "工作流", "业务逻辑",
    "数据模型", "属性定义", "关系定义", "事件类型", "指标类型"
]
TYPES = ["DigitalTwin", "Sensor", "Actuator", "Controller", "SubSystem",
         "Space", "Floor", "Building", "Tenant", "Asset"]
PARENTS = ["Entity", "Thing", "Location", "Organization", "Person"]
ATTRS = ["name", "description", "status", "createdAt", "updatedAt"]
RELS = ["locatedIn", "measuredBy", "controls", "belongs"]
ATTRS_DESC = ["名称, 描述, 状态, 创建时间, 更新时间"]
DTYPES = ["String", "Integer", "Float", "Boolean", "DateTime"]
REQUIREDs = ["true", "false", "true"]
RANGES = ["0~100", "可选", "必填"]
RELS2 = ["包含", "测量", "控制", "所属"]
CARDINALITIES = ["1:N", "1:1", "N:M"]
DIRECTIONS = ["自顶向下", "自底向上", "双向"]
SUBCLASSES = ["空调主机", "冷冻水泵", "冷却塔"]
NAMESPACEs = ["http://dt-lite.local/ontology#", "http://fiware.org/ontology#"]
PREFIXs = ["dtl", "fiware"]
LOCATIONS = ["schema.json", "ontology.ttl"]
BINDING_TARGETs = ["IoT设备", "BA系统", "SCADA系统"]
SYNC_ATTRS = ["温度", "压力", "流量", "状态"]
CONSTRAINTS = ["非空、格式校验、范围校验"]
CAN_INstantiate = ["是", "否"]
TWINs = ["设备Twin", "空间Twin"]
FIWARE_TYPES = ["Thing", "Location", "Organization", "Person", "SubSystem"]
MAPPINGS = ["属性一一映射", "转换规则"]
DTYPE_T = ["Float", "Integer", "String"]
FREQs = ["1s", "5s", "10s", "1min"]
RETENTIONs = ["7天", "30天", "90天", "1年"]
COMPRESSs = ["None", "Delta", "GZIP"]
READ_ROLES = ["admin", "operator", "viewer"]
WRITE_ROLES = ["admin", "operator"]
INHERITs = ["向下继承", "不继承"]
STATES = ["active", "inactive", "pending", "error"]
TRANSITIONS = ["active→inactive, inactive→pending, pending→active"]
SEMVERs = ["1.x.x", "2.x.x"]
CHANGELOGs = ["CHANGELOG.md"]
COMPAT = ["向后兼容", "部分兼容"]
MODEs = ["公开", "私有", "受限共享"]
SCOPEs = ["全量", "增量", "字段级"]
ACCESSs = ["RBAC", "ABAC"]
SPARQLs = ["SELECT ?s ?p ?o WHERE { ?s ?p ?o . }"]
FILTERs = ["时间范围", "状态过滤"]
ORDERs = ["时间倒序", "优先级"]
TTLS = ["300", "600", "3600"]
INVALIDATEs = ["写入失效", "定时失效"]
HIT_RATES = ["95%", "88%", "92%"]
PRIMARYs = ["主键索引"]
SECONDARYs = ["二级索引", "复合索引"]
FULLTEXTs = ["全文索引", "无"]
TOOLS = ["migration-tool"]
INCREMENTALs = ["增量迁移", "全量迁移"]
ROLLBACKs = ["支持回滚", "不支持回滚"]
ROLES = ["管理员", "审批人"]
STEPs = ["提交→审批→执行"]
TIMEOUTs = ["24h超时自动通过"]
SCENARIOS = ["实时监控", "故障诊断", "能效分析"]
REALTIMEs = ["支持"]
ANALYSISs = ["趋势分析"]
CONDITIONs = ["阈值超限", "状态变化"]
LEVELs = ["紧急", "重要", "一般"]
NOTIFYs = ["短信", "邮件", "BMS弹窗"]
COMPLETENESS = ["100%必填字段"]
CONSISTENCY = ["跨表一致性校验"]
ACCURACY = ["与源系统数据一致"]
API_PATHs = ["/api/v1/entities", "/api/v1/twins"]
REQUESTs = ["POST body JSON"]
RESPONSEs = ["200 OK + data"]
FORMATs = ["JSON", "CSV", "XML"]
DELIMITERs = [",", "|", "\\t"]
ENCODINGs = ["UTF-8", "GBK"]
PROTOCOLs = ["MQTT", "Modbus", "BACnet"]
DATAPoints = ["temperature", "pressure", "flow"]
REPORT_FREQs = ["1s", "5s", "10s"]
PRELOADs = ["预加载关联数据"]
PAGINATIONs = ["分页查询"]
CACHEs = ["Redis缓存"]
OPS = ["操作记录"]
OPERATORs = ["操作人"]
TIMEs = ["操作时间"]
BEFORE_AFTERS = ["变更前值→变更后值"]
DEFAULT_VALUES = ["null", "0", "false"]
ENUM_VALUES = ["on/off", "open/close", "normal/alarm"]
JOINs = ["LEFT JOIN"]
SUBQUERIES = ["子查询"]
RESULTs = ["关联结果集"]


def fill_ontology(i: int) -> dict:
    tpl = ONTOLOGY_TEMPLATES[i % len(ONTOLOGY_TEMPLATES)]
    entity = ENTITIES[i % len(ENTITIES)]
    related = ENTITIES[(i + 3) % len(ENTITIES)]
    q = tpl["question"].format(entity=entity, related=related)
    c = tpl["context"].format(
        entity=entity, related=related,
        type_=TYPES[i % len(TYPES)],
        parent=PARENTS[i % len(PARENTS)],
        attrs=ATTRS[i % len(ATTRS)],
        rels=RELS[i % len(RELS)],
        attrs_desc=ATTRS_DESC[i % len(ATTRS_DESC)],
        dtype=DTYPES[i % len(DTYPES)],
        required=REQUIREDs[i % len(REQUIREDs)],
        range_=RANGES[i % len(RANGES)],
        rel_type=RELS2[i % len(RELS2)],
        cardinality=CARDINALITIES[i % len(CARDINALITIES)],
        direction=DIRECTIONS[i % len(DIRECTIONS)],
        subclasses=SUBCLASSES[i % len(SUBCLASSES)],
        namespace=NAMESPACEs[i % len(NAMESPACEs)],
        prefix=PREFIXs[i % len(PREFIXs)],
        location=LOCATIONS[i % len(LOCATIONS)],
        binding_target=BINDING_TARGETs[i % len(BINDING_TARGETs)],
        sync_attrs=SYNC_ATTRS[i % len(SYNC_ATTRS)],
        constraints=CONSTRAINTS[i % len(CONSTRAINTS)],
        can_instantiate=CAN_INstantiate[i % len(CAN_INstantiate)],
        Twin=TWINs[i % len(TWINs)],
        fiware_type=FIWARE_TYPES[i % len(FIWARE_TYPES)],
        mapping=MAPPINGS[i % len(MAPPINGS)],
        dtype2=DTYPE_T[i % len(DTYPE_T)],
        freq=FREQs[i % len(FREQs)],
        retention=RETENTIONs[i % len(RETENTIONs)],
        compress=COMPRESSs[i % len(COMPRESSs)],
        read_roles=READ_ROLES[i % len(READ_ROLES)],
        write_roles=WRITE_ROLES[i % len(WRITE_ROLES)],
        inherit=INHERITs[i % len(INHERITs)],
        states=STATES[i % len(STATES)],
        transitions=TRANSITIONS[i % len(TRANSITIONS)],
        semver=SEMVERs[i % len(SEMVERs)],
        changelog=CHANGELOGs[0],
        compat=COMPAT[i % len(COMPAT)],
        mode=MODEs[i % len(MODEs)],
        scope=SCOPEs[i % len(SCOPEs)],
        access=ACCESSs[i % len(ACCESSs)],
        sparql=SPARQLs[0],
        filter=FILTERs[i % len(FILTERs)],
        order=ORDERs[i % len(ORDERs)],
        ttl=TTLS[i % len(TTLS)],
        invalidate=INVALIDATEs[i % len(INVALIDATEs)],
        hit_rate=HIT_RATES[i % len(HIT_RATES)],
        primary=PRIMARYs[0],
        secondary=SECONDARYs[i % len(SECONDARYs)],
        fulltext=FULLTEXTs[i % len(FULLTEXTs)],
        tool=TOOLS[0],
        incremental=INCREMENTALs[i % len(INCREMENTALs)],
        rollback=ROLLBACKs[i % len(ROLLBACKs)],
        roles=ROLES[i % len(ROLES)],
        steps=STEPs[i % len(STEPs)],
        timeout=TIMEOUTs[i % len(TIMEOUTs)],
        scenarios=SCENARIOS[i % len(SCENARIOS)],
        realtime=REALTIMEs[i % len(REALTIMEs)],
        analysis=ANALYSISs[i % len(ANALYSISs)],
        condition=CONDITIONs[i % len(CONDITIONs)],
        level=LEVELs[i % len(LEVELs)],
        notify=NOTIFYs[i % len(NOTIFYs)],
        completeness=COMPLETENESS[0],
        consistency=CONSISTENCY[0],
        accuracy=ACCURACY[0],
        api_path=API_PATHs[i % len(API_PATHs)],
        request=REQUESTs[0],
        response=RESPONSEs[0],
        format_f=FORMATs[i % len(FORMATs)],
        delimiter=DELIMITERs[i % len(DELIMITERs)],
        encoding=ENCODINGs[i % len(ENCODINGs)],
        protocol=PROTOCOLs[i % len(PROTOCOLs)],
        datapoints=DATAPoints[i % len(DATAPoints)],
        report_freq=REPORT_FREQs[i % len(REPORT_FREQs)],
        preload=PRELOADs[0],
        pagination=PAGINATIONs[0],
        cache=CACHEs[0],
        ops=OPS[0],
        operator=OPERATORs[0],
        time=TIMEs[0],
        before_after=BEFORE_AFTERS[0],
        default_value=DEFAULT_VALUES[i % len(DEFAULT_VALUES)],
        enum_values=ENUM_VALUES[i % len(ENUM_VALUES)],
        join=JOINs[0],
        subquery=SUBQUERIES[0],
        result=RESULTs[0],
    )
    return {
        "question": q,
        "answer": f"ontology_doc_{i:04d}",
        "context": c,
        "kb_id": "ontology",
    }


# ── Generate all 500 records ─────────────────────────────────────────
records = []

# 200 maintenance
for i in range(200):
    records.append(fill_maintenance(i))

# 100 alarm
for i in range(100):
    records.append(fill_alarm(i))

# 100 asset info
for i in range(100):
    records.append(fill_asset(i))

# 50 energy
for i in range(50):
    records.append(fill_energy(i))

# 50 ontology
for i in range(50):
    records.append(fill_ontology(i))

assert len(records) == 500, f"Expected 500, got {len(records)}"

# Write to JSONL
out_path = Path(__file__).parent.parent / "tests" / "ai" / "rag_eval_dataset.jsonl"
out_path.parent.mkdir(parents=True, exist_ok=True)
with out_path.open("w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Generated {len(records)} records to {out_path}")
print(f"  maintenance: {sum(1 for r in records if r['kb_id'] == 'maintenance')}")
print(f"  alarm: {sum(1 for r in records if r['kb_id'] == 'alarm')}")
print(f"  asset_info: {sum(1 for r in records if r['kb_id'] == 'asset_info')}")
print(f"  energy: {sum(1 for r in records if r['kb_id'] == 'energy')}")
print(f"  ontology: {sum(1 for r in records if r['kb_id'] == 'ontology')}")
