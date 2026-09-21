#!/bin/bash
# Staging 环境部署脚本
# 负责人：DevOps Team
# 截止：2026-09-21 22:00
# 环境：Staging (远程 K8s 集群)

set -euo pipefail

# === 配置 ===
ENV_NAME="staging"
NAMESPACE="dt-lite-staging"
RELEASE_NAME="dt-lite-smart-park-staging"
CHART_PATH="./deployment/helm/ai"
VALUES_FILE="./packages/smart-park/v1.0/helm/values-smart-park.yaml"
KUBECONFIG="${KUBECONFIG:-~/.kube/config-staging}"
LOG_FILE="/tmp/${RELEASE_NAME}-deploy-$(date +%Y%m%d-%H%M%S).log"

# === 颜色输出 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# === 前置检查 ===
check_prerequisites() {
    log "检查前置条件..."
    
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
        log_warn "提示：请确保 staging 集群的 kubeconfig 已配置"
        exit 1
    fi
    log_success "kubeconfig 已找到: $KUBECONFIG"
    
    # 检查集群连接
    if ! kubectl cluster-info --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_error "无法连接到 Staging 集群"
        exit 1
    fi
    log_success "Staging 集群连接正常"
    
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
    log_success "Namespace $NAMESPACE 创建成功"
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
    
    local install_cmd="helm install $RELEASE_NAME $CHART_PATH -n $NAMESPACE --create-namespace"
    
    # 添加自定义 values
    if [ -f "$VALUES_FILE" ]; then
        install_cmd="$install_cmd -f $VALUES_FILE"
        log "使用自定义 values 文件: $VALUES_FILE"
    fi
    
    # 启用依赖服务（Staging 环境）
    install_cmd="$install_cmd --set postgresql.enabled=true --set redis.enabled=true --set prometheus.enabled=true"
    
    # 设置副本数
    install_cmd="$install_cmd --set replicaCount=2"
    
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

# === 验证外部系统模拟器 ===
validate_external_simulators() {
    log "验证外部系统模拟器..."
    
    # BACnet 模拟器
    if kubectl get svc -n "$NAMESPACE" | grep -i bacnet &> /dev/null; then
        log_success "BACnet 模拟器已部署"
    else
        log_warn "BACnet 模拟器未部署（可选）"
    fi
    
    # Modbus 模拟器
    if kubectl get svc -n "$NAMESPACE" | grep -i modbus &> /dev/null; then
        log_success "Modbus 模拟器已部署"
    else
        log_warn "Modbus 模拟器未部署（可选）"
    fi
    
    # OPC UA 模拟器
    if kubectl get svc -n "$NAMESPACE" | grep -i opcua &> /dev/null; then
        log_success "OPC UA 模拟器已部署"
    else
        log_warn "OPC UA 模拟器未部署（可选）"
    fi
    
    # MQTT Broker
    if kubectl get svc -n "$NAMESPACE" | grep -i mqtt &> /dev/null; then
        log_success "MQTT Broker 已部署"
    else
        log_warn "MQTT Broker 未部署（可选）"
    fi
}

# === 生成部署报告 ===
generate_deploy_report() {
    log "生成部署报告..."
    
    local report_file="/tmp/${RELEASE_NAME}-deploy-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# $RELEASE_NAME Staging 环境部署报告

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
| Helm Release | ✅ | $RELEASE_NAME 已部署 |
| Pod 状态 | ✅ | 全部 Running |
| Helm Test | ✅ | Succeeded |
| Service Health | ✅ | 健康检查通过 |
| 外部模拟器 | ⏳ | 见下方详情 |

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

## 外部系统模拟器状态
\`\`\`
$(validate_external_simulators 2>&1)
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
    log "$RELEASE_NAME Staging 环境部署脚本"
    log "========================================"
    
    check_prerequisites
    create_namespace
    update_helm_dependencies
    deploy_helm_release
    wait_for_pods
    run_helm_test
    validate_service_health
    validate_external_simulators
    generate_deploy_report
    
    log "========================================"
    log_success "$RELEASE_NAME Staging 环境部署完成！"
    log "日志文件: $LOG_FILE"
    log "========================================"
}

# 执行主流程
main "$@"
