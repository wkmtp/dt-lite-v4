"""Task 18 CP1 — 四泳道接口契约草案"""
from __future__ import annotations

# =============================================================================
# 泳道 A: Edge Runtime Core (services/edge/)
# =============================================================================

class EdgeNodeAPI:
    """
    Edge Node 生命周期管理 API
    """

    # --- 注册与认证 ---
    PROVISIONING_TOKEN = """
    POST /api/v1/edge/provision
    Body: { "token": str, "node_id": str, "tenant_id": str }
    Response: { "node_id": str, "config": dict, "expires_at": str }
    """

    HEARTBEAT = """
    POST /api/v1/edge/heartbeat
    Body: { "node_id": str, "status": str, "resources": dict }
    Response: { "ack": bool, "next_heartbeat_ms": int }
    """

    # --- 健康检查 ---
    HEALTH = """
    GET /health
    Response: { "status": "ok", "uptime_s": float, "components": dict }
    """

    # --- 配置管理 ---
    GET_CONFIG = """
    GET /api/v1/edge/config
    Response: { "config": dict, "version": str }
    """

    PUT_CONFIG = """
    PUT /api/v1/edge/config
    Body: { "config": dict }
    Response: { "ack": bool, "version": str }
    """

    # --- 资源配额 ---
    GET_QUOTA = """
    GET /api/v1/edge/quota
    Response: { "cpu_limit": str, "memory_limit": str, "disk_limit": str }
    """

    GET_USAGE = """
    GET /api/v1/edge/usage
    Response: { "cpu_pct": float, "memory_bytes": int, "disk_bytes": int }
    """


# =============================================================================
# 泳道 B: Sync Engine (services/sync/)
# =============================================================================

class SyncEngineAPI:
    """
    双向同步引擎 API
    """

    # --- 连接建立 ---
    WS_CONNECT = """
    WS /api/v1/sync/ws?token=<provision_token>
    Events:
      - open: { "node_id": str, "session_id": str }
      - close: { "code": int, "reason": str }
    """

    # --- 数据上报 ---
    UPLOAD_TELEROMETRY = """
    WS Message: { "type": "telemetry", "data": list[TelemetryPoint] }
    Ack: { "seq": int, "accepted": int, "rejected": int }
    """

    UPLOAD_COMMANDS = """
    WS Message: { "type": "commands", "data": list[Command] }
    Ack: { "seq": int, "applied": int }
    """

    # --- 配置同步 ---
    SYNC_CONFIG = """
    WS Message: { "type": "config_sync", "version": str }
    Response: { "diff": dict, "applied": bool }
    """

    # --- 冲突解决 ---
    GET_CONFLICTS = """
    GET /api/v1/sync/conflicts
    Response: { "conflicts": list[Conflict], "cursor": str }
    """

    RESOLVE_CONFLICT = """
    POST /api/v1/sync/conflicts/{conflict_id}/resolve
    Body: { "strategy": "lww|merge|manual" }
    Response: { "resolved": bool }
    """


# =============================================================================
# 泳道 C: Local Persistence & Compute (services/edge/storage/, compute/)
# =============================================================================

class LocalStorageAPI:
    """
    本地存储 API
    """

    # --- 遥测写入 ---
    WRITE_POINTS = """
    POST /api/v1/storage/telemetry/batch
    Body: { "points": list[TelemetryPoint] }
    Response: { "accepted": int, "rejected": int, "seq": int }
    """

    # --- 遥测查询 ---
    QUERY_POINTS = """
    POST /api/v1/storage/telemetry/query
    Body: { "asset_id": str, "property_code": str, "start": str, "end": str, "aggregate": str }
    Response: { "points": list[dict], "total": int }
    """

    # --- 本地规则 ---
    LIST_RULES = """
    GET /api/v1/storage/rules
    Response: { "rules": list[Rule] }
    """

    EXECUTE_RULE = """
    POST /api/v1/storage/rules/{rule_id}/execute
    Response: { "result": dict, "duration_ms": float }
    """


class EdgeComputeAPI:
    """
    边缘推理 API
    """

    # --- 模型管理 ---
    LIST_MODELS = """
    GET /api/v1/compute/models
    Response: { "models": list[ModelInfo] }
    """

    LOAD_MODEL = """
    POST /api/v1/compute/models/load
    Body: { "model_id": str, "path": str, "quantization": str }
    Response: { "loaded": bool, "latency_ms": float }
    """

    # --- 推理 ---
    PREDICT = """
    POST /api/v1/compute/predict
    Body: { "model_id": str, "input": dict }
    Response: { "prediction": dict, "latency_ms": float, "confidence": float }
    """


# =============================================================================
# 泳道 D: Edge Adapter Pack (services/adapter/edge/)
# =============================================================================

class EdgeAdapterAPI:
    """
    边缘适配器 API
    """

    # --- 适配器管理 ---
    LIST_ADAPTERS = """
    GET /api/v1/edge/adapters
    Response: { "adapters": list[AdapterInfo] }
    """

    REGISTER_ADAPTER = """
    POST /api/v1/edge/adapters/register
    Body: { "type": str, "config": dict }
    Response: { "adapter_id": str, "status": str }
    """

    # --- 数据采集 ---
    COLLECT_DATA = """
    POST /api/v1/edge/adapters/{adapter_id}/collect
    Body: { "points": list[NormalizedTelemetry] }
    Response: { "accepted": int, "queued": int }
    """

    # --- 本地 MQTT Broker ---
    MQTT_PUBLISH = """
    POST /api/v1/edge/mqtt/publish
    Body: { "topic": str, "payload": str, "qos": int }
    Response: { "msg_id": str }
    """

    MQTT_SUBSCRIBE = """
    POST /api/v1/edge/mqtt/subscribe
    Body: { "topic": str, "qos": int }
    Response: { "subscription_id": str }
    """


# =============================================================================
# 共享数据模型
# =============================================================================

class SharedModels:
    """
    四泳道共享的数据模型定义
    """

    TELEMETRY_POINT = """
    {
      "asset_id": str (UUID),
      "property_code": str,
      "timestamp": str (ISO-8601),
      "value": float,
      "data_type": str ("INT32"|"FLOAT"|"BOOLEAN"|"STRING"),
      "unit": str,
      "quality": str ("GOOD"|"UNCERTAIN"|"BAD"),
      "source_adapter": str,
      "metadata": dict
    }
    """

    HLC_TIMESTAMP = """
    Hybrid Logical Clock:
    {
      "physical_ts": int (nanoseconds),
      "logical_counter": int,
      "node_id": str
    }
    """

    CONFLICT = """
    {
      "key": str,
      "cloud_value": any,
      "edge_value": any,
      "cloud_hlc": HLC_TIMESTAMP,
      "edge_hlc": HLC_TIMESTAMP,
      "strategy": str ("lww"|"merge"|"manual")
    }
    """

    OTA_PACKAGE = """
    {
      "package_id": str,
      "version": str,
      "checksum_blake3": str,
      "signature_ed25519": str,
      "size_bytes": int,
      "changelog": str
    }
    """
