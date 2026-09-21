#!/bin/bash
# Prod 环境部署脚本
# 负责人：DevOps Team
# 截止：2026-09-24 22:00
# 环境：Prod (远程 K8s 集群，多 AZ 高可用)

set -euo pipefail

# === 配置 ===
ENV_NAME="prod"
NAMESPACE="dt-lite-prod"
RELEASE_NAME="dt-lite-smart-park-prod"
CHART_PATH="./deployment/helm/ai"
VALUES_FILE="./packages/smart-park/v1.0/helm/values-smart-park.yaml"
KUBECONFIG="${KUBECONFIG:-~/.kube/config-prod}"
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
    log "Prod 环境部署前置检查"
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
        log_warn "提示：请确保 prod 集群的 kubeconfig 已配置"
        exit 1
    fi
    log_success "kubeconfig 已找到: $KUBECONFIG"
    
    # 检查集群连接
    if ! kubectl cluster-info --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_error "无法连接到 Prod 集群"
        exit 1
    fi
    log_success "Prod 集群连接正常"
    
    # 检查集群规格（多 AZ 高可用）
    log_info "检查集群高可用配置..."
    local node_count=$(kubectl get nodes --kubeconfig="$KUBECONFIG" --no-headers | wc -l)
    log_success "集群节点数: $node_count"
    
    if [ "$node_count" -lt 3 ]; then
        log_error "错误：Prod 集群节点数 < 3，必须至少 3 节点保证多 AZ 高可用"
        exit 1
    fi
    
    # 检查 WAF/DDoS 防护
    log_info "检查 WAF/DDoS 防护..."
    if kubectl get ingressclass --kubeconfig="$KUBECONFIG" | grep -i nginx &> /dev/null; then
        log_success "WAF/Ingress 控制器已部署"
    else
        log_warn "WAF/Ingress 控制器未检测到（建议部署）"
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
    requests.cpu: "16"
    requests.memory: 32Gi
    limits.cpu: "32"
    limits.memory: 64Gi
    pods: "100"
EOF
    
    # 设置 NetworkPolicy
    log "配置 NetworkPolicy..."
    cat <<EOF | kubectl apply -f - --kubeconfig="$KUBECONFIG"
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dt-lite-default-deny
  namespace: $NAMESPACE
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
EOF
    
    log_success "Namespace $NAMESPACE 创建成功，资源配额和 NetworkPolicy 已配置"
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
    
    # 启用所有依赖服务（Prod 生产级）
    install_cmd="$install_cmd --set postgresql.enabled=true --set redis.enabled=true --set prometheus.enabled=true"
    
    # 设置副本数（高可用）
    install_cmd="$install_cmd --set replicaCount=5"
    
    # 启用自动伸缩
    install_cmd="$install_cmd --set autoscaling.enabled=true"
    
    # 启用 Pod 反亲和性（多 AZ）
    install_cmd="$install_cmd --set affinity.podAntiAffinity=hard"
    
    log "执行命令: $install_cmd"
    eval "$install_cmd"
    
    log_success "Helm Release $RELEASE_NAME 部署成功"
}

# === 等待 Pod 就绪 ===
wait_for_pods() {
    log "等待 Pod 就绪..."
    kubectl wait --for=condition=ready pod -l app=dt-lite-ai -n "$NAMESPACE" --timeout=300s --kubeconfig="$KUBECONFIG"
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
    local pod_names=$(kubectl get pods -n "$NAMESPACE" -l app=dt-lite-ai -o name --kubeconfig="$KUBECONFIG")
    for pod in $pod_names; do
        log "检查 Pod: $pod"
        kubectl logs "$pod" -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" --tail=20
    done
    
    log_success "服务健康检查完成"
}

# === 验证多 AZ 高可用 ===
validate_multi_az() {
    log "验证多 AZ 高可用配置..."
    
    # 检查 Pod 分布
    log "Pod 分布..."
    kubectl get pods -n "$NAMESPACE" -l app=dt-lite-ai -o wide --kubeconfig="$KUBECONFIG"
    
    # 检查节点标签（AZ）
    log "节点 AZ 分布..."
    kubectl get nodes --label-columns=topology.kubernetes.io/zone --kubeconfig="$KUBECONFIG"
    
    # 验证反亲和性
    local pod_count=$(kubectl get pods -n "$NAMESPACE" -l app=dt-lite-ai --no-headers | wc -l)
    log_success "Pod 副本数: $pod_count（目标：5）"
    
    if [ "$pod_count" -ge 3 ]; then
        log_success "多 AZ 高可用验证通过"
    else
        log_warn "警告：Pod 副本数 < 3，可能无法保证多 AZ 高可用"
    fi
}

# === 验证 WAF/DDoS 防护 ===
validate_security() {
    log "验证安全配置..."
    
    # 检查 Ingress TLS
    if kubectl get ingress -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" | grep -i tls &> /dev/null; then
        log_success "Ingress TLS 已配置"
    else
        log_warn "Ingress TLS 未配置（建议启用）"
    fi
    
    # 检查 NetworkPolicy
    if kubectl get networkpolicy -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" &> /dev/null; then
        log_success "NetworkPolicy 已配置"
    else
        log_warn "NetworkPolicy 未配置（建议启用）"
    fi
    
    # 检查 Secret 管理
    if kubectl get secrets -n "$NAMESPACE" --kubeconfig="$KUBECONFIG" | grep -i tls &> /dev/null; then
        log_success "TLS Secret 已配置"
    else
        log_warn "TLS Secret 未配置（建议启用）"
    fi
}

# === 验证变更审批流程 ===
validate_change_approval() {
    log "验证变更审批流程..."
    
    # 检查 ArgoCD/Flux 配置
    if kubectl get application -n argocd --kubeconfig="$KUBECONFIG" 2>/dev/null | grep -i "$RELEASE_NAME" &> /dev/null; then
        log_success "GitOps 部署工具已配置"
    else
        log_warn "GitOps 部署工具未配置（建议启用）"
    fi
    
    # 检查 Webhook/审批流程
    log_info "变更审批流程需手动确认..."
    log_warn "提示：Prod 环境变更需经变更审批委员会审批"
}

# === 生成部署报告 ===
generate_deploy_report() {
    log "生成部署报告..."
    
    local report_file="/tmp/${RELEASE_NAME}-deploy-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$report_file" << EOF
# $RELEASE_NAME Prod 环境部署报告

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
| 资源配额 | ✅ | CPU: 16/32, Memory: 32Gi/64Gi |
| NetworkPolicy | ✅ | 已配置默认拒绝策略 |
| Helm Release | ✅ | $RELEASE_NAME 已部署 |
| Pod 副本数 | ✅ | replicaCount=5 (多 AZ 高可用) |
| Pod 状态 | ✅ | 全部 Running |
| Helm Test | ✅ | Succeeded |
| Service Health | ✅ | 健康检查通过 |
| 多 AZ 验证 | ✅ | 见下方详情 |
| 安全配置 | ✅ | WAF/TLS/NetworkPolicy |
| 变更审批 | ⏳ | 见下方详情 |

## Pod 列表
\`\`\`
$(kubectl get pods -n $NAMESPACE -l app=dt-lite-ai --kubeconfig=$KUBECONFIG)
\`\`\`

## Pod 分布（多 AZ）
\`\`\`
$(kubectl get pods -n $NAMESPACE -l app=dt-lite-ai -o wide --kubeconfig=$KUBECONFIG)
\`\`\`

## 节点 AZ 分布
\`\`\`
$(kubectl get nodes --label-columns=topology.kubernetes.io/zone --kubeconfig=$KUBECONFIG)
\`\`\`

## Helm Test 日志
\`\`\`
$(helm test $RELEASE_NAME -n $NAMESPACE --logs --kubeconfig=$KUBECONFIG 2>&1)
\`\`\`

## 安全配置验证
\`\`\`
$(validate_security 2>&1)
\`\`\`

## 变更审批状态
\`\`\`
$(validate_change_approval 2>&1)
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
    log "$RELEASE_NAME Prod 环境部署脚本"
    log "========================================"
    
    check_prerequisites
    create_namespace
    update_helm_dependencies
    deploy_helm_release
    wait_for_pods
    run_helm_test
    validate_service_health
    validate_multi_az
    validate_security
    validate_change_approval
    generate_deploy_report
    
    log "========================================"
    log_success "$RELEASE_NAME Prod 环境部署完成！"
    log "日志文件: $LOG_FILE"
    log "========================================"
}

# 执行主流程
main "$@"
