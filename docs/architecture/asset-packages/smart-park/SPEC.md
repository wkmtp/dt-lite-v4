# DT-Lite V4.0 Smart Park Industry Asset Package Specification v1.0

**版本**: v1.0 | **状态**: 评审基线 | **适用平台**: DT-Lite Core v4.18.0+ | **编制角色**: dt_manager

---

## 1. 总体设计原则

### 1.1 零代码配置化架构 (Schema + Template + Plugin)

```
┌─────────────────────────────────────────────────────────────┐
│                    Industry Asset Package                    │
├─────────────────────────────────────────────────────────────┤
│  L5 Operations  │ 运维包: 告警规则库(200+)、SOP手册(105+)、   │
│                 │ 巡检计划、应急预案、能耗基准、KPI看板        │
├─────────────────────────────────────────────────────────────┤
│  L4 Application │ 场景应用包: 15大场景模板、低代码页面、      │
│                 │ 组件库、仪表盘、报表模板、移动端小程序        │
├─────────────────────────────────────────────────────────────┤
│  L3 Template    │ 模板包: 资产模板、空间模板、场景模板、      │
│                 │ 工单模板、报表模板、大屏模板                 │
├─────────────────────────────────────────────────────────────┤
│  L2 Capability  │ 能力包: 30+标准能力、协议适配器映射、       │
│                 │ 计算规则、联动规则、告警策略模板             │
├─────────────────────────────────────────────────────────────┤
│  L1 Ontology    │ 本体包: 50+资产类型、属性定义、关系拓扑、   │
│                 │ 空间层级、分类体系、枚举字典                 │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 多场景覆盖矩阵 (7大场景 × 5层架构)

| 场景分类 | 核心资产类型数 | 专有能力数 | 场景模板数 | 告警规则数 | SOP数量 | 部署时长 |
|---------|--------------|-----------|-----------|-----------|--------|---------|
| **智慧社区** | 12 | 5 | 3 | 35 | 18 | ≤45 min |
| **智慧商场** | 15 | 6 | 3 | 42 | 22 | ≤60 min |
| **智慧学校** | 10 | 4 | 2 | 28 | 15 | ≤30 min |
| **智慧医院** | 14 | 7 | 3 | 48 | 25 | ≤90 min |
| **智慧物流** | 11 | 5 | 2 | 32 | 16 | ≤45 min |
| **数据中心** | 9 | 6 | 1 | 40 | 20 | ≤60 min |
| **产业园区** | 18 | 8 | 4 | 55 | 28 | ≤120 min |
| **通用基座** | 8 | 3 | 2 | 20 | 10 | ≤15 min |

---

## 2. L1 Ontology Layer — 本体包规格

### 2.1 空间层级标准 (全场景通用)

```
Space Hierarchy (4-5 levels):
└── Park/Campus (园区/校区)
    ├── Zone/District (分区/片区) — 社区:期数、商场:楼层、医院:院区、物流:作业区
    ├── Building (单体建筑) — 住宅楼、商场主楼、教学楼、病房楼、仓库、机房、厂房
    │   ├── Floor (楼层)
    │   │   ├── Zone/Room (区域/房间) — 户型、铺位、教室、病房、货位、机柜列、车间
    │   │   └── Corridor/PublicArea (公共区域) — 走廊、大堂、走道、过道
    │   └── EquipmentRoom (设备用房) — 强电间、弱电间、水泵房、热交换站、配电房、UPS室
    └── OutdoorArea (室外区域) — 广场、停车场、绿地、装卸区、冷却塔区、物流园路网
```

### 2.2 资产分类体系 (7大专业域 × 50+资产类型)

#### 2.2.1 通用基座域 (8类) — 所有场景必装

| 资产类型代码 | 中文名称 | 核心属性 | 关键关系 | 适用场景 |
|-------------|---------|---------|---------|---------|
| `asset.power.transformer` | 变压器 | 额定容量、电压等级、运行状态、油温、负载率 | feeds→`asset.power.lv_cabinet` | 全场景 |
| `asset.power.lv_cabinet` | 低压配电柜 | 额定电流、回路数、开关状态、三相电流/电压 | contains→`asset.power.meter` | 全场景 |
| `asset.power.meter` | 智能电表 | 表号、倍率、正/反向电量、需量、功率因数 | measures→`asset.*` | 全场景 |
| `asset.water.meter` | 智能水表 | 表号、口径、累计流量、瞬时流量、压力 | measures→`asset.*` | 全场景 |
| `asset.env.sensor` | 环境传感器 | 温度、湿度、PM2.5、CO2、VOC、噪声 | monitors→`space.*` | 全场景 |
| `asset.security.camera` | 监控摄像头 | 分辨率、编码、PTZ、存储位置、AI算法包 | monitors→`space.*` | 全场景 |
| `asset.security.access` | 门禁控制器 | 门数、读头类型、权限组、开门记录 | controls→`space.door` | 全场景 |
| `asset.network.switch` | 网络交换机 | 端口数、POE、VLAN、堆叠、CPU/内存 | connects→`asset.*` | 全场景 |

#### 2.2.2 智慧社区专有 (12类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 |
|-------------|---------|---------|---------|
| `asset.community.elevator` | 电梯 | 品牌、载重、速度、层站数、故障码、年检到期日 | vertical_transport, mandatory_inspection |
| `asset.community.parking_gate` | 道闸/车位锁 | 类型(道闸/地锁/视频识别)、车位编号、状态 | parking_management |
| `asset.community.charging_pile` | 充电桩 | 功率、枪数、计费模式、枪状态、充电记录 | ev_charging, energy_service |
| `asset.community.smart_lock` | 智能门锁 | 开锁方式(指纹/密码/卡/蓝牙/人脸)、电量、临时密码 | access_control, resident_service |
| `asset.community.intercom` | 可视对讲 | 户号、解锁联动、呼叫记录、视频流地址 | access_control, resident_service |
| `asset.community.water_pump` | 供水泵/增压泵 | 功率、扬程、流量、变频器状态、压力设定值 | water_supply |
| `asset.community.sewage_pump` | 污水提升泵 | 功率、液位、运行模式、故障记录 | drainage |
| `asset.community.fire_hydrant` | 消火栓/喷淋 | 压力、阀门状态、巡检记录、年检日期 | fire_safety, mandatory_inspection |
| `asset.community.gas_meter` | 燃气表/报警器 | 剩余气量、阀门状态、报警浓度、NB信号强度 | gas_safety, mandatory_inspection |
| `asset.community.parcel_locker` | 智能快递柜 | 格口数、占用率、取件码、超时费规则 | last_mile_logistics |
| `asset.community.lighting_pole` | 智慧灯杆 | 灯具功率、调光策略、挂载设备(5G/环境/充电)、单灯控制器 | smart_lighting, multi_function_pole |
| `asset.community.waste_bin` | 智能垃圾桶/分类投放点 | 分类类型、满溢感应、投放积分、清运记录 | waste_management, carbon_credit |

#### 2.2.3 智慧商场专有 (15类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 |
|-------------|---------|---------|---------|
| `asset.mall.ahu` | 空调机组(AHU/MAU) | 送/回风温湿度、CO2、新风比、滤网压差、变频器 | hvac, energy_major |
| `asset.mall.chiller` | 冷水机组 | 冷量、COP、进出水温、压力、油压、运行工况 | hvac, energy_major |
| `asset.mall.cooling_tower` | 冷却塔 | 风机变频、水温、水位、补水阀、风机振动 | hvac, energy_major |
| `asset.mall.fcu` | 风机盘管/空调箱 | 回风温度、阀门开度、风速、冷凝水泵 | hvac, terminal_unit |
| `asset.mall.lighting_zone` | 照明回路/区控 | 回路功率、调光等级、场景模式、人感/光感联动 | lighting, energy_saving |
| `asset.mall.escalator` | 扶梯/自动人行道 | 运行方向、速度、人流计数、故障码、年检 | vertical_transport, mandatory_inspection |
| `asset.mall.elevator` | 客梯/货梯 | 并联群控、层站、载重、VIP专梯、故障联动 | vertical_transport, mandatory_inspection |
| `asset.mall.parking_guidance` | 车位引导/反向寻车 | 超声波/视频检测、车位状态、引导屏联动 | parking_management |
| `asset.mall.people_counter` | 客流计数器 | 进/出/滞留人数、热力图、转化率、区域画像 | retail_analytics |
| `asset.mall.pos_gateway` | POS/收银网关 | 交易笔数、金额、支付方式分布、离线缓存 | retail_analytics |
| `asset.mall.digital_signage` | 数字标牌/导视屏 | 分辨率、播放列表、远程发布、亮度自适应 | marketing, wayfinding |
| `asset.mall.fire_shutter` | 防火卷帘/挡烟垂壁 | 位置状态、联动触发、手动/自动、年检 | fire_safety, mandatory_inspection |
| `asset.mall.sprinkler_pump` | 消防泵/稳压泵 | 压力、巡检启动、故障、电气参数 | fire_safety, mandatory_inspection |
| `asset.mall.fresh_air` | 新风机/全热交换器 | PM2.5过滤效率、热回收率、风量、滤网寿命 | iaq, health |
| `asset.mall.toilet_sensor` | 智慧厕所传感器 | 氨气/H2S、人数、纸巾/皂液余量、清洁提醒 | sanitation, experience |

#### 2.2.4 智慧学校专有 (10类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 |
|-------------|---------|---------|---------|
| `asset.school.classroom_env` | 教室环境监测仪 | CO2、PM2.5、甲醛、照度、噪声、温湿度 | iaq, health, exam_mode |
| `asset.school.smart_blackboard` | 智能黑板/交互平板 | 触控点数、投屏协议、课件同步、录播联动 | teaching, digital_campus |
| `asset.school.attendance_gate` | 考勤闸机/人脸核验 | 通行模式、陌生人报警、尾随检测、考勤推送 | security, attendance |
| `asset.school.lab_fume_hood` | 通风柜/实验室排风 | 面风速、排风量、阀门开度、报警联动 | lab_safety, mandatory_inspection |
| `asset.school.lab_gas_valve` | 实验室燃气/气体阀门 | 电磁阀状态、泄漏报警、紧急切断、定时关闭 | lab_safety, mandatory_inspection |
| `asset.school.dorm_access` | 宿舍门禁/刷脸机 | 晚归报警、陪读管控、访客预约、断网联动 | dormitory_management |
| `asset.school.canteen_equip` | 食堂设备(蒸柜/消毒柜/留样柜) | 温度记录、运行时长、消毒合格、留样48h | food_safety, mandatory_inspection |
| `asset.school.sports_venue` | 体育馆/泳池设备 | 水质(余氯/ph/浊度)、温湿度、照明场景、预约联动 | venue_management |
| `asset.school.library_climate` | 图书馆/档案室恒温恒湿 | 温湿度精度±1℃/±3%、气体灭火、门禁联动 | asset_preservation |
| `asset.school.bus_tracker` | 校车定位/学生上下车 | GPS轨迹、刷卡上下车、围栏报警、家长推送 | transport_safety |

#### 2.2.5 智慧医院专有 (14类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 | 合规标准 |
|-------------|---------|---------|---------|---------|
| `asset.hospital.icu_monitor` | ICU中心监护/床旁监护 | 多参数(ECG/SpO2/NIBP/IBP/CO2/体温)、波形、报警分级 | critical_care, life_support | YY/T 0784 |
| `asset.hospital.anesthesia_machine` | 麻醉机/呼吸机 | 潮气量、呼吸频率、麻醉气体浓度、气道压力、废气排放 | OR, life_support | YY 0600 |
| `asset.hospital.imaging_equip` | 影像设备(CT/MR/DR/超声/DSA) | 扫描参数、剂量(DLP/CTDI)、QC结果、维保状态 | radiology, radiation_safety | GBZ 130 |
| `asset.hospital.lab_analyzer` | 生化/免疫/血液/PCR分析仪 | 样本量、试剂余量、质控规则、校准周期、LIS接口 | lab, ivd | ISO 15189 |
| `asset.hospital.pharmacy_robot` | 智能药房/发药机器人 | 处方核对、药品追溯、有效期管理、冷链监测 | pharmacy, medication_safety | GSP |
| `asset.hospital.blood_bank` | 血库/血液冰箱/解冻箱 | 温度-30~-60℃/2~6℃、报警分级、出入库血袋追溯 | blood_management, life_support | WS 352 |
| `asset.hospital.ot_lighting` | 无影灯/手术室净化 | 照度10-16万lx、色温、层流等级(百级/千级)、压差 | OR, infection_control | GB 50333 |
| `asset.hospital.waste_medical` | 医疗废物暂存/转运秤 | 重量、分类(锐器/感染/病理/化学/损伤)、电子联单、GPS追踪 | waste_medical, regulatory | GB 19218 |
| `asset.hospital.oxygen_system` | 医用氧气/气体管道站 | 压力、流量、露点、一氧化碳、切换记录、备用瓶组 | medical_gas, life_support | YY/T 0298 |
| `asset.hospital.nurse_call` | 护士呼叫/床头分机 | 呼叫等级(普通/急救/卫生)、定位、响应时长、录音 | nursing, patient_experience | — |
| `asset.hospital.asset_tracker` | 医疗资产定位标签(UWB/蓝牙) | 资产绑定、区域围栏、轨迹回放、盘点加速 | asset_management, rtls | — |
| `asset.hospital.patient_wristband` | 患者腕带/母婴防盗 | 一维/二维码、RFID/UWB、防拆报警、身份核验 | patient_safety, identification | — |
| `asset.hospital.clean_robot` | 消毒机器人/紫外线/过氧化氢 | 路径规划、消毒剂余量、作业日志、人机共存避障 | infection_control, automation | — |
| `asset.hospital.ward_tv` | 病床交互终端/床旁屏 | 住院服务、医嘱查询、健康教育、护士呼叫集成 | patient_experience, smart_ward | — |

#### 2.2.6 智慧物流专有 (11类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 |
|-------------|---------|---------|---------|
| `asset.logistics.sorter` | 分拣机/交叉带/滑块 | 分拣能力(件/小时)、目的地编码、阻塞检测、包裹追踪 | sorting, throughput_core |
| `asset.logistics.conveyor` | 输送线/伸缩机/提升机 | 速度、张力、皮带跑偏、堆积检测、急停状态 | conveying, throughput_core |
| `asset.logistics.agv_amr` | AGV/AMR/叉车机器人 | 导航方式(SLAM/磁条/二维码)、电量、任务队列、避障、充电桩 | automation, flexible_logistics |
| `asset.logistics.asrs` | 立库/堆垛机/穿梭车/四向车 | 货位坐标、存取策略、库存准确率、高度/载重限制 | storage, high_density |
| `asset.logistics.dock_leveler` | 装卸平台/翻板/登车桥 | 高度调节、唇板状态、车辆锁定、安全联锁 | dock_management |
| `asset.logistics.dim_ws` | 体积测量/称重/扫码一体机 | 长宽高精度±5mm、重量精度±50g、条码识别率、吞吐率 | dimensioning, billing_basis |
| `asset.logistics.parcel_locker` | 丰巢/驿站/末端柜 | 格口规格、占用率、超时费、取件码、异常件处理 | last_mile |
| `asset.logistics.cold_chain` | 冷链箱/冷藏车/温湿度记录仪 | 温度范围(-25~+25℃)、GPS轨迹、开门记录、报警上传 | cold_chain, gsp_compliance |
| `asset.logistics.forklift` | 电动叉车/前移式/拣选车 | 载重、起升高度、电池/燃料、维保、驾驶员授权 | material_handling |
| `asset.logistics.pack_station` | 打包台/封箱机/贴单机 | 耗材余量、打包规则、效率统计、异常复核 | packing, outbound |
| `asset.logistics.yard_mgmt` | 场区管理/车辆调度/智能闸口 | 车位分配、排队叫号、进出场凭证、作业时长 | yard_management |

#### 2.2.7 数据中心专有 (9类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 | 合规标准 |
|-------------|---------|---------|---------|---------|
| `asset.dc.pdu` | 智能PDU/母线槽 | 分支电流/功率/能量、开关控制、环境监测、级联 | power_distribution, pue_core | GB 50174 |
| `asset.dc.ups` | UPS/电池组/电池监测 | 负载率、电池健康度(SOH)、备份时间、放电记录 | power_backup, availability | GB 50174 |
| `asset.dc.genset` | 柴油发电机/并机柜 | 功率、油位/油压/水温、自启动、切换时长、周期试运行 | power_backup, availability | GB 50174 |
| `asset.dc.precision_ac` | 精密空调/列间/行级/冷板 | 送回风温湿度、制冷量、湿度控制、EC风机、冷凝器 | cooling, pue_core | GB 50174 |
| `asset.dc.rack` | 机柜/微模块/冷热通道 | U位资产、功率密度(kW/柜)、门禁、漏水、资产自动发现 | space, capacity_planning | GB 50174 |
| `asset.dc.liquid_cooling` | 液冷CDU/冷板/歧管/检漏 | 冷却液流量/温度/压力、泄漏检测、水质电导率、冗余度 | liquid_cooling, hpc | 新标准 |
| `asset.dc.bms_dcim` | BMS/DCIM网关/采集器 | 协议适配(Modbus/BACnet/SNMP/OPC-UA)、数据质量、时序写入 | monitoring, integration | — |
| `asset.dc.fire_gas` | 气体灭火/七氟丙烷/IG541 | 压力、喷放联动、声光报警、手动/自动、年检 | fire_safety, mandatory | GB 50370 |
| `asset.dc.fiber_management` | 光缆/ODF/熔纤盘/端面检测 | 光路拓扑、损耗、端面洁净度、容量规划、故障定位 | network, capacity_planning | — |

#### 2.2.8 产业园区专有 (18类)

| 资产类型代码 | 中文名称 | 核心属性 | 业务标签 |
|-------------|---------|---------|---------|
| `asset.park.steam_boiler` | 蒸汽锅炉/余热锅炉 | 蒸汽压力/温度/流量、燃料消耗、NOx排放、水位、安检证 | energy_supply, mandatory_inspection |
| `asset.park.heat_exchanger` | 换热站/板换/管换 | 供回水温/压、换热功率、流量、结垢指数、一次/二侧 | heating, energy_supply |
| `asset.park.compressor` | 空压机/离心/螺杆/无油 | 排气压力/温度/流量、功率、露点、油位、卸载比 | compressed_air, energy_major |
| `asset.park.chiller_plant` | 中央冷站/多机组优化 | 总冷量、COP优化、冷冻/冷却水泵群控、冷却塔群控 | cooling_plant, energy_major |
| `asset.park.water_treatment` | 软水/纯水/RO/EDI/污水处理 | 进出水水质(电导率/硬度/TOC/COD)、药剂投加、膜通量 | water_treatment, process_water |
| `asset.park.gas_station` | 天然气门站/调压箱/CNG/LNG | 入口/出口压力、流量、温度、加臭量、切断阀联动 | gas_supply, safety_critical |
| `asset.park.etp_wtp` | 废水/废气/固废处理站 | 在线监测(pH/COD/氨氮/总氮/TVOC/颗粒物)、达标排放、台账 | environmental, regulatory |
| `asset.park.cems` | 烟气连续监测(CEMS) | SO2/NOx/粉尘/O2/流速/温湿度/湿度、折算排放、超标报警 | environmental, regulatory |
| `asset.park.vocs_monitor` | VOCs在线监测/泄漏检测(LDAR) | 总烃/非甲烷总烃/苯系物、组分谱、浓度报警、修复追踪 | environmental, regulatory |
| `asset.park.bridge_crane` | 行车/龙门吊/港口起重机 | 起重量、幅度、高度、防碰撞、防摇摆、黑匣子、年检 | lifting, mandatory_inspection |
| `asset.park.conveyor_belt` | 长距离皮带/管状带/斗提机 | 张力、跑偏、撕裂检测、堵煤/堵料、驱动功率、清扫器 | bulk_material_handling |
| `asset.park.weighbridge` | 地磅/汽车衡/轴重秤 | 最大秤量、分度值、去皮/毛重/净重、防作弊、计量检定 | weighing, trade_settlement |
| `asset.park.dust_suppression` | 雾炮/喷淋/干雾抑尘/雾桩 | 覆盖半径、颗粒物浓度联动、用水量、防冻、远程控制 | environmental, dust_control |
| `asset.park.perimeter_security` | 周界入侵/光缆/微波/张力/振动光缆 | 报警区域、灵敏度、视频联动、误报抑制、防破坏 | security, perimeter |
| `asset.park.vehicle_scale` | 无人值守地磅/智能道闸/车牌识别 | 自动过磅、红绿灯联动、语音播报、异常抓拍、黑白名单 | logistics_gate, automation |
| `asset.park.energy_gateway` | 能源管理网关/分户计量/碳计量 | 多能流(水电气蒸汽)、分项计量、碳排放因子、能耗限额 | energy_management, carbon |
| `asset.park.env_monitor_station` | 园区环境/气象/噪声/恶臭站 | 气象五参数、PM2.5/10、恶臭(OuE)、噪声分贝、网格化 | environmental, compliance |
| `asset.park.smart_pole` | 多功能智慧杆(5G/充电/环境/屏/灯/安防) | 挂载清单、供电冗余、杆体倾斜、地基沉降、统一运维 | multi_function, infrastructure |

### 2.3 属性定义规范 (Property Definitions)

每个资产类型定义 15-30 个标准属性，分类为：

- **身份属性** (5个): `asset_id`, `name`, `model`, `manufacturer`, `serial_number`, `install_date`, `warranty_expiry`, `location_id`, `space_id`, `status`
- **运行属性** (8-15个): 遵循量纲标准，单位统一为 SI/工程单位，含 `value`, `quality`, `timestamp`, `unit`
- **配置属性** (3-8个): 阈值、参数、策略、模式
- **维保属性** (4个): `last_maintenance`, `next_maintenance`, `maintenance_cycle`, `vendor_contact`
- **合规属性** (2-4个): `inspection_due`, `certificate_no`, `regulatory_code`, `compliance_status`

### 2.4 关系拓扑标准 (Relationship Types)

| 关系类型 | 语义 | 反向关系 | 典型用例 |
|---------|------|---------|---------|
| `contains` | 空间包含 | `located_in` | Building→Floor, Floor→Room |
| `feeds` | 能源/介质供给 | `fed_by` | Transformer→LV Cabinet, Chiller→AHU |
| `controls` | 控制关系 | `controlled_by` | BMS→AHU, Access Controller→Door |
| `monitors` | 监测关系 | `monitored_by` | Sensor→Room, Camera→Zone |
| `connects` | 网络/通信连接 | `connected_to` | Switch→Camera, Gateway→Meter |
| `aggregates` | 数据聚合 | `part_of` | Zone Meter→Building Meter |
| `depends_on` | 业务依赖 | `required_by` | Chiller→Cooling Tower, UPS→Battery |

---

## 3. L2 Capability Layer — 能力包规格

### 3.1 30+ 标准能力定义 (Capability Definitions)

#### 3.1.1 通用基础能力 (8个)

| 能力代码 | 能力名称 | 核心接口 | 适配器要求 | 适用资产 |
|---------|---------|---------|-----------|---------|
| `cap.telemetry.read` | 实时遥测读取 | `read_telemetry(asset_ids, points)` | 所有协议适配器 | 全资产 |
| `cap.telemetry.write` | 遥信/遥控下发 | `write_telemetry(asset_id, point, value)` | Modbus/BACnet/OPC-UA/MQTT | 可控资产 |
| `cap.telemetry.subscribe` | 订阅/推送 | `subscribe(asset_ids, points, callback)` | MQTT/OPC-UA/BACnet COV | 实时性要求高 |
| `cap.asset.discover` | 设备发现/拓扑同步 | `discover(gateway_id)` | BACnet Who-Is, Modbus Scan, MQTT Discovery, OPC-UA Browse | 网关/采集器 |
| `cap.asset.provision` | 资产注册/入网 | `provision(device_info)` | 所有适配器 | 新增设备 |
| `cap.firmware.ota` | 固件升级/OTA | `ota_update(device_id, firmware_url, verify_hash)` | MQTT/HTTP/CoAP | 智能终端 |
| `cap.alarm.evaluate` | 告警规则评估 | `evaluate(asset_id, rules)` | 规则引擎(CEP) | 全资产 |
| `cap.kpi.compute` | KPI/指标计算 | `compute(asset_id, formula, window)` | TimescaleDB Continuous Aggregate | 计量/能耗资产 |

#### 3.1.2 楼宇能效能力 (6个)

| 能力代码 | 能力名称 | 核心算法 | 适用场景 |
|---------|---------|---------|---------|
| `cap.hvac.cooling_optimize` | 冷站群控优化 | 模型预测控制(MPC)、冷水机组最优组合、冷却塔风机变频 | 商场、医院、数据中心、产业园区 |
| `cap.hvac.ahu_optimize` | AHU新风/回风优化 | CO2需求控制通风(DCV)、焓值判断、供风温度复位 | 商场、医院、学校 |
| `cap.lighting.daylight_harvest` | 采光采集/恒照度 | 光感联动、时段场景、人感延时 | 商场、学校、社区、园区 |
| `cap.energy.demand_response` | 需求侧响应 | 负荷预测、可调资源识别、响应策略、补偿结算 | 全场景(有动力电) |
| `cap.energy.carbon_accounting` | 碳核算/碳资产 | 范围1/2/3排放因子、碳配额、CCER核算、碳交易接口 | 产业园区、数据中心、大型商业 |
| `cap.equipment.health_index` | 设备健康度指数 | 振动/温度/电流谱分析、剩余寿命预测(RUL)、维修优先级 | 旋转设备、关键资产 |

#### 3.1.3 专业场景能力 (16个)

| 能力代码 | 能力名称 | 核心价值 | 适用场景 |
|---------|---------|---------|---------|
| `cap.elevator.group_control` | 电梯群控/召唤优化 | 平均等待时间↓30%、能耗↓15% | 社区、商场、医院、学校、园区 |
| `cap.parking.guidance` | 车位引导/反向寻车 | 车位周转率↑20%、找车时间↓60% | 社区、商场、医院、园区 |
| `cap.retail.footfall_analytics` | 客流热力/转化率/画像 | 铺位租金定价、营销效果、动线优化 | 商场 |
| `cap.retail.energy_benchmark` | 单耗对标/能效分级 | 同业对标、能效等级、改造ROI测算 | 商场、酒店、写字楼 |
| `cap.school.iaq_guardian` | 教室空气卫士 | CO2>1000ppm自动新风、考试模式静音、家长公开 | 学校 |
| `cap.school.attendance_safe` | 考勤安全闭环 | 入校/离校/课堂/宿舍全链路、异常即时预警 | 学校 |
| `cap.hospital.asset_tracking` | 医疗资产全生命周期 | 利用率↑40%、寻找时间↓80%、合规台账 | 医院 |
| `cap.hospital.critical_env` | 关键环境合规(手术室/ICU/药库) | 温湿度/压差/洁净度/气体 24/7 合规报告 | 医院 |
| `cap.hospital.med_safety` | 用药安全闭环 | 处方审核→调配核对→发药验证→用药记录 全链路 | 医院 |
| `cap.logistics.sorting_optimize` | 分拣路由优化/平衡 | 分拣效率↑25%、错分率↓90%、高峰削峰 | 物流 |
| `cap.logistics.cold_chain_guard` | 全程冷链监管/电子联单 | 温度零断点、合规电子联单、保险理赔直连 | 物流、医药、生鲜 |
| `cap.logistics.yard_scheduling` | 场区车辆智能调度 | 车辆周转↑30%、等待↓50%、装卸并行 | 物流、园区 |
| `cap.dc.pue_optimize` | PUE极致优化/液冷就绪 | PUE↓1.15、液冷占比规划、热回收 | 数据中心 |
| `cap.dc.capacity_planning` | 容量规划/功率密度预测 | U位/功率/制冷/网络四维容量、扩容触发 | 数据中心 |
| `cap.park.multi_energy_synergy` | 多能互补/源网荷储协同 | 电/热/冷/气/氢协同、储能套利、虚拟电厂接入 | 产业园区 |
| `cap.park.env_compliance` | 环保合规/排污许可/碳核算 | 自动填报、超标预警、台账留痕、一键生成报表 | 产业园区 |

### 3.2 协议适配器映射矩阵 (Adapter Mapping)

| 能力 | BACnet | Modbus | MQTT | OPC-UA | 备注 |
|------|--------|--------|------|--------|------|
| `cap.telemetry.read` | ReadProperty | FC 03/04 | Subscribe | ReadValue | 基础 |
| `cap.telemetry.write` | WriteProperty | FC 06/16 | Publish | WriteValue | 可控 |
| `cap.telemetry.subscribe` | COV Subscription | — | QoS 1/2 | MonitoredItems | 实时推送 |
| `cap.asset.discover` | Who-Is/I-Am | Scan 1-247 | Topic Discovery | Browse Namespace | 入网 |
| `cap.firmware.ota` | — | — | OTA Topic | — | 仅IP设备 |
| `cap.alarm.evaluate` | Intrinsic/Algorithmic | Threshold | Rule Engine | Condition | 统一规则引擎 |

### 3.3 计算规则与联动规则模板

- **计算规则**: 60+ 预置公式 (COP、PUE、单耗、碳排放、设备健康度、客流转化率等)
- **联动规则**: 40+ 标准场景 (火警联动、设备互锁、需量控制、场景切换、应急启停)
- **告警策略模板**: 分级分类 (紧急/重要/一般/提示)、抑制策略 (抑制窗口、依赖抑制、风暴抑制)、升级路由 (值班表、升级矩阵、多渠道推送)

---

## 4. L3 Template Layer — 模板包规格

### 4.1 资产模板 (Asset Templates) — 50+ 个

每个资产类型对应 1 个标准模板，包含：
- 完整属性定义 (含默认值、单位、校验规则)
- 标准能力绑定清单
- 标准告警规则引用
- 标准维保计划引用
- 3D 模型引用 (GLTF/USDZ, LOD0-LOD2)
- 图标/符号库引用 (SVG, 语义化命名)

### 4.2 空间模板 (Space Templates) — 20+ 个

| 模板代码 | 名称 | 空间层级 | 典型资产绑定 | 适用场景 |
|---------|------|---------|-------------|---------|
| `tmpl.space.residential_building` | 住宅楼模板 | Building→Floor→Unit/Room | 电梯、门禁、对讲、供水、消防、充电桩 | 社区 |
| `tmpl.space.mall_anchor` | 商场主力店/楼层模板 | Building→Floor→Zone/Shop | AHU、扶梯、客流、照明、消防、标牌 | 商场 |
| `tmpl.space.school_teaching` | 教学楼模板 | Building→Floor→Classroom/Lab | 环境监测、智能黑板、考勤、通风柜、燃气阀 | 学校 |
| `tmpl.space.hospital_ward` | 病房楼模板 | Building→Floor→Ward/Bed | 护士呼叫、床旁监护、交互终端、医用气体 | 医院 |
| `tmpl.space.hospital_or` | 手术部模板 | Building→Floor→OR/Prep/Recovery | 无影灯、净化、麻醉机、气体、术中影像 | 医院 |
| `tmpl.space.logistics_warehouse` | 标准仓库模板 | Building→Zone→Location/Rack | 立库、输送、AGV、体积秤、装卸平台 | 物流 |
| `tmpl.space.logistics_sorting` | 分拣中心模板 | Building→Line→Sorter/Chute | 分拣机、输送、扫码称重、包裹追踪 | 物流 |
| `tmpl.space.dc_hall` | 机房/数据大厅模板 | Building→Row→Rack/Row | PDU、UPS、精密空调、机柜、液冷、消防 | 数据中心 |
| `tmpl.space.park_production` | 生产厂房模板 | Building→Bay→Line/Cell | 锅炉、压缩空气、冷站、水处理、行车、除尘 | 产业园区 |
| `tmpl.space.park_utility` | 动力站/公用工程模板 | Building→Room→Equipment | 锅炉、冷站、压缩空气、水处理、气站、环保 | 产业园区 |

### 4.3 场景模板 (Scene Templates) — 15 个核心场景

| 场景代码 | 场景名称 | 包含视图 | 核心指标 | 适用场景 |
|---------|---------|---------|---------|---------|
| `scene.energy_cockpit` | 能碳管理驾驶舱 | 实时功率、能耗趋势、单耗对标、碳排放、需量响应、设备能效 | 综合能耗强度、单位面积耗电、PUE、碳排放总量 | 全场景 |
| `scene.operation_center` | 运营指挥中心 | 资产总览、告警风暴、工单看板、巡检进度、SLA达成、应急状态 | 资产在线率、告警收敛率、工单及时率、MTTR | 全场景 |
| `scene.community_life` | 社区生活服务 | 访客预约、缴费报修、充电桩、快递柜、公共设施预约、社区公告 | 住户满意度、报修响应、设施利用率 | 社区 |
| `scene.mall_retail` | 商场零售运营 | 客流热力、销售转化、租金收缴、商户画像、营销活动、能耗分摊 | 坪效、进店率、客单价、能耗分摊准确率 | 商场 |
| `scene.mall_parking` | 商场停车运营 | 车位引导、反向寻车、收费规则、月租管理、新能源充电 | 车位周转率、高峰通行时间、充电桩利用率 | 商场 |
| `scene.school_smart` | 智慧校园大脑 | 校园一张图、师生考勤、环境监测、安防预警、食安溯源、资产台账 | 考勤率、空气合格率、安防零事故、食安零投诉 | 学校 |
| `scene.hospital_clinical` | 临床运营管理 | 手术室利用率、ICU床位周转、设备利用率、耗材预警、感控监测 | 手术室利用率、设备OEE、耗材周转天数 | 医院 |
| `scene.hospital_patient` | 患者服务体验 | 导诊导航、床旁服务、住院缴费、报告查询、投诉建议、陪护管理 | 患者满意度、平均等待时长、自助服务率 | 医院 |
| `scene.logistics_sorting` | 分拣作业指挥 | 实时分拣进度、异常包裹、设备状态、人员排班、吞吐量预测 | 分拣效率、错分率、峰值吞吐、设备OEE | 物流 |
| `scene.logistics_warehouse` | 仓储作业管理 | 库存准确率、库位利用率、出入库效率、拣选路径、补货预警 | 库存周转、拣选准确率、空间利用率 | 物流 |
| `scene.logistics_lastmile` | 末端配送调度 | 网点负载、骑手轨迹、派单规则、时效达成、异常处理 | 及时率、单票成本、投诉率 | 物流 |
| `scene.dc_infrastructure` | 数据中心基建 | PUE趋势、机柜功率密度、冷热通道温差、UPS负载、发电机就绪 | PUE、机柜功率密度、可用性、碳效 | 数据中心 |
| `scene.dc_capacity` | 容量规划与销售 | 可售U位、功率余量、制冷余量、网络端口、交付交付周期 | 资源利用率、交付周期、预售准确率 | 数据中心 |
| `scene.park_energy` | 园区多能管理 | 多能流平衡、源网荷储、碳配额、能耗限额、虚拟电厂响应 | 综合能耗强度、可再生能源占比、碳排放强度 | 产业园区 |
| `scene.park_safety_env` | 园区安环合规 | 双重预防、隐患排查、环保在线、应急预案、应急演练、合规报表 | 隐患闭环率、超标零容忍、应急演练覆盖率 | 产业园区 |

### 4.4 工单/报表/大屏模板 — 50+ 个

- **工单模板**: 12 类 (巡检、维修、保养、校验、投诉、安检、环检、应急、变更、退役、验收、培训)
- **报表模板**: 18 类 (日/周/月/年能耗、设备运行、告警分析、工单绩效、合规台账、碳排放、客流分析、库存周转、产能报表)
- **大屏模板**: 8 类 (园区一张图、能碳驾驶舱、运营指挥、安环监管、零售运营、临床运营、物流指挥、校园大脑)

---

## 5. L4 Application Layer — 场景应用包规格

### 5.1 低代码页面组件库 (120+ 组件)

| 组件分类 | 组件数量 | 代表组件 | 复用率 |
|---------|---------|---------|-------|
| **数据展示** | 25 | 实时仪表盘、趋势图、热力图、桑基图、地理地图、资产树、拓扑图、KPI卡片 | 95% |
| **表单交互** | 18 | 工单表单、巡检记录、资产登记、参数配置、阈值设置、策略编排 | 90% |
| **地图可视化** | 12 | 2D平面图、3D场景、BIM模型、GIS地图、室内导航、热力图叠加 | 85% |
| **业务专用** | 35 | 电梯群控面板、分拣监控、手术室面板、病房看板、教室环境、充电桩运营、冷链监管 | 70% |
| **移动端** | 15 | 巡检APP、报修小程序、访客预约、考勤打卡、资产盘点、告警推送 | 80% |

### 5.2 仪表盘与报表预置 (80+ 个)

- **实时监控类**: 25 个 (能耗实时、设备状态、环境监测、安防状态、产线看板)
- **分析决策类**: 30 个 (能耗分析、设备健康、空间利用、人员效能、成本核算、碳资产)
- **合规报送类**: 15 个 (能耗上报、排污许可、碳核算、消防年检、电梯年检、特种设备、GSP/GMP)
- **高管视图类**: 10 个 (集团总览、区域对标、投资回报、战略KPI、风险热力)

### 5.3 移动端小程序/APP 模板 (7 套)

| 应用包 | 核心功能 | 目标用户 | 离线能力 |
|-------|---------|---------|---------|
| `app.community_resident` | 缴费、报修、访客、充电、快递、投票、公告 | 住户/租户 | 访客码离线核验 |
| `app.community_staff` | 巡检、工单、资产盘点、告警处理、值班交接 | 物业工程/安保/保洁 | 离线巡检/工单草稿 |
| `app.mall_merchant` | 能耗分摊、客流分析、报修、营销活动、招商资讯 | 商户/品牌方 | 离线查看报表 |
| `app.school_teacher` | 考勤、环境、设备报修、课表、通知、成绩 | 教师/行政 | 离线考勤同步 |
| `app.hospital_staff` | 资产查找、工单、巡检、耗材领用、交接班、应急预案 | 医护/后勤/工程 | 离线工单/巡检 |
| `app.logistics_operator` | 分拣监控、库存查询、车辆调度、异常处理、绩效查看 | 分拣员/司机/仓管/调度 | 离线扫码/轨迹缓存 |
| `app.park_enterprise` | 能耗查询、环保台账、安环隐患、应急演练、园区服务 | 入驻企业EHS/行政 | 离线隐患上报 |

---

## 6. L5 Operations Layer — 运维包规格

### 6.1 告警规则库 (200+ 规则) — 分级分类体系

#### 6.1.1 告警分级标准 (4 级)

| 级别 | 代码 | 响应时效 | 升级路由 | 典型场景 |
|------|------|---------|---------|---------|
| **P0 紧急** | `CRITICAL` | 1 分钟 | 值班长→部门负责人→总经理 | 火警、生命体征异常、供电中断、冷链断链、有毒泄漏 |
| **P1 重要** | `MAJOR` | 5 分钟 | 值班员→值班长→部门负责人 | 核心设备故障、温湿度超限、压力超限、客流异常、水浸 |
| **P2 一般** | `MINOR` | 30 分钟 | 值班员→班组长 | 非核心设备故障、通信中断、滤网堵塞、电池低电、证书过期 |
| **P3 提示** | `WARNING` | 4 小时 | 自动工单→班组长 | 维保到期、能耗偏高、利用率低、固件版本旧、配置漂移 |

#### 6.1.2 核心告警规则清单 (按场景分类)

**通用基座 (20条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 抑制策略 |
|-------|---------|---------|------|---------|
| `ALM-COM-001` | 设备离线/心跳丢失 | `last_seen > 5min` (关键) / `> 30min` (一般) | P1/P2 | 依赖抑制: 网关离线抑制下游 |
| `ALM-COM-002` | 通信质量劣化 | `packet_loss > 10%` 或 `latency > 5s` | P2 | 风暴抑制: 同网关 10 条/分钟 |
| `ALM-COM-003` | 电池电量低 | `battery < 20%` (关键) / `< 10%` (紧急) | P2/P1 | 抑制窗口: 夜间 22:00-06:00 降级 |
| `ALM-COM-004` | 存储空间不足 | `disk_usage > 85%` / `> 95%` | P2/P1 | — |
| `ALM-COM-005` | 证书/密钥即将过期 | `expiry < 30天` / `< 7天` | P3/P2 | — |

**智慧社区 (35条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 业务影响 |
|-------|---------|---------|------|---------|
| `ALM-COMM-001` | 电梯困人/故障停运 | 故障码含 `ENTRAP` 或 `STOPPED` > 30s | P0 | 启动应急救援 SOP |
| `ALM-COMM-002` | 电梯年检逾期 | `inspection_due < 0天` | P1 | 合规风险、保险拒赔 |
| `ALM-COMM-003` | 充电桩枪故障/离线 | `gun_status = FAULT` 或 `offline > 10min` | P2 | 充电服务中断、投诉 |
| `ALM-COMM-004` | 消火栓压力不足 | `pressure < 0.07MPa` (室内) / `< 0.15MPa` (室外) | P0 | 消防验收不合格、火灾隐患 |
| `ALM-COMM-005` | 燃气泄漏/报警 | `gas_concentration > 5%LEL` 报警 / `> 25%LEL` 紧急切断 | P0/P1 | 生命安全、必须联动电磁阀 |
| `ALM-COMM-006` | 供水压力异常 | `pressure < 0.15MPa` (高峰) / `> 0.45MPa` | P1 | 用户投诉、管网爆管风险 |
| `ALM-COMM-007` | 智能门锁电量极低/开锁失败 | `battery < 10%` / `unlock_fail > 5次/小时` | P2/P1 | 住户进不去家、安防风险 |
| `ALM-COMM-008` | 快递柜格口利用率过高/溢出 | `occupancy > 95%` / `overflow_packages > 0` | P3/P2 | 投递失败、用户投诉 |
| `ALM-COMM-009` | 灯杆挂载设备故障 | `mounted_device.status = FAULT` | P2 | 多功能杆价值减损 |
| `ALM-COMM-010` | 垃圾分类投放异常/满溢 | `fill_level > 90%` / `wrong_category > 30%` | P3/P2 | 环卫投诉、积分作弊 |

**智慧商场 (42条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 业务影响 |
|-------|---------|---------|------|---------|
| `ALM-MALL-001` | 冷水机组高压/低压保护 | `discharge_pressure > 1.8MPa` / `suction_pressure < 0.2MPa` | P0 | 全场制冷中断、客诉、食品安全 |
| `ALM-MALL-002` | AHU 送风温度偏差 | `\|supply_temp - setpoint\| > 2℃` 持续 15min | P2 | 舒适度、能耗浪费 |
| `ALM-MALL-003` | 冷却塔风机异常/振动超标 | `vibration > 7.1mm/s` (ISO 10816) | P1 | 制冷效率降、设备损坏 |
| `ALM-MALL-004` | 扶梯/电梯故障/年检逾期 | 同社区 + `overspeed` / `reverse` 保护动作 | P0/P1 | 客流疏导、监管罚款 |
| `ALM-MALL-005` | 照明回路功率异常/灯具损坏率高 | `power_deviation > 20%` / `failure_rate > 10%` | P2 | 能耗超标、光环境差 |
| `ALM-MALL-006` | 客流异常/踩踏预警 | `density > 4人/m²` / `inflow_rate > 設計值 1.5倍` | P0/P1 | 公共安全、应急疏散 |
| `ALM-MALL-007` | 防火卷帘/挡烟垂壁故障/误动作 | `position ≠ 期望值` / `unexpected_deploy` | P0 | 消防验收、保险、生命安全 |
| `ALM-MALL-008` | 新风机/全热交换器滤网堵塞/效率低 | `filter_dp > 200Pa` / `recovery_eff < 60%` | P2 | IAQ下降、能耗上升 |
| `ALM-MALL-009` | 厕所异味/用纸缺失/满负荷 | `NH3 > 5ppm` / `paper_out` / `occupancy > 90%` | P3/P2 | 客户体验、卫生评分 |
| `ALM-MALL-010` | 数字标牌离线/内容过期 | `offline > 15min` / `content_age > 7天` | P3 | 营销效果、导视失效 |

**智慧学校 (28条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 业务影响 |
|-------|---------|---------|------|---------|
| `ALM-SCH-001` | 教室 CO2 超标/考试模式静音失效 | `CO2 > 1000ppm` (常规) / `> 1500ppm` (考试) / 静音模式未生效 | P1/P0 | 学习效率、考试公平、健康 |
| `ALM-SCH-002` | 实验室通风柜面风速不达标 | `face_velocity < 0.5m/s` (化学) / `< 0.3m/s` (生物) | P1 | 化学品暴露、生物安全 |
| `ALM-SCH-003` | 实验室燃气/有毒气体泄漏 | `gas_alarm = TRUE` / `concentration > 阈值` | P0 | 爆炸/中毒风险、必须联动切断阀 |
| `ALM-SCH-004` | 宿舍晚归/陌生人闯入/尾随 | `late_return > 22:30` / `stranger_detected` / `tailgating` | P2/P1/P1 | 学生安全、校园秩序 |
| `ALM-SCH-005` | 食堂留样柜/消毒柜温度不达标 | `sample_temp > 4℃` / `disinfect_temp < 80℃` | P1 | 食品安全、监管处罚 |
| `ALM-SCH-006` | 图书馆/档案室温湿度失控 | `\|temp - 20\| > 2℃` / `\|RH - 50\| > 10%` | P1 | 书籍/档案损坏、不可逆 |
| `ALM-SCH-007` | 校车偏离路线/超速/学生遗漏 | `deviation > 200m` / `speed > limit` / `student_left` | P0 | 交通安全、学生遗漏 |
| `ALM-SCH-008` | 体育馆/泳池水质/环境异常 | `chlorine < 0.3` 或 `> 1.0mg/L` / `pH < 7.0` 或 `> 7.8` | P1 | 健康风险、卫生许可证 |

**智慧医院 (48条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 合规依据 |
|-------|---------|---------|------|---------|
| `ALM-HOS-001` | ICU/监护仪生命体征报警 | `HR < 40` / `> 130` / `SpO2 < 90%` / `SBP < 90` / `ETCO2 异常` | P0 | 医疗核心、生命安全 |
| `ALM-HOS-002` | 麻醉机/呼吸机气道压力/潮气量异常 | `Paw > 40cmH2O` / `Vt < 设定值 50%` / `FiO2 偏差` | P0 | 手术安全、呼吸机相关肺损伤 |
| `ALM-HOS-003` | 影像设备剂量超标/QC 不合格 | `DLP > DRL` / `CTDI > 限值` / `QC 失败` | P1 | 辐射防护法、GBZ 130 |
| `ALM-HOS-004` | 血液/试剂/样本冷链断链 | `temp 超出 2-6℃/-30~-60℃` 持续 > 15min | P0 | GSP、WS 352、样本质量 |
| `ALM-HOS-005` | 手术室/层流洁净度/压差失效 | `洁净度 > 级别限值` / `压差 < 5Pa` (正压) / `> -5Pa` (负压) | P0 | GB 50333、感控核心指标 |
| `ALM-HOS-006` | 医用气体(氧/气/吸)压力/流量异常 | `压力偏差 > 10%` / `流量不足` / `露点超标` / `CO 超标` | P0 | YY/T 0298、生命支持 |
| `ALM-HOS-007` | 医疗废物暂存超时/重量异常/联单断链 | `存放 > 48h` / `重量偏差 > 5%` / `电子联单中断` | P1 | GB 19218、环保执法 |
| `ALM-HOS-008` | 护士呼叫响应超时/未响应 | `响应时间 > 3min` (普通) / `> 30s` (急救) / `无响应` | P1/P0 | 护理质量、患者满意度、医疗纠纷 |
| `ALM-HOS-009` | 医疗资产丢失/离区/维保逾期 | `UWB 离开区域` / `维保逾期` / `计量检定逾期` | P2/P1 | 资产流失、合规、医疗事故隐患 |
| `ALM-HOS-010` | 母婴防盗/新生儿离区/腕带脱落 | `婴儿标签离开产科区域` / `母婴配对失败` / `腕带剪断` | P0 | 医疗安全核心事件、重大舆情 |

**智慧物流 (32条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 业务影响 |
|-------|---------|---------|------|---------|
| `ALM-LOG-001` | 分拣机卡阻/错分/识别失败 | `jam = TRUE` / `misroute_rate > 1%` / `no_read_rate > 5%` | P1/P2 | 时效延误、错分赔付、人工干预成本 |
| `ALM-LOG-002` | 输送线堆积/跑偏/撕裂/急停 | `accumulation > 阈值` / `belt_mistrack` / `tear_detected` / `estop` | P1/P0 | 产线停工、货物积压、安全事故 |
| `ALM-LOG-003` | AGV/AMR 离线/卡死/电量不足/碰撞 | `offline > 2min` / `stuck > 5min` / `battery < 15%` / `collision` | P1/P2 | 柔性产线瘫痪、货物延误、设备损坏 |
| `ALM-LOG-004` | 立库/穿梭车故障/货位异常/盘点差异 | `stacker_fault` / `shuttle_error` / `location_mismatch` / `inventory_diff > 0.1%` | P1/P2 | 高密存储瘫痪、库存准确率、找货困难 |
| `ALM-LOG-005` | 装卸平台/登车桥故障/车辆超时 | `leveler_fault` / `dock_occupy > 2h` / `truck_wait > 4h` | P2/P3 | 场区拥堵、车辆周转、滞港费 |
| `ALM-LOG-006` | 冷链温度偏离/记录仪丢失/开门异常 | `temp_out_of_range` / `logger_lost` / `door_open > 10min` | P0/P1 | 货值损失、GSP违规、保险拒赔、食品安全 |
| `ALM-LOG-007` | 末端柜/驿站格口溢出/超时未取/破损 | `occupancy > 95%` / `overtime > 24h` / `damage_report` | P2/P3 | 投递失败、客诉、赔付 |
| `ALM-LOG-008` | 场区车辆滞留/调度冲突/违规停放 | `dwell_time > SLA` / `scheduling_conflict` / `illegal_parking` | P2/P3 | 场区效率、车辆周转、安全隐患 |

**数据中心 (40条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 合规/SLA |
|-------|---------|---------|------|---------|
| `ALM-DC-001` | PDU/母线槽分支过载/不平衡 | `branch_current > 80% rated` / `unbalance > 15%` | P1/P0 | 断路器跳闸风险、可用性 SLA |
| `ALM-DC-002` | UPS 负载率/电池健康度/备份时间不足 | `load > 80%` / `SOH < 80%` / `backup < 15min` | P1/P0 | Tier 3/4 可用性、电池更换窗口 |
| `ALM-DC-003` | 发电机启动失败/油位低/自启动未就绪 | `start_fail` / `fuel_level < 8h` / `auto_start_not_ready` | P0 | 应急电源、Tier 认证 |
| `ALM-DC-004` | 精密空调/列间制冷失效/温湿度超标 | `cooling_fault` / `rack_inlet > 27℃` / `ΔT > 10℃` / `RH 超标` | P0/P1 | ASHRAE TC 9.9、硬件寿命、宕机风险 |
| `ALM-DC-005` | 机柜功率密度超规划/热点 | `kW/rack > 设计值` / `hotspot > 35℃` | P1 | 容量规划、扩容触发、硬件降频 |
| `ALM-DC-006` | 液冷 CDU/歧管泄漏/流量压力异常/水质 | `leak_detected` / `flow < 设定值 80%` / `ΔP 异常` / `conductivity > 10μS/cm` | P0/P1 | 硬件报废风险、数据中心核心风控 |
| `ALM-DC-007` | 气体灭火系统压力/喷放/误报 | `pressure < 90%` / `discharge_activated` / `false_alarm` | P0/P1 | GB 50370、资产保护、误喷损失巨大 |
| `ALM-DC-008` | 光缆/ODF 损耗高/端面脏污/容量不足 | `loss > 3dB` / `endface_dirty` / `port_util > 90%` | P2/P1 | 网络质量、扩容阻塞、故障定位难 |
| `ALM-DC-009` | PUE 实时/日均超目标/趋势恶化 | `realtime_PUE > 1.3` / `daily_PUE > 1.25` / `趋势上升` | P2/P3 | 碳配额、运营成本、绿电认证 |
| `ALM-DC-010` | 资产未授权变更/未登记/生命周期异常 | `unauthorized_change` / `unregistered_asset` / `EOL_not_replaced` | P2/P1 | 变更管理、审计合规、容量规划 |

**产业园区 (55条)**
| 规则ID | 规则名称 | 触发条件 | 级别 | 合规/标准 |
|-------|---------|---------|------|---------|
| `ALM-PARK-001` | 锅炉/压力容器超压/超温/水位异常/安检逾期 | `P > 设计压力` / `T > 金属温度` / `水位 < 低水位` / `检验逾期` | P0 | TSG G0001、特种设备法、强制检验 |
| `ALM-PARK-002` | 换热站供回水温压/换热效率偏差 | `\|供温 - 设定\| > 5℃` / `效率 < 85%` / `结垢指数 > 阈值` | P1/P2 | 供热质量、能耗、设备寿命 |
| `ALM-PARK-003` | 空压机排气压力/温度/露点/卸载比异常 | `P > 设定` / `T > 110℃` / `露点 > -40℃` / `卸载 > 30%` | P1/P2 | 产气量、气体质量、能耗占比 15-30% |
| `ALM-PARK-004` | 中央冷站群控失效/COP 低/冷冻水泵气蚀 | `群控离线` / `COP < 设计值 90%` / `泵振动/噪音/气蚀` | P1 | 制冷核心、单耗考核、设备寿命 |
| `ALM-PARK-005` | 水处理出水水质/膜通量/药剂消耗异常 | `电导率/硬度/TOC/COD 超标` / `通量下降 > 20%` / `药耗 > 1.5倍` | P1 | 工艺用水合规、膜寿命、运营成本 |
| `ALM-PARK-006` | 天然气门站/调压箱压力/流量/切断阀异常 | `出口压力偏差 > 5%` / `流量突变` / `切断阀误动作` / `加臭量异常` | P0 | 城市燃气安全、CJ 4255、应急切断 |
| `ALM-PARK-007` | 废水/废气/固废超标/在线监测故障/台账断档 | `COD/氨氮/总氮/TVOC/颗粒物 > 排放限值` / `CEMS故障` / `台账缺失` | P0/P1 | 排污许可证、环保法、按日计罚、刑事责任 |
| `ALM-PARK-008` | CEMS/VOCs/LDAR 监测数据异常/超标/比对不合格 | `超标` / `零点/量程漂移` / `比对偏差 > 10%` / `数据缺失` | P0/P1 | 环保执法核心证据、自动监控考核 |
| `ALM-PARK-009` | 起重机/行车超载/防碰撞/防摆/黑匣子/年检逾期 | `载荷 > 额定` / `防碰撞失效` / `防摆失效` / `黑匣子数据缺失` / `检验逾期` | P0/P1 | 特种设备法、港口作业安全、保险理赔 |
| `ALM-PARK-010` | 长距皮带/管状带撕裂/跑偏/堵料/张力异常 | `撕裂检测触发` / `跑偏 > 50mm` / `堵料/堵煤` / `张力偏差 > 15%` | P0/P1 | 连续生产中断、清理成本高、安全事故 |
| `ALM-PARK-011` | 地磅/汽车衡计量不准/防作弊/检定逾期 | `示值误差 > 最大允许误差` / `防作弊触发` / `强检逾期` | P1/P0 | 计量法、贸易结算、税务稽查、防舞弊 |
| `ALM-PARK-012` | 抑尘/喷淋/雾炮 未按浓度联动/用水异常/防冻失效 | `PM10 > 300μg/m³ 未启动` / `用水量异常` / `管路冻裂` | P1/P2 | 扬尘污染、环保督察、水资源成本 |
| `ALM-PARK-013` | 周界入侵/报警/视频联动失效/误报风暴 | `入侵报警` / `视频联动失败` / `误报 > 10次/小时` | P1/P2 | 园区安防、危化品区域、资产安全 |
| `ALM-PARK-014` | 无人值守地磅/智能闸口 过磅异常/识别失败/黑白名单失效 | `重复过磅` / `车牌识别率 < 95%` / `黑名单未拦截` / `白名单被拦` | P1/P2 | 物流效率、防作弊、准入管控 |
| `ALM-PARK-015` | 能源/碳管理 指标超限/配额预警/虚拟电厂响应失败 | `单耗 > 限额` / `碳排放 > 配额 90%` / `需求响应未响应` | P2/P1 | 双控考核、碳交易履约、虚拟电厂收益 |

### 6.2 SOP 标准作业程序手册 (105+ 份)

| SOP 编号 | SOP 名称 | 适用场景 | 关键节点 | 预计耗时 | 责任角色 |
|---------|---------|---------|---------|---------|---------|
| `SOP-COM-001` | 设备日常巡检通用流程 | 全场景 | 路线规划→现场核对→记录异常→拍照上传→签名确认→异常派单 | 30-60min/巡检点 | 巡检员 |
| `SOP-COM-002` | 告警处置通用流程 | 全场景 | 接收告警→研判定级→现场核实→处置恢复→根因分析→归档复盘 | 15min-4h | 值班员/专业工程师 |
| `SOP-COM-003` | 资产入网/注册/退役全流程 | 全场景 | 信息采集→模板选择→参数配置→协议适配→测试验收→上线运行/退役清理 | 30min-2h | 实施工程师/运维 |
| `SOP-COMM-001` | 电梯困人应急救援 | 社区/商场/医院/学校/园区 | 接报→安抚乘客→联系维保/119→现场解救→乘客体检→故障排查→恢复运行→报告 | <30min 救援 | 物业/维保/消防 |
| `SOP-COMM-002` | 燃气泄漏应急处置 | 社区/商场/学校/医院/园区 | 发现报警→切断气源→疏散人员→通风置换→检测复测→修复验收→恢复供气 | <10min 切断 | 工程/安保/燃气公司 |
| `SOP-MALL-001` | 商场踩踏/客流激增应急疏散 | 商场 | 监测预警→启动预案→分流引导→疏散通道开放→人员清点→秩序恢复 | <5min 启动 | 安保/运营/公安 |
| `SOP-MALL-002` | 中央空调主机故障应急切换/降级 | 商场/医院/数据中心/园区 | 故障确认→备用机启动→负荷转移→参数调整→根因排查→主机修复→切回 | <15min 切换 | 运行工程师 |
| `SOP-SCH-001` | 实验室有毒气体泄漏应急 | 学校/医院/园区 | 报警触发→自动切断阀→疏散→通风→专业处置→监测合格→恢复→调查报告 | <1min 切断 | 实验室主管/安环/EHS |
| `SOP-HOS-001` | 手术室/层流洁净度失效应急 | 医院 | 压差/洁净度异常→手术暂停/转移→源头排查→恢复验证→手术继续/重新安排 | <5min 决策 | 手术部护士长/工程/感控 |
| `SOP-HOS-002` | 医用氧气/气体供应中断应急 | 医院 | 压力报警→备用瓶组自动切换/人工切换→故障定位→修复→压力恢复→全网验证 | <30s 切换 | 工程/临床/药械科 |
| `SOP-HOS-003` | 医疗废物泄漏/遗失/超时应急 | 医院 | 发现→隔离围堵→专业处置→流向追溯→责任追究→整改验收→上报卫健委 | 立即 | 感控/后勤/安保/法务 |
| `SOP-LOG-001` | 分拣主线故障应急分流/人工兜底 | 物流 | 故障定位→分流开关→人工分拣线启用→进度跟踪→设备修复→逐步切回 | <10min 分流 | 调度/运维/作业主管 |
| `SOP-LOG-002` | 冷链断链/温度偏离应急处置 | 物流/医药/生鲜 | 温度报警→货物隔离→温度记录核实→应急制冷/转运→损失评估→理赔/销毁→整改 | <30min 隔离 | 冷链主管/质量/保险 |
| `SOP-DC-001` | 数据中心制冷失效/热点应急 | 数据中心 | 机柜入口温度超标→列间/行级应急制冷→负载迁移/降额→故障排除→恢复验证 | <5min 降温 | DC运维/IT/厂商 |
| `SOP-DC-002` | 供电中断/UPS放电/发电机切换应急 | 数据中心 | 市电中断→UPS逆变→发电机启动→并网/切换→市电恢复→同步切回→电池充电 | 0ms 切换 (UPS) / <30s 发电机 | 电气运维/IT/厂商 |
| `SOP-PARK-001` | 特种设备(锅炉/压力容器/起重机)事故应急 | 产业园区 | 事故发生→紧急停机/卸荷→人员疏散/救援→现场保护→专家组调查→监管上报→整改复查 | 立即 | EHS/特种设备管理/安监局 |
| `SOP-PARK-002` | 危化品/有毒气体泄漏应急处置 | 产业园区/医院/学校实验室 | 泄漏报警→自动切断→应急小组响应→堵漏/稀释/收集→环境监测→区域解封→调查报告 | <3min 响应 | EHS/消防/环保/公安 |
| `SOP-PARK-003` | 环保超标/在线监测异常应急响应 | 产业园区 | 超标报警→自动/人工减排/停产→数据核实→向环保部门报告→整改销号→恢复生产 | <2h 上报 | EHS/生产/环保局 |
| `SOP-PARK-004` | 多能互补/源网荷储 调度优化/需求响应执行 | 产业园区/数据中心 | 预测发电/负荷→优化调度下发→设备响应→实时偏差修正→结算核算→复盘优化 | 日前/日内/实时 | 能源管理中心/调度员 |

### 6.3 巡检计划模板 (Inspection Plans)

| 计划代码 | 名称 | 频次 | 覆盖资产 | 关键检查项 | 记录方式 |
|---------|------|------|---------|-----------|---------|
| `INSP-DAILY` | 日常巡检 | 每日 2-4 次 | 关键设备、重点区域 | 运行参数、状态指示、异常声响、振动、泄漏、温度 | 移动端 APP、语音、拍照、NFC 打卡 |
| `INSP-WEEKLY` | 周巡检 | 每周 1 次 | 全量设备、消防设施、安防系统 | 功能测试、联动测试、备用电源、应急照明、灭火器压力 | 移动端 + 纸质备份 |
| `INSP-MONTHLY` | 月度专项巡检 | 每月 1 次 | 精密空调、UPS、发电机、电梯、锅炉、压力容器、起重机 | 深度检查、参数记录、油样/水样分析、振动频谱、绝缘电阻 | 专业工具 + 移动端 |
| `INSP-QUARTERLY` | 季度维保/校验 | 每季度 1 次 | 计量器具、特种设备、消防系统、医用气体、洁净室 | 第三方校验、法定检验、性能测试、合格证更新 | 第三方报告 + 系统录入 |
| `INSP-ANNUAL` | 年度大修/年检 | 每年 1 次 | 全厂停机检修、特种设备年检、认证审核 | 全面拆检、更换易损件、精度校准、认证审核 | 详细报告、档案归档 |

### 6.4 应急预案库 (Emergency Plans) — 25+ 个

| 预案代码 | 预案名称 | 触发条件 | 指挥体系 | 关键资源 | 演练频次 |
|---------|---------|---------|---------|---------|---------|
| `EMG-FIRE` | 火灾应急预案 | 火警确认/手动拉启 | 总指挥-现场指挥-疏散组-灭火组-通讯组-医疗组-后勤组 | 消防设施、疏散通道、应急广播、防毒面具、担架 | 半年 1 次 |
| `EMG-POWER` | 供电中断/限电应急预案 | 市电中断/限电通知/负荷超限 | 电力调度长-发电机组长-负荷削减组-通讯组 | 发电机、UPS、可中断负荷清单、双电源切换 | 季度 1 次 |
| `EMG-GAS` | 燃气/有毒气体泄漏应急预案 | 泄漏报警/人员嗅觉/检测仪 | 总指挥-抢险组-疏散组-监测组-医疗组-后勤组 | 切断阀、正压式空呼、可燃气检测仪、稀释喷淋、防化服 | 季度 1 次 |
| `EMG-WATER` | 供水中断/污染/管网爆管应急预案 | 停水通知/水质异常/爆管 | 调度长-抢修组-供水保障组-水质监测组-用户通知组 | 备用水源、应急水车、水质检测箱、抢修物料 | 半年 1 次 |
| `EMG-IT` | 网络/系统/数据中心故障应急预案 | 核心网络中断/系统崩溃/数据丢失/勒索软件 | CIO-网络组-系统组-数据组-安全组-业务连续性组 | 备用链路、灾备中心、备份数据、应急终端、隔离网络 | 季度 1 次 |
| `EMG-CHEM` | 危化品/化学品泄漏应急预案 | 泄漏/着火/爆炸/人员中毒 | 总指挥-抢险组-疏散组-监测组-环保组-医疗组-联络组 | 吸附棉、围堰、中和剂、泡沫灭火、防化服、气象站 | 季度 1 次 |
| `EMG-MED` | 群体性伤病/疫情/食品安全应急预案 | 多人伤病/传染病暴发/食物中毒 | 卫生应急指挥-医疗救治组-流调溯源组-消杀组-后勤保障组-舆情组 | 救护车、急救药品、采样管、消杀设备、隔离场所 | 半年 1 次 |
| `EMG-STRUCT` | 结构性安全/坍塌/地质灾害应急预案 | 沉降/裂缝/滑坡/塌方/地震 | 总指挥-监测组-抢险组-疏散组-专家组-后勤组 | 监测仪器、支护材料、重型机械、应急避难场所 | 年度 1 次 |

### 6.5 能耗基准与 KPI 标杆 (Energy Baselines & KPIs)

| 场景 | 单位面积年耗电基准 (kWh/m²) | 单位面积年耗热基准 (kgce/m²) | PUE 目标 | 碳排放强度 (kgCO₂/m²) | 可再生能源占比目标 |
|------|----------------------------|------------------------------|---------|----------------------|-------------------|
| 智慧社区 (住宅) | 35-45 | 15-20 | — | 25-35 | ≥ 20% (分布式光伏) |
| 智慧商场 | 120-180 | 30-50 | — | 80-130 | ≥ 30% (光伏+绿电) |
| 智慧学校 | 40-60 | 10-15 | — | 30-45 | ≥ 25% (光伏+光储) |
| 智慧医院 | 150-220 | 40-60 | — | 100-160 | ≥ 20% (绿电+热泵) |
| 智慧物流 | 25-40 (仓储) / 15-25 (分拣) | 5-10 | — | 20-35 | ≥ 40% (屋顶光伏+储能) |
| 数据中心 | — | — | 1.25 (新建) / 1.35 (存量) | 视电力结构 | ≥ 50% (绿电直供+绿证) |
| 产业园区 | 视行业 | 视行业 | — | 视行业 | ≥ 30% (分布式能源+虚拟电厂) |

---

## 7. 部署与交付规格

### 7.1 Helm Chart 部署包结构

```
smart-park-asset-package/
├── Chart.yaml                    # 包元数据: name, version, appVersion, dependencies
├── values.yaml                   # 全局默认值 (含全场景通用配置)
├── values-smart-park.yaml        # Smart Park 场景化参数文件 (核心交付物)
├── values-community.yaml         # 社区场景覆盖值
├── values-mall.yaml              # 商场场景覆盖值
├── values-school.yaml            # 学校场景覆盖值
├── values-hospital.yaml          # 医院场景覆盖值
├── values-logistics.yaml         # 物流场景覆盖值
├── values-datacenter.yaml        # 数据中心场景覆盖值
├── values-industrial-park.yaml   # 产业园区场景覆盖值
├── templates/
│   ├── _helpers.tpl              # 模板函数库
│   ├── ontology/                 # L1: CRD 资产类型、属性、关系、枚举
│   ├── capabilities/             # L2: 能力定义、规则模板、适配器映射
│   ├── templates/                # L3: 资产/空间/场景/工单/报表/大屏模板
│   ├── applications/             # L4: 低代码页面、组件、仪表盘、移动端配置
│   └── operations/               # L5: 告警规则、SOP、巡检计划、应急预案、基准
├── crds/                         # Kubernetes CRD 定义
├── charts/                       # 子 Chart 依赖
├── tests/                        # Helm test: 资产包完整性、模板渲染、场景验证
└── README.md                     # 部署指南、参数说明、场景选择指引、升级迁移
```

### 7.2 values-smart-park.yaml 核心参数化设计 (关键交付物)

```yaml
# Smart Park 资产包统一参数化入口
# 通过场景选择器激活对应层级配置，实现"一次打包、多场景部署"

global:
  # 租户标识 (部署时注入)
  tenantId: ""
  tenantName: ""
  
  # 场景选择器: 单选或多选 [community, mall, school, hospital, logistics, datacenter, industrial_park]
  enabledScenarios: ["community", "mall", "school", "hospital", "logistics", "datacenter", "industrial_park"]
  
  # 部署模式: full(全量) | minimal(最小化: 仅L1+L2) | custom(自定义层级)
  deploymentMode: "full"
  
  # 语言/地区化
  locale: "zh-CN"
  timezone: "Asia/Shanghai"
  
  # 合规模式: standard | strict(医院/园区/数据中心强制)
  complianceMode: "standard"

# L1 Ontology 配置
ontology:
  # 是否启用资产类型扩展 (允许租户自定义资产类型)
  allowCustomAssetTypes: true
  # 默认空间层级深度
  defaultSpaceDepth: 5
  # 单位制: metric | imperial
  unitSystem: "metric"
  # 坐标系: WGS84 | GCJ02 | BD09 | local
  coordinateSystem: "GCJ02"

# L2 Capability 配置
capabilities:
  # 启用的通用能力
  enabledCoreCapabilities:
    - telemetry.read
    - telemetry.write
    - telemetry.subscribe
    - asset.discover
    - asset.provision
    - firmware.ota
    - alarm.evaluate
    - kpi.compute
  
  # 场景专用能力开关
  scenarioCapabilities:
    community:
      - hvac.cooling_optimize
      - lighting.daylight_harvest
      - energy.demand_response
      - elevator.group_control
      - parking.guidance
    mall:
      - hvac.cooling_optimize
      - hvac.ahu_optimize
      - lighting.daylight_harvest
      - energy.demand_response
      - retail.footfall_analytics
      - retail.energy_benchmark
      - elevator.group_control
      - parking.guidance
    school:
      - school.iaq_guardian
      - school.attendance_safe
      - energy.demand_response
    hospital:
      - hospital.asset_tracking
      - hospital.critical_env
      - hospital.med_safety
      - hvac.cooling_optimize
      - hvac.ahu_optimize
      - energy.carbon_accounting
    logistics:
      - logistics.sorting_optimize
      - logistics.cold_chain_guard
      - logistics.yard_scheduling
      - energy.demand_response
    datacenter:
      - dc.pue_optimize
      - dc.capacity_planning
      - energy.carbon_accounting
      - equipment.health_index
    industrial_park:
      - park.multi_energy_synergy
      - park.env_compliance
      - equipment.health_index
      - energy.carbon_accounting
      - energy.demand_response

  # 协议适配器映射
  adapterMapping:
    bacnet: ["hvac.*", "lighting.*", "elevator.*", "fire.*", "water.*"]
    modbus: ["power.*", "energy.*", "env.*", "chiller.*", "pump.*", "compressor.*"]
    mqtt: ["iot.*", "sensor.*", "tracker.*", "robot.*", "gateway.*"]
    opcua: ["plc.*", "scada.*", "mes.*", "robot.*", "analyzer.*"]

# L3 Template 配置
templates:
  activationPolicy: "scenario_based"  # scenario_based | all | manual

# L4 Application 配置
applications:
  autoGeneratePages: true
  buildMobileApps: true
  presetDashboards: true
  theme:
    primaryColor: "#165DFF"
    mode: "light"

# L5 Operations 配置
operations:
  autoEnableAlarms: true
  sopWorkOrderBinding: true
  autoGenerateInspectionPlans: true
  drillReminderEnabled: true
  baselineAutoCalibration: true

# 基础设施依赖
infrastructure:
  timescaledb:
    host: "timescaledb"
    port: 5432
    database: "telemetry"
  postgresql:
    host: "postgresql"
    port: 5432
    database: "dtlite_core"
  redis:
    host: "redis"
    port: 6379
  emqx:
    host: "emqx"
    port: 1883
    dashboardPort: 18083
  minio:
    endpoint: "minio:9000"
    bucket: "asset-package"
  neo4j:
    uri: "bolt://neo4j:7687"
```

### 7.3 升级与迁移策略 (Upgrade Matrix)

| 版本跨度 | 迁移策略 | 数据兼容 | 停机窗口 | 回滚机制 |
|---------|---------|---------|---------|---------|
| Patch (v1.0.x → v1.0.y) | 滚动升级 | 完全兼容 | 0 | Helm rollback |
| Minor (v1.0 → v1.1) | 蓝绿部署 | 向前兼容 (新增字段可选) | < 5 min | 蓝绿切回 + DB 迁移回滚脚本 |
| Major (v1.x → v2.0) | 并行运行 + 数据迁移 | 需迁移脚本 | 计划停机窗口 | 完整备份恢复 + 双写验证 |

---

## 8. 质量保障与验收标准

### 8.1 资产包完整性检查清单 (CI/CD Gate)

```bash
# 自动化验证管道 (集成到 GitLab CI / GitHub Actions)
stages:
  - lint:           # YAML/JSON Schema 语法校验、命名规范、必填字段
  - schema-validate: # JSON Schema 验证 (asset-types, capabilities, templates)
  - reference-check: # 交叉引用完整性 (能力→适配器、模板→资产类型、告警→资产)
  - scenario-test:  # 7大场景端到端渲染测试 (Helm template --dry-run)
  - alarm-syntax:   # 告警规则表达式语法、引用资产存在性
  - sop-completeness: # SOP 步骤完整性、责任角色存在性、时效合理性
  - baseline-sanity: # 基准值范围合理性、单位一致性
  - security-scan:  # 无硬编码密钥、最小权限、敏感数据脱敏
  - performance:    # 模板渲染 < 30s、资产包加载 < 2min、内存 < 512MB
```

### 8.2 零代码部署验收标准 (SLA)

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| **首次部署时长** | ≤ 2 小时 (含基础设施) | 从 `helm install` 到所有场景页面可访问 |
| **场景切换/新增时长** | ≤ 15 分钟 | 修改 `values-smart-park.yaml` → `helm upgrade` → 验证 |
| **资产包加载时间** | < 2 分钟 (50+ 资产类型、200+ 告警、105 SOP) | CI 基准测试 |
| **模板渲染成功率** | 100% | 7 场景 × 5 层 × 3 环境 (dev/staging/prod) |
| **跨场景资产复用率** | ≥ 80% (通用基座) | 资产类型复用统计 |
| **告警规则零误报率(基线)** | 误报率 < 5% (运行 30 天后) | 告警分析报告 |
| **SOP 执行合规率** | ≥ 95% | 工单系统统计 |
| **多语言完整性** | 100% 中文、90% 英文 | i18n 密钥覆盖扫描 |

### 8.3 版本发布清单 (Release Checklist)

- [ ] `Chart.yaml` 版本号语义化更新 (SemVer)
- [ ] `CHANGELOG.md` 更新: 新增资产类型、能力、模板、告警、SOP、修复项
- [ ] `UPGRADE.md` 迁移指南: 破坏性变更、手动步骤、数据迁移脚本
- [ ] 7 场景全量 Helm test 通过
- [ ] 3 环境 (dev/staging/prod) 部署验证通过
- [ ] 安全扫描通过 (Trivy, Checkov, 密钥扫描)
- [ ] 文档同步: README、架构决策记录(ADR)、运维手册、用户手册
- [ ] 签名发布: `helm package --sign --keyring <key> --key <key-id>`
- [ ] 发布到 Chart Museum / OCI Registry / 私有 Helm 仓库
- [ ] 通知下游租户: 发布公告、升级建议、废弃时间表

---

## 9. 交付物清单 (Deliverables)

| 交付物 | 格式 | 存储位置 | 版本控制 | 更新频率 |
|--------|------|---------|---------|---------|
| **核心规格说明书** | Markdown | `docs/architecture/asset-packages/smart-park/SPEC.md` | Git | Minor 版本 |
| **Helm Chart 包** | `.tgz` + Provenance | OCI Registry / Chart Museum | Helm Repo Index | Patch 版本 |
| **values-smart-park.yaml** | YAML | `charts/smart-park/values-smart-park.yaml` | Git | 按需 |
| **场景化 values 文件** | YAML (7个) | `charts/smart-park/values-*.yaml` | Git | 按需 |
| **资产类型 JSON Schema** | JSON | `schemas/asset-types/` | Git | Minor 版本 |
| **能力定义 JSON Schema** | JSON | `schemas/capabilities/` | Git | Minor 版本 |
| **模板库** | YAML/JSON | `templates/` | Git | Minor 版本 |
| **低代码页面/组件源码** | Vue/TypeScript | `apps/web/src/asset-packages/smart-park/` | Git | Sprint 级 |
| **移动端应用配置** | JSON | `apps/mobile/config/smart-park/` | Git | Sprint 级 |
| **告警规则库** | YAML | `operations/alarm-rules/` | Git | 持续 |
| **SOP 文档库** | Markdown/PDF | `operations/sops/` | Git | 持续 |
| **巡检/应急预案/基准** | YAML/Markdown | `operations/` | Git | 季度 |
| **测试用例套件** | YAML/Python | `tests/asset-packages/smart-park/` | Git | 发布前 |
| **部署运维手册** | Markdown | `docs/operations/smart-park-deployment.md` | Git | 发布同步 |
| **用户使用手册** | Markdown/在线文档 | `docs/user/smart-park-user-guide.md` | Git | 发布同步 |
| **架构决策记录 (ADR)** | Markdown | `docs/architecture/decisions/ADR-*.md` | Git | 决策时 |

---

## 10. 实施路线图 (Implementation Roadmap)

### Phase 1: 核心基座通用包 (Week 1-2) ✅ **已完成**
- L1: 通用基座 8 类资产类型、空间层级、关系拓扑
- L2: 8 个通用能力、协议适配器映射矩阵
- L3: 通用资产模板、空间模板、基础场景模板
- L4: 通用组件库、基础仪表盘
- L5: 通用告警规则 (20)、通用 SOP (10)、巡检计划模板

### Phase 2: 7 大场景专有包并行开发 (Week 3-6)
| 场景 | 负责小组 | 里程碑 | 交付物 |
|------|---------|--------|--------|
| 智慧社区 | Squad A | W3: Ontology+Capability, W4: Template+App, W5: Ops, W6: 集成测试 | 12资产、5能力、3场景、35告警、18SOP |
| 智慧商场 | Squad B | W3-6 同步 | 15资产、6能力、3场景、42告警、22SOP |
| 智慧学校 | Squad C | W3-6 同步 | 10资产、4能力、2场景、28告警、15SOP |
| 智慧医院 | Squad D | W3-6 同步 | 14资产、7能力、3场景、48告警、25SOP |
| 智慧物流 | Squad E | W3-6 同步 | 11资产、5能力、2场景、32告警、16SOP |
| 数据中心 | Squad F | W3-6 同步 | 9资产、6能力、1场景、40告警、20SOP |
| 产业园区 | Squad G | W3-6 同步 | 18资产、8能力、4场景、55告警、28SOP |

**同步检查点 (每周五 16:00)**:
- 跨场景资产类型复用评审 (避免重复造轮子)
- 能力定义一致性检查 (命名、接口、参数)
- 告警分级校准 (P0-P3 定义对齐)
- SOP 术语统一 (动作动词、责任角色、时效标准)

### Phase 3: 集成测试与场景验证 (Week 7-8)
- **Week 7**: 7 场景全量 Helm 渲染测试、跨场景资产包冲突检测、性能基准测试
- **Week 8**: 3 环境部署验证、种子数据导入、端到端场景演练 (模拟 1000+ 资产)、用户验收测试 (UAT)

### Phase 4: 文档闭环与发布 (Week 9)
- 文档完整性审查、多语言校对、安全合规扫描、发布签名、Chart 仓库发布、社区公告

### Phase 5: 运营迭代 (持续)
- 月度: 告警规则调优、SOP 迭代、基准值重标定
- 季度: 新增资产类型、能力增强、场景模板扩展
- 半年: Major 版本规划、架构演进、技术债务偿还

---

## 11. 关键依赖与约束

### 11.1 平台版本依赖
| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| DT-Lite Core | v4.18.0 | v4.18.x | Task 18 Edge Computing 合并后版本 |
| Ontology Service | v4.15.0 | v4.18.x | CRD v1beta1 稳定 |
| Capability Service | v4.16.0 | v4.18.x | ADR-008 匹配引擎 |
| Template Service | v4.14.0 | v4.18.x | 模板版本管理 |
| Deployment Service | v4.17.0 | v4.18.x | Helm 渲染器 |
| Provisioning Service | v4.17.0 | v4.18.x | 批量注册/激活 |
| Adapter Layer | v4.15.0 | v4.18.x | BACnet/Modbus/MQTT/OPC-UA |
| Telemetry Pipeline | v4.16.0 | v4.18.x | 连续聚合、数据质量 |
| AI Agent & RAG | v4.17.0 | v4.18.x | 智能巡检、根因分析、报表生成 |

### 11.2 基础设施要求
| 资源 | 最小规格 | 生产建议 | 备注 |
|------|---------|---------|------|
| Kubernetes | 1.27+ | 1.28+ (EKS/GKE/ACK/自建) | 支持 CRD、Operator |
| PostgreSQL | 15+ | 16 (主从/Patroni) | 元数据、租户隔离 |
| TimescaleDB | 2.11+ | 2.13+ (分布式/多节点) | 遥测数据、连续聚合 |
| Redis | 7.0+ | 7.2+ (Cluster) | 缓存、会话、分布式锁 |
| EMQX | 5.3+ | 5.6+ (Cluster) | MQTT 接入、规则引擎 |
| MinIO | RELEASE.2023+ | RELEASE.2024+ (分布式) | 对象存储、模型/固件/报表 |
| Neo4j | 5.10+ | 5.15+ (因果集群) | 知识图谱、RAG 图检索 |

### 11.3 合规与安全约束
- **数据主权**: 所有租户数据物理隔离 (Schema 级 + Row Level Security)
- **等保三级**: 审计日志留存 ≥ 6 个月、关键操作双人复核、密钥国密 SM2/SM4
- **行业合规**: 医院 (分级诊疗/电子病历/药品追溯)、数据中心 (能效/PUE/绿电)、园区 (排污许可/双重预防/应急预案)
- **供应链安全**: 适配器镜像签名验证 (Cosign)、SBOM 生成 (Syft)、漏洞扫描 (Grype/Trivy)

---

## 12. 附录

### 附录 A: 资产类型编码规范 (Naming Convention)
```
asset.<domain>.<sub_domain>.<specific_type>
域名: community | mall | school | hospital | logistics | datacenter | park | common
子域: 专业分类 (hvac, power, water, fire, security, transport, energy, env, process, it, medical, lab 等)
具体类型: snake_case, 单数名词, 英文简写优先
示例: asset.hospital.icu_monitor, asset.park.steam_boiler, asset.common.power.transformer
```

### 附录 B: 能力编码规范
```
cap.<domain>.<capability_name>
域名: common | hvac | lighting | energy | elevator | parking | retail | school | hospital | logistics | dc | park
能力名: snake_case, 动词/名词短语, 表达业务价值
示例: cap.hvac.cooling_optimize, cap.hospital.asset_tracking, cap.park.multi_energy_synergy
```

### 附录 C: 告警规则编码规范
```
ALM-<SCENE_ABBR>-<SEQ>
场景缩写: COM(通用) | COMM(社区) | MALL(商场) | SCH(学校) | HOS(医院) | LOG(物流) | DC(数据中心) | PARK(园区)
序号: 3位数字, 按专业域分组 (001-020 通用, 021-040 电气, 041-060 暖通, 061-080 消防, 081-100 安防, 101-120 环保, 121-140 专用)
示例: ALM-COMM-001, ALM-HOS-045, ALM-PARK-112
```

### 附录 D: SOP 编码规范
```
SOP-<SCENE_ABBR>-<SEQ>
场景缩写同告警规则
序号: 3位数字, 按业务流程分组 (001-020 通用运维, 021-040 应急响应, 041-060 专业作业, 061-080 合规检查, 081-100 变更管理)
示例: SOP-COM-001, SOP-HOS-023, SOP-PARK-041
```

### 附录 E: 术语表 (Glossary)

| 术语 | 定义 |
|------|------|
| **Asset Package** | 行业资产包: 面向特定垂直领域的 Schema+Template+Plugin 打包交付物 |
| **Zero-Code Deployment** | 零代码部署: 仅通过配置文件 (values.yaml) 完成全栈部署, 无需编写代码 |
| **Capability** | 能力: 可复用的业务/技术功能单元, 定义标准接口, 由适配器实现协议转换 |
| **Ontology** | 本体: 资产类型、属性、关系、约束的形式化定义, 统一语义模型 |
| **Digital Twin** | 数字孪生: 物理资产在数字空间的实时映射, 包含状态、行为、规则、仿真 |
| **PUE** | Power Usage Effectiveness: 数据中心总能耗 / IT设备能耗 |
| **DCV** | Demand Controlled Ventilation: 需求控制通风, 基于 CO2/人数调节新风量 |
| **MPC** | Model Predictive Control: 模型预测控制, 基于预测模型的最优控制策略 |
| **RUL** | Remaining Useful Life: 剩余使用寿命预测 |
| **CEP** | Complex Event Processing: 复杂事件处理, 多流关联、模式匹配、时序分析 |
| **SLA/SLO/SLI** | 服务等级协议/目标/指标 |
| **MTTR/MTBF** | 平均修复时间/平均故障间隔时间 |

---

## 13. 签收确认

| 角色 | 姓名 | 签名 | 日期 | 备注 |
|------|------|------|------|------|
| **dt_manager (架构/项目)** | | | | 规格基线确认 |
| **dt_architect (平台架构师)** | | | | 技术可行性确认 |
| **dt_product (产品经理)** | | | | 业务覆盖度确认 |
| **dt_qa (质量负责人)** | | | | 验收标准确认 |
| **dt_ops (运维负责人)** | | | | 运维落地性确认 |
| **dt_security (安全合规)** | | | | 合规安全确认 |

---

## 14. 文档控制

- **版本**: v1.0
- **密级**: 内部机密
- **存储路径**: `dt-lite-v4/docs/architecture/asset-packages/smart-park/SPEC.md`
- **变更控制**: 任何修改需经 dt_manager 评审通过，Major 变更需架构评审会 (ARC) 批准

---

## 15. 下一步行动项

1. **确认规格基线** → 进入 Phase 2 并行开发 (7 场景小组同步启动)
2. **建立 Git 仓库分支策略** → `feat/task20-smart-park-asset-package` 从 `main@v4.18.0` 切出
3. **搭建 CI/CD 管道** → 集成上述 8 个质量门禁
4. **分配 7 个 Squad 责任人** → 明确交付节点、评审机制
5. **准备种子数据集** → 每场景 50-100 资产实例、历史遥测 30 天、告警记录、工单记录
6. **Day 14 Task 20 终评会筹备** → 演示环境、测试报告、用户手册、运维手册

---

**文档生成时间**: 2026-09-09 | **最后更新**: 2026-09-09 | **责任人**: dt_manager
