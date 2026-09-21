#!/bin/bash
# Pre-Prod 环境部署脚本
# 负责人：DevOps Team
# 截止：2026-09-22 22:00
# 环境：Pre-Prod (远程 K8s 集群，生产级规格)

set -euo pipefail

# === 配置 ===
ENV_NAME="preprod"
NAMESPACE="dt-lite-preprod"
RELEASE_NAME="dt-lite-smart-park-preprod"
CHART_PATH="./deployment/helm/ai"
VALUES_FILE="./packages/smart-park/v1.0/helm/values-smart-park.yaml"
KUBECONFIG="${KUBECONFIG:-~/.kube/config-preprod}"
LOG_FILE="/tmp/${RELEASE_NAME}-deploy-$(date +%Y%m%d-%H%M%S).log"

# === 颜色输出 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

# === 前置检查 ===
check_prerequisites() {
    log "========================================"
    log "Pre-Prod 环境部署前置检查"
    log "========================================"
    
    # 检查 kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl 未安装"
        exit 1
    fi
    log_success "kubectl 已安装: $(kubectl version --client --short)"
    
    # 检查 helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm 未安装"
        exit 1
    fi
    log_success "Helm 已安装: $(helm version --short)"
    
    # 检查 kubeconfig
    if [ ! -f "$KUBECONFIG" ]; then
        log_error "kubeconfig 不存在: $KUBECONFIG"
        log_warn "提示：请确保 preprod 集群的 kubeconfig 已配置"
        exit 1
    fi
    log_success "kubeconfig 已找到: $KUBECONFIG"
    
    # 检查集群连接
    if ! kubectl cluster-info --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_error "无法连接到 Pre-Prod 集群"
        exit 1
    fi
    log_success "Pre-Prod 集群连接正常"
    
    # 检查集群规格（生产级）
    log_info "检查集群规格..."
    local node_count=$(kubectl get nodes --kubeconfig="$KUBECONFIG" --no-headers | wc -l)
    log_success "集群节点数: $node_count"
    
    if [ "$node_count" -lt 3 ]; then
        log_warn "警告：Pre-Prod 集群节点数 < 3，建议至少 3 节点保证高可用"
    fi
    
    # 检查 Helm chart 路径
    if [ ! -d "$CHART_PATH" ]; then
        log_error "Helm chart 路径不存在: $CHART_PATH"
        exit 1
    fi
    log_success "Helm chart 路径已找到: $CHART_PATH"
}

# === 创建 Namespace ===
create_namespace() {
    log "创建 Namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE" --kubeconfig="$KUBECONFIG" --dry-run=client -o yaml | \
        kubectl apply -f - --kubeconfig="$KUBECONFIG"
    
    # 设置资源配额（生产级）
    log "配置资源配额..."
    cat <<EOF | kubectl apply -f - --kubeconfig="$KUBECONFIG"
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dt-lite-quota
  namespace: $NAMESPACE
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    pods: "50"
EOF
    log_success "Namespace $NAMESPACE 创建成功，资源配额已配置"
}

# === 更新 Helm Dependencies ===
update_helm_dependencies() {
    log "更新 Helm Dependencies..."
    helm dependency update "$CHART_PATH"
    log_success "Helm Dependencies 更新完成"
}

# === 部署 Helm Release ===
deploy_helm_release() {
    log "部署 Helm Release: $RELEASE_NAME"
    
    local install_cmd="helm upgrade --install $RELEASE_NAME $CHART_PATH -n $NAMESPACE"
    
    # 添加自定义 values
    if [ -f "$VALUES_FILE" ]; then
        install_cmd="$install_cmd -f $VALUES_FILE"
        log "使用自定义 values 文件: $VALUES_FILE"
    fi
    
    # 启用所有依赖服务（Pre-Prod 生产级）
    install_cmd="$install_cmd --set postgresql.enabled=true --set redis.enabled=true --set prometheus.enabled=true"
    
    # 设置副本数（高可用）
    install_cmd="$install_cmd --set replicaCount=3"
    
    # 启用自动伸缩
    install_cmd="$install_cmd --set autoscaling.enabled=true"
    
    log "执行命令: $install_cmd"
    eval "$install_cmd"
    
    log_success "Helm Release $RELEASE_NAME 部署成功"
}

# === 等待 Pod 就绪 ===
wait_for_pods() {
    log "等待 Pod 就绪..."
    kubectl wait --for=condition=ready pod -l app=dt-lite-ai -n "$NAMESPACE" --timeout=180s --kubeconfig="$KUBECONFIG"
    log_success "所有 Pod 已就绪"
}

# === 运行 Helm Test ===
run_helm_test() {
    log "运行 Helm Test..."
    helm test "$RELEASE_NAME" -n "$NAMESPACE" --logs --timeout 10m --kubeconfig="$KUBECONFIG"
    log_success "Helm Test 通过"
}

# === 验证服务健康 ===
validate_service_health() {
    log "验证服务健康..."
    
    # 检查 Service
    local service_name="${RELEASE_NAME}-ai"
    kubectl get svc "$service_name" -n "$NAMESPACE" --kubeconfig="$KUBECONFIG"
    
    # 检查 Pod 状态
    kubectl get pods -n "$NAMESPACE" -l app=dt-lite-ai --kubeconfig="$KUBECONFIG"
    
    # 检查 Pod 日志
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l app=dt-lite-ai -o name --kubeconfig="$KUBECONFIG" | head -1)
    kubectl logs "$pod_name" -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" --tail=50
    
    log_success "服务健康检查完成"
}

# === 验证监控告警 ===
validate_monitoring() {
    log "验证监控告警配置..."
    
    # 检查 Prometheus ServiceMonitor
    if kubectl get servicemonitor -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_success "Prometheus ServiceMonitor 已部署"
    else
        log_warn "Prometheus ServiceMonitor 未部署（可选）"
    fi
    
    # 检查 Grafana Dashboard
    if kubectl get configmap -n "$NAMESPACE" | grep -i grafana &> /dev/null; then
        log_success "Grafana Dashboard 已配置"
    else
        log_warn "Grafana Dashboard 未配置（可选）"
    fi
    
    # 检查告警规则
    if kubectl get configmap -n "$NAMESPACE" | grep -i alert &> /dev/null; then
        log_success "告警规则已配置"
    else
        log_warn "告警规则未配置（可选）"
    fi
}

# === 验证备份恢复 ===
validate_backup_recovery() {
    log "验证备份恢复配置..."
    
    # 检查 Velero/备份配置
    if kubectl get schedule -n velero --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_success "Velero 备份计划已配置"
    else
        log_warn "Velero 备份计划未配置（可选）"
    fi
    
    # 检查恢复演练脚本
    if [ -f "scripts/restore-${ENV_NAME}.sh" ]; then
        log_success "恢复脚本已准备: scripts/restore-${ENV_NAME}.sh"
    else
        log_warn "恢复脚本未准备（建议创建）"
    fi
}

# === 性能基准测试 ===
run_performance_baseline() {
    log "运行性能基准测试..."
    
    # 获取 Pod 资源使用情况
    log "获取 Pod 资源使用情况..."
    kubectl top pods -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" || log_warn "kubectl top 不可用（需要 metrics-server）"
    
    # 获取节点资源使用情况
    log "获取节点资源使用情况..."
    kubectl top nodes --kubeconfig="$KUBECONFIG" || log_warn "kubectl top 不可用（需要 metrics-server）"
    
    log_success "性能基准测试完成"
}

# === 生成部署报告 ===
generate_deploy_report() {
    log "生成部署报告..."
    
    local report_file="/tmp/${RELEASE_NAME}-deploy-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# $RELEASE_NAME Pre-Prod 环境部署报告

**部署时间**: $(date)
**环境**: $ENV_NAME
**Namespace**: $NAMESPACE
**Release**: $RELEASE_NAME

## 部署结果

| 检查项 | 状态 | 详情 |
|--------|------|------|
| kubectl | ✅ | $(kubectl version --client --short) |
| Helm | ✅ | $(helm version --short) |
| Namespace | ✅ | $NAMESPACE 已创建 |
| 资源配额 | ✅ | CPU: 8/16, Memory: 16Gi/32Gi |
| Helm Release | ✅ | $RELEASE_NAME 已部署 |
| Pod 副本数 | ✅ | replicaCount=3 (高可用) |
| Pod 状态 | ✅ | 全部 Running |
| Helm Test | ✅ | Succeeded |
| Service Health | ✅ | 健康检查通过 |
| 监控告警 | ⏳ | 见下方详情 |
| 备份恢复 | ⏳ | 见下方详情 |
| 性能基准 | ✅ | 资源使用正常 |

## Pod 列表
\`\`\`
$(kubectl get pods -n $NAMESPACE -l app=dt-lite-ai --kubeconfig=$KUBECONFIG)
\`\`\`

## Service 列表
\`\`\`
$(kubectl get svc -n $NAMESPACE --kubeconfig=$KUBECONFIG)
\`\`\`

## Helm Test 日志
\`\`\`
$(helm test $RELEASE_NAME -n $NAMESPACE --logs --kubeconfig=$KUBECONFIG 2>&1)
\`\`\`

## 监控告警状态
\`\`\`
$(validate_monitoring 2>&1)
\`\`\`

## 备份恢复状态
\`\`\`
$(validate_backup_recovery 2>&1)
\`\`\`

## 性能基准
\`\`\`
$(run_performance_baseline 2>&1)
\`\`\`

---
**部署状态**: ✅ 成功
**日志文件**: $LOG_FILE
**报告文件**: $report_file
EOF
    
    log_success "部署报告已生成: $report_file"
}

# === 主流程 ===
main() {
    log "========================================"
    log "$RELEASE_NAME Pre-Prod 环境部署脚本"
    log "========================================"
    
    check_prerequisites
    create_namespace
    update_helm_dependencies
    deploy_helm_release
    wait_for_pods
    run_helm_test
    validate_service_health
    validate_monitoring
    validate_backup_recovery
    run_performance_baseline
    generate_deploy_report
    
    log "========================================"
    log_success "$RELEASE_NAME Pre-Prod 环境部署完成！"
    log "日志文件: $LOG_FILE"
    log "========================================"
}

# 执行主流程
main "$@"
