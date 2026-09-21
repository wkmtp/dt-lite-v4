"""
Preset Workflow Templates for Common DT-Lite Operations.

Provides 10+ pre-built workflow templates for common use cases.
"""

from __future__ import annotations

from .dsl import (
    WorkflowDSL, NodeType, BaseNodeConfig, EdgeConfig, Variable,
    LLMNodeConfig, ToolNodeConfig, HTTPNodeConfig, ConditionNodeConfig,
    ParallelNodeConfig, HumanApprovalNodeConfig, SubWorkflowNodeConfig,
    StartNodeConfig, EndNodeConfig
)


def _make_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:03d}"


def _make_edge(source: str, target: str, index: int) -> EdgeConfig:
    return EdgeConfig(
        edge_id=f"edge-{index:03d}",
        source_node_id=source,
        target_node_id=target
    )


# ============================================================================
# TEMPLATE 1: Device Inspection
# ============================================================================
def template_device_inspection(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for automated device inspection.
    - Check device status
    - Collect metrics
    - Generate report
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["device_id"]
        ),
        ToolNodeConfig(
            node_id="check-status",
            node_type=NodeType.TOOL,
            label="Check Device Status",
            tool_name="device.get_status",
            tool_params={"device_id": "${inputs.device_id}"},
            output_variable="device_status"
        ),
        ToolNodeConfig(
            node_id="collect-metrics",
            node_type=NodeType.TOOL,
            label="Collect Metrics",
            tool_name="device.collect_metrics",
            tool_params={"device_id": "${inputs.device_id}"},
            output_variable="metrics"
        ),
        LLMNodeConfig(
            node_id="analyze",
            node_type=NodeType.LLM,
            label="Analyze Results",
            system_prompt="You are a device inspection analyst.",
            user_prompt="Analyze the device metrics and generate inspection report.\nStatus: ${device_status}\nMetrics: ${metrics}",
            output_variable="report"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["report"]
        )
    ]

    edges = [
        _make_edge("start", "check-status", 1),
        _make_edge("check-status", "collect-metrics", 2),
        _make_edge("collect-metrics", "analyze", 3),
        _make_edge("analyze", "end", 4)
    ]

    return WorkflowDSL(
        workflow_id="device-inspection",
        tenant_id=tenant_id,
        name="Device Inspection",
        description="Automated device inspection workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="device_id", scope="workflow"),
            Variable(name="device_status", scope="workflow"),
            Variable(name="metrics", scope="workflow"),
            Variable(name="report", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 2: Alarm Handling
# ============================================================================
def template_alarm_handling(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for automated alarm handling.
    - Detect alarm
    - Classify severity
    - Notify responders
    - Execute response
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["alarm_id"]
        ),
        ToolNodeConfig(
            node_id="fetch-alarm",
            node_type=NodeType.TOOL,
            label="Fetch Alarm Details",
            tool_name="alarm.get_details",
            tool_params={"alarm_id": "${inputs.alarm_id}"},
            output_variable="alarm"
        ),
        LLMNodeConfig(
            node_id="classify",
            node_type=NodeType.LLM,
            label="Classify Severity",
            system_prompt="Classify alarm severity.",
            user_prompt="Classify this alarm: ${alarm}",
            output_variable="severity"
        ),
        ConditionNodeConfig(
            node_id="check-severity",
            node_type=NodeType.CONDITION,
            label="Check Severity",
            expression="${severity} >= 'high'",
            true_node_id="notify-high",
            false_node_id="notify-low"
        ),
        ToolNodeConfig(
            node_id="notify-high",
            node_type=NodeType.TOOL,
            label="Notify High Priority",
            tool_name="notification.send",
            tool_params={"level": "high", "message": "${alarm}"},
            output_variable="notification_sent"
        ),
        ToolNodeConfig(
            node_id="notify-low",
            node_type=NodeType.TOOL,
            label="Notify Low Priority",
            tool_name="notification.send",
            tool_params={"level": "low", "message": "${alarm}"},
            output_variable="notification_sent"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["notification_sent"]
        )
    ]

    edges = [
        _make_edge("start", "fetch-alarm", 1),
        _make_edge("fetch-alarm", "classify", 2),
        _make_edge("classify", "check-severity", 3),
        _make_edge("check-severity", "notify-high", 4),
        _make_edge("check-severity", "notify-low", 5),
        _make_edge("notify-high", "end", 6),
        _make_edge("notify-low", "end", 7)
    ]

    return WorkflowDSL(
        workflow_id="alarm-handling",
        tenant_id=tenant_id,
        name="Alarm Handling",
        description="Automated alarm classification and notification",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="alarm_id", scope="workflow"),
            Variable(name="alarm", scope="workflow"),
            Variable(name="severity", scope="workflow"),
            Variable(name="notification_sent", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 3: Report Generation
# ============================================================================
def template_report_generation(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for generating comprehensive reports.
    - Collect data from multiple sources
    - Generate analysis
    - Compile report
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["report_type", "parameters"]
        ),
        ParallelNodeConfig(
            node_id="parallel-collect",
            node_type=NodeType.PARALLEL,
            label="Collect Data",
            parallel_nodes=["collect-telemetry", "collect-assets"]
        ),
        ToolNodeConfig(
            node_id="collect-telemetry",
            node_type=NodeType.TOOL,
            label="Collect Telemetry",
            tool_name="telemetry.get_data",
            tool_params={"params": "${inputs.parameters}"},
            output_variable="telemetry_data"
        ),
        ToolNodeConfig(
            node_id="collect-assets",
            node_type=NodeType.TOOL,
            label="Collect Assets",
            tool_name="asset.get_list",
            tool_params={"params": "${inputs.parameters}"},
            output_variable="asset_data"
        ),
        LLMNodeConfig(
            node_id="analyze",
            node_type=NodeType.LLM,
            label="Analyze Data",
            system_prompt="Analyze collected data for report.",
            user_prompt="Analyze telemetry and asset data for ${report_type} report.",
            output_variable="analysis"
        ),
        LLMNodeConfig(
            node_id="generate",
            node_type=NodeType.LLM,
            label="Generate Report",
            system_prompt="Generate comprehensive report.",
            user_prompt="Generate ${report_type} report from analysis.\n${analysis}",
            output_variable="report"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["report"]
        )
    ]

    edges = [
        _make_edge("start", "parallel-collect", 1),
        _make_edge("parallel-collect", "collect-telemetry", 2),
        _make_edge("parallel-collect", "collect-assets", 3),
        _make_edge("collect-telemetry", "analyze", 4),
        _make_edge("collect-assets", "analyze", 5),
        _make_edge("analyze", "generate", 6),
        _make_edge("generate", "end", 7)
    ]

    return WorkflowDSL(
        workflow_id="report-generation",
        tenant_id=tenant_id,
        name="Report Generation",
        description="Multi-source data collection and report generation",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="report_type", scope="workflow"),
            Variable(name="parameters", scope="workflow"),
            Variable(name="telemetry_data", scope="workflow"),
            Variable(name="asset_data", scope="workflow"),
            Variable(name="analysis", scope="workflow"),
            Variable(name="report", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 4: Energy Analysis
# ============================================================================
def template_energy_analysis(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for energy consumption analysis.
    - Fetch energy data
    - Analyze patterns
    - Generate recommendations
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["building_id", "period"]
        ),
        HTTPNodeConfig(
            node_id="fetch-energy",
            node_type=NodeType.HTTP,
            label="Fetch Energy Data",
            method="GET",
            url="/api/energy/consumption",
            headers={"X-Building-ID": "${inputs.building_id}"},
            response_variable="energy_data"
        ),
        LLMNodeConfig(
            node_id="analyze",
            node_type=NodeType.LLM,
            label="Analyze Consumption",
            system_prompt="Energy consumption analyst.",
            user_prompt="Analyze energy consumption patterns.\nData: ${energy_data}\nPeriod: ${inputs.period}",
            output_variable="analysis"
        ),
        LLMNodeConfig(
            node_id="recommend",
            node_type=NodeType.LLM,
            label="Generate Recommendations",
            system_prompt="Energy efficiency consultant.",
            user_prompt="Generate energy efficiency recommendations.\n${analysis}",
            output_variable="recommendations"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["recommendations"]
        )
    ]

    edges = [
        _make_edge("start", "fetch-energy", 1),
        _make_edge("fetch-energy", "analyze", 2),
        _make_edge("analyze", "recommend", 3),
        _make_edge("recommend", "end", 4)
    ]

    return WorkflowDSL(
        workflow_id="energy-analysis",
        tenant_id=tenant_id,
        name="Energy Analysis",
        description="Energy consumption analysis and recommendations",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="building_id", scope="workflow"),
            Variable(name="period", scope="workflow"),
            Variable(name="energy_data", scope="workflow"),
            Variable(name="analysis", scope="workflow"),
            Variable(name="recommendations", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 5: Asset Inventory
# ============================================================================
def template_asset_inventory(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for asset inventory management.
    - Scan assets
    - Verify inventory
    - Generate discrepancies
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["location_id"]
        ),
        ToolNodeConfig(
            node_id="scan",
            node_type=NodeType.TOOL,
            label="Scan Assets",
            tool_name="inventory.scan",
            tool_params={"location_id": "${inputs.location_id}"},
            output_variable="scanned_assets"
        ),
        ToolNodeConfig(
            node_id="fetch-records",
            node_type=NodeType.TOOL,
            label="Fetch Records",
            tool_name="inventory.get_records",
            tool_params={"location_id": "${inputs.location_id}"},
            output_variable="recorded_assets"
        ),
        LLMNodeConfig(
            node_id="compare",
            node_type=NodeType.LLM,
            label="Compare Inventory",
            system_prompt="Inventory analyst.",
            user_prompt="Compare scanned and recorded assets.\nScanned: ${scanned_assets}\nRecorded: ${recorded_assets}",
            output_variable="discrepancies"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["discrepancies"]
        )
    ]

    edges = [
        _make_edge("start", "scan", 1),
        _make_edge("start", "fetch-records", 2),
        _make_edge("scan", "compare", 3),
        _make_edge("fetch-records", "compare", 4),
        _make_edge("compare", "end", 5)
    ]

    return WorkflowDSL(
        workflow_id="asset-inventory",
        tenant_id=tenant_id,
        name="Asset Inventory",
        description="Automated asset inventory verification",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="location_id", scope="workflow"),
            Variable(name="scanned_assets", scope="workflow"),
            Variable(name="recorded_assets", scope="workflow"),
            Variable(name="discrepancies", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 6: Incident Response
# ============================================================================
def template_incident_response(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for incident response.
    - Detect incident
    - Assess impact
    - Execute response plan
    - Notify stakeholders
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["incident_id"]
        ),
        ToolNodeConfig(
            node_id="assess",
            node_type=NodeType.TOOL,
            label="Assess Incident",
            tool_name="incident.assess",
            tool_params={"incident_id": "${inputs.incident_id}"},
            output_variable="assessment"
        ),
        LLMNodeConfig(
            node_id="plan",
            node_type=NodeType.LLM,
            label="Generate Response Plan",
            system_prompt="Incident response planner.",
            user_prompt="Generate response plan for: ${assessment}",
            output_variable="response_plan"
        ),
        ParallelNodeConfig(
            node_id="parallel-execute",
            node_type=NodeType.PARALLEL,
            label="Execute Response",
            parallel_nodes=["execute-action-1", "execute-action-2"]
        ),
        ToolNodeConfig(
            node_id="execute-action-1",
            node_type=NodeType.TOOL,
            label="Execute Action 1",
            tool_name="response.execute",
            tool_params={"action": "isolate"},
            output_variable="action1_result"
        ),
        ToolNodeConfig(
            node_id="execute-action-2",
            node_type=NodeType.TOOL,
            label="Execute Action 2",
            tool_name="response.execute",
            tool_params={"action": "notify"},
            output_variable="action2_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["action1_result", "action2_result"]
        )
    ]

    edges = [
        _make_edge("start", "assess", 1),
        _make_edge("assess", "plan", 2),
        _make_edge("plan", "parallel-execute", 3),
        _make_edge("parallel-execute", "execute-action-1", 4),
        _make_edge("parallel-execute", "execute-action-2", 5),
        _make_edge("execute-action-1", "end", 6),
        _make_edge("execute-action-2", "end", 7)
    ]

    return WorkflowDSL(
        workflow_id="incident-response",
        tenant_id=tenant_id,
        name="Incident Response",
        description="Automated incident response workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="incident_id", scope="workflow"),
            Variable(name="assessment", scope="workflow"),
            Variable(name="response_plan", scope="workflow"),
            Variable(name="action1_result", scope="workflow"),
            Variable(name="action2_result", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 7: Data Backup
# ============================================================================
def template_data_backup(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for automated data backup.
    - Validate backup scope
    - Execute backup
    - Verify integrity
    - Notify completion
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["backup_scope"]
        ),
        ConditionNodeConfig(
            node_id="validate",
            node_type=NodeType.CONDITION,
            label="Validate Scope",
            expression="len(${inputs.backup_scope}) > 0",
            true_node_id="backup",
            false_node_id="error-end"
        ),
        ToolNodeConfig(
            node_id="backup",
            node_type=NodeType.TOOL,
            label="Execute Backup",
            tool_name="backup.execute",
            tool_params={"scope": "${inputs.backup_scope}"},
            output_variable="backup_result"
        ),
        ToolNodeConfig(
            node_id="verify",
            node_type=NodeType.TOOL,
            label="Verify Integrity",
            tool_name="backup.verify",
            tool_params={"backup_id": "${backup_result.backup_id}"},
            output_variable="verification_result"
        ),
        ToolNodeConfig(
            node_id="notify",
            node_type=NodeType.TOOL,
            label="Notify Completion",
            tool_name="notification.send",
            tool_params={"message": "Backup completed successfully"},
            output_variable="notification_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["verification_result", "notification_result"]
        ),
        EndNodeConfig(
            node_id="error-end",
            node_type=NodeType.END,
            label="Error End",
            outputs=[]
        )
    ]

    edges = [
        _make_edge("start", "validate", 1),
        _make_edge("validate", "backup", 2),
        _make_edge("validate", "error-end", 3),
        _make_edge("backup", "verify", 4),
        _make_edge("verify", "notify", 5),
        _make_edge("notify", "end", 6)
    ]

    return WorkflowDSL(
        workflow_id="data-backup",
        tenant_id=tenant_id,
        name="Data Backup",
        description="Automated data backup with verification",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="backup_scope", scope="workflow"),
            Variable(name="backup_result", scope="workflow"),
            Variable(name="verification_result", scope="workflow"),
            Variable(name="notification_result", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 8: Device Provisioning
# ============================================================================
def template_device_provisioning(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for device provisioning.
    - Validate request
    - Configure device
    - Test connectivity
    - Register in system
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["device_specs"]
        ),
        ToolNodeConfig(
            node_id="validate",
            node_type=NodeType.TOOL,
            label="Validate Specs",
            tool_name="device.validate_specs",
            tool_params={"specs": "${inputs.device_specs}"},
            output_variable="validation_result"
        ),
        ConditionNodeConfig(
            node_id="check-validation",
            node_type=NodeType.CONDITION,
            label="Check Validation",
            expression="${validation_result.valid}",
            true_node_id="configure",
            false_node_id="reject-end"
        ),
        ToolNodeConfig(
            node_id="configure",
            node_type=NodeType.TOOL,
            label="Configure Device",
            tool_name="device.configure",
            tool_params={"specs": "${inputs.device_specs}"},
            output_variable="config_result"
        ),
        ToolNodeConfig(
            node_id="test",
            node_type=NodeType.TOOL,
            label="Test Connectivity",
            tool_name="device.test_connectivity",
            tool_params={"device_id": "${config_result.device_id}"},
            output_variable="test_result"
        ),
        ToolNodeConfig(
            node_id="register",
            node_type=NodeType.TOOL,
            label="Register Device",
            tool_name="device.register",
            tool_params={"device_id": "${config_result.device_id}"},
            output_variable="register_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["register_result"]
        ),
        EndNodeConfig(
            node_id="reject-end",
            node_type=NodeType.END,
            label="Reject End",
            outputs=[]
        )
    ]

    edges = [
        _make_edge("start", "validate", 1),
        _make_edge("validate", "check-validation", 2),
        _make_edge("check-validation", "configure", 3),
        _make_edge("check-validation", "reject-end", 4),
        _make_edge("configure", "test", 5),
        _make_edge("test", "register", 6),
        _make_edge("register", "end", 7)
    ]

    return WorkflowDSL(
        workflow_id="device-provisioning",
        tenant_id=tenant_id,
        name="Device Provisioning",
        description="Automated device provisioning workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="device_specs", scope="workflow"),
            Variable(name="validation_result", scope="workflow"),
            Variable(name="config_result", scope="workflow"),
            Variable(name="test_result", scope="workflow"),
            Variable(name="register_result", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 9: Compliance Check
# ============================================================================
def template_compliance_check(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for compliance checking.
    - Collect compliance data
    - Evaluate rules
    - Generate compliance report
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["compliance_domain"]
        ),
        ParallelNodeConfig(
            node_id="parallel-collect",
            node_type=NodeType.PARALLEL,
            label="Collect Data",
            parallel_nodes=["collect-policy", "collect-evidence"]
        ),
        ToolNodeConfig(
            node_id="collect-policy",
            node_type=NodeType.TOOL,
            label="Collect Policy",
            tool_name="compliance.get_policy",
            tool_params={"domain": "${inputs.compliance_domain}"},
            output_variable="policy"
        ),
        ToolNodeConfig(
            node_id="collect-evidence",
            node_type=NodeType.TOOL,
            label="Collect Evidence",
            tool_name="compliance.get_evidence",
            tool_params={"domain": "${inputs.compliance_domain}"},
            output_variable="evidence"
        ),
        LLMNodeConfig(
            node_id="evaluate",
            node_type=NodeType.LLM,
            label="Evaluate Compliance",
            system_prompt="Compliance evaluator.",
            user_prompt="Evaluate compliance against policy.\nPolicy: ${policy}\nEvidence: ${evidence}",
            output_variable="evaluation"
        ),
        LLMNodeConfig(
            node_id="report",
            node_type=NodeType.LLM,
            label="Generate Report",
            system_prompt="Generate compliance report.",
            user_prompt="Generate compliance report.\n${evaluation}",
            output_variable="report"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["report"]
        )
    ]

    edges = [
        _make_edge("start", "parallel-collect", 1),
        _make_edge("parallel-collect", "collect-policy", 2),
        _make_edge("parallel-collect", "collect-evidence", 3),
        _make_edge("collect-policy", "evaluate", 4),
        _make_edge("collect-evidence", "evaluate", 5),
        _make_edge("evaluate", "report", 6),
        _make_edge("report", "end", 7)
    ]

    return WorkflowDSL(
        workflow_id="compliance-check",
        tenant_id=tenant_id,
        name="Compliance Check",
        description="Automated compliance checking workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="compliance_domain", scope="workflow"),
            Variable(name="policy", scope="workflow"),
            Variable(name="evidence", scope="workflow"),
            Variable(name="evaluation", scope="workflow"),
            Variable(name="report", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 10: Maintenance Scheduling
# ============================================================================
def template_maintenance_scheduling(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for maintenance scheduling.
    - Check maintenance requirements
    - Schedule maintenance
    - Notify stakeholders
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["asset_id"]
        ),
        ToolNodeConfig(
            node_id="check-requirements",
            node_type=NodeType.TOOL,
            label="Check Requirements",
            tool_name="maintenance.check_requirements",
            tool_params={"asset_id": "${inputs.asset_id}"},
            output_variable="requirements"
        ),
        ConditionNodeConfig(
            node_id="check-maintenance",
            node_type=NodeType.CONDITION,
            label="Check Need",
            expression="${requirements.need_maintenance}",
            true_node_id="schedule",
            false_node_id="skip-end"
        ),
        ToolNodeConfig(
            node_id="schedule",
            node_type=NodeType.TOOL,
            label="Schedule Maintenance",
            tool_name="maintenance.schedule",
            tool_params={"requirements": "${requirements}"},
            output_variable="schedule_result"
        ),
        ToolNodeConfig(
            node_id="notify",
            node_type=NodeType.TOOL,
            label="Notify Stakeholders",
            tool_name="notification.send",
            tool_params={"message": f"Maintenance scheduled for {inputs.asset_id}"},
            output_variable="notification_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["schedule_result", "notification_result"]
        ),
        EndNodeConfig(
            node_id="skip-end",
            node_type=NodeType.END,
            label="Skip End",
            outputs=[]
        )
    ]

    edges = [
        _make_edge("start", "check-requirements", 1),
        _make_edge("check-requirements", "check-maintenance", 2),
        _make_edge("check-maintenance", "schedule", 3),
        _make_edge("check-maintenance", "skip-end", 4),
        _make_edge("schedule", "notify", 5),
        _make_edge("notify", "end", 6)
    ]

    return WorkflowDSL(
        workflow_id="maintenance-scheduling",
        tenant_id=tenant_id,
        name="Maintenance Scheduling",
        description="Automated maintenance scheduling workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="asset_id", scope="workflow"),
            Variable(name="requirements", scope="workflow"),
            Variable(name="schedule_result", scope="workflow"),
            Variable(name="notification_result", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 11: Anomaly Detection
# ============================================================================
def template_anomaly_detection(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for anomaly detection.
    - Collect data
    - Analyze patterns
    - Detect anomalies
    - Generate alerts
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["data_source", "time_range"]
        ),
        ToolNodeConfig(
            node_id="collect",
            node_type=NodeType.TOOL,
            label="Collect Data",
            tool_name="data.collect",
            tool_params={"source": "${inputs.data_source}", "range": "${inputs.time_range}"},
            output_variable="data"
        ),
        LLMNodeConfig(
            node_id="analyze",
            node_type=NodeType.LLM,
            label="Analyze Patterns",
            system_prompt="Anomaly detection analyst.",
            user_prompt="Analyze data for anomalies.\nData: ${data}",
            output_variable="analysis"
        ),
        ConditionNodeConfig(
            node_id="check-anomaly",
            node_type=NodeType.CONDITION,
            label="Check Anomaly",
            expression="${analysis.has_anomaly}",
            true_node_id="alert",
            false_node_id="log-end"
        ),
        ToolNodeConfig(
            node_id="alert",
            node_type=NodeType.TOOL,
            label="Generate Alert",
            tool_name="alert.create",
            tool_params={"analysis": "${analysis}"},
            output_variable="alert_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["alert_result"]
        ),
        EndNodeConfig(
            node_id="log-end",
            node_type=NodeType.END,
            label="Log End",
            outputs=[]
        )
    ]

    edges = [
        _make_edge("start", "collect", 1),
        _make_edge("collect", "analyze", 2),
        _make_edge("analyze", "check-anomaly", 3),
        _make_edge("check-anomaly", "alert", 4),
        _make_edge("check-anomaly", "log-end", 5),
        _make_edge("alert", "end", 6)
    ]

    return WorkflowDSL(
        workflow_id="anomaly-detection",
        tenant_id=tenant_id,
        name="Anomaly Detection",
        description="Automated anomaly detection workflow",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="data_source", scope="workflow"),
            Variable(name="time_range", scope="workflow"),
            Variable(name="data", scope="workflow"),
            Variable(name="analysis", scope="workflow"),
            Variable(name="alert_result", scope="workflow")
        ]
    )


# ============================================================================
# TEMPLATE 12: Asset Lifecycle Management
# ============================================================================
def template_asset_lifecycle(tenant_id: str) -> WorkflowDSL:
    """
    Workflow for asset lifecycle management.
    - Track asset status
    - Update records
    - Generate lifecycle report
    """
    nodes = [
        StartNodeConfig(
            node_id="start",
            node_type=NodeType.START,
            label="Start",
            inputs=["asset_id", "lifecycle_stage"]
        ),
        ToolNodeConfig(
            node_id="track",
            node_type=NodeType.TOOL,
            label="Track Status",
            tool_name="asset.track",
            tool_params={"asset_id": "${inputs.asset_id}"},
            output_variable="status"
        ),
        LLMNodeConfig(
            node_id="predict",
            node_type=NodeType.LLM,
            label="Predict Lifecycle",
            system_prompt="Asset lifecycle predictor.",
            user_prompt="Predict next lifecycle stage.\nCurrent: ${status}",
            output_variable="prediction"
        ),
        ToolNodeConfig(
            node_id="update",
            node_type=NodeType.TOOL,
            label="Update Records",
            tool_name="asset.update",
            tool_params={"asset_id": "${inputs.asset_id}", "stage": "${prediction.next_stage}"},
            output_variable="update_result"
        ),
        EndNodeConfig(
            node_id="end",
            node_type=NodeType.END,
            label="End",
            outputs=["update_result"]
        )
    ]

    edges = [
        _make_edge("start", "track", 1),
        _make_edge("track", "predict", 2),
        _make_edge("predict", "update", 3),
        _make_edge("update", "end", 4)
    ]

    return WorkflowDSL(
        workflow_id="asset-lifecycle",
        tenant_id=tenant_id,
        name="Asset Lifecycle Management",
        description="Asset lifecycle tracking and prediction",
        nodes=nodes,
        edges=edges,
        variables=[
            Variable(name="asset_id", scope="workflow"),
            Variable(name="lifecycle_stage", scope="workflow"),
            Variable(name="status", scope="workflow"),
            Variable(name="prediction", scope="workflow"),
            Variable(name="update_result", scope="workflow")
        ]
    )


# ============================================================================
# Template Registry
# ============================================================================
PRESET_TEMPLATES: dict[str, callable] = {
    "device-inspection": template_device_inspection,
    "alarm-handling": template_alarm_handling,
    "report-generation": template_report_generation,
    "energy-analysis": template_energy_analysis,
    "asset-inventory": template_asset_inventory,
    "incident-response": template_incident_response,
    "data-backup": template_data_backup,
    "device-provisioning": template_device_provisioning,
    "compliance-check": template_compliance_check,
    "maintenance-scheduling": template_maintenance_scheduling,
    "anomaly-detection": template_anomaly_detection,
    "asset-lifecycle": template_asset_lifecycle,
}


def get_template(name: str, tenant_id: str) -> Optional[WorkflowDSL]:
    """Get a preset template by name."""
    factory = PRESET_TEMPLATES.get(name)
    if factory:
        return factory(tenant_id)
    return None
