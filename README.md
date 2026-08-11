# Kubernetes HomeLab

A production-ready Kubernetes homelab running on legacy hardware, demonstrating modern cloud-native practices with GitOps, automated certificate management, and centralized secrets orchestration.

**Philosophy**: Everything is defined as code, version controlled, and applied declaratively. This setup showcases enterprise-grade patterns adapted for a single-node homelab environment.

---

## 🖥️ Hardware

| Node | Model | CPU | RAM | Role |
|------|-------|-----|-----|------|
| homelab-1 | MacBook Air 2011 | Intel Core | 4GB | k3s server + worker |

---

## 🧰 Tech Stack

| Component | Purpose |
|-----------|---------|
| **k3s** | Lightweight Kubernetes distribution |
| **Helm** | Kubernetes package manager |
| **Traefik** | Ingress controller and reverse proxy |
| **ArgoCD** | GitOps continuous delivery platform |
| **HashiCorp Vault** | Centralized secrets management |
| **External Secrets Operator** | Syncs secrets from Vault to Kubernetes |
| **Cert-Manager** | Automated TLS certificate management |
| **Nextcloud** | Self-hosted file sync and collaboration |
| **Vaultwarden** | Lightweight Bitwarden-compatible password manager |
| **Redis** | Caching layer for ArgoCD |
| **SQLite** | Embedded database for applications |

---

## 📁 Repository Structure

```
Kubernetes-HomeLab/
├── .gitignore                    # Excludes secrets, certificates, keys
└── my-home-cluster/
    ├── apps/                     # Application layer
    │   ├── nextcloud/           # Self-hosted cloud storage
    │   │   ├── Chart.yaml
    │   │   ├── values.yaml
    │   │   └── templates/
    │   └── vaultwarden/         # Password manager
    │       ├── Chart.yaml
    │       ├── values.yaml
    │       └── templates/
    └── infra/                    # Infrastructure layer
        ├── argocd/              # GitOps CD platform
        │   ├── Chart.yaml
        │   └── values.yaml
        ├── cert-manager/        # Certificate automation
        │   ├── Chart.yaml
        │   └── values.yaml
        ├── external-secrets/    # Secrets sync operator
        │   ├── Chart.yaml
        │   └── values.yaml
        └── vault/               # Secrets store
            ├── Chart.yaml
            └── values.yaml
```

**Deployment Strategy**: ArgoCD continuously monitors this Git repository and automatically applies changes to the cluster. Infrastructure components are deployed first to establish foundational services (secrets, certificates, ingress), followed by applications that depend on them.

---

## 🔧 Infrastructure Components

### ArgoCD (GitOps Continuous Delivery)

**Version**: v3.4.5 (Helm Chart v10.2.1)
**Domain**: `argocd.kube.home`
**Namespace**: `infra-argocd`

Declarative GitOps platform that manages all cluster deployments from this Git repository.

**Key Features**:
- Ingress via Traefik with TLS termination
- Custom RBAC roles for namespace-scoped deployments
- Redis for caching and session management
- Dex integration for SSO/authentication
- ApplicationSet controller for multi-app patterns
- Network policies enabled for pod-level security

**Configuration Highlights**:
- Server runs in insecure mode (TLS terminates at Traefik ingress)
- Notifications controller enabled for deployment alerts
- Automated sync policies for infrastructure components

---

### Cert-Manager (Certificate Management)

**Version**: v1.20.2
**Namespace**: `infra-cert-manager`

Automates the lifecycle of TLS certificates using a custom internal Certificate Authority.

**Key Features**:
- Custom CA Issuer: `homelab-ca` (self-signed root CA)
- Automatic certificate renewal before expiration
- Secret: `homelab-root-ca-secret` stores root CA keypair
- Webhook validation for certificate resources
- CA injector for automatic CA bundle distribution
- Security hardened (runAsNonRoot, readOnlyRootFilesystem)

**How It Works**: Applications request certificates via `Certificate` CRD, cert-manager issues them from the internal CA, and stores them as Kubernetes secrets. Traefik ingress automatically picks up these secrets for TLS termination.

---

### HashiCorp Vault (Secrets Management)

**Version**: 1.21.2
**Mode**: Standalone with integrated storage
**Domain**: `vault.kube.home`
**Namespace**: `app-vault`

Centralized secrets store for sensitive data (credentials, API keys, certificates).

**Key Features**:
- Integrated Raft storage backend (10Gi PVC)
- TLS enabled with custom certificates
- UI accessible at `https://vault.kube.home`
- Traefik IngressRouteTCP with TLS passthrough
- Standalone mode (sufficient for single-node homelab)

**Security**: Vault data is encrypted at rest. Unsealing is required after pod restarts. CSI provider and injector are disabled in favor of External Secrets Operator pattern.

---

### External Secrets Operator

Bridges Vault and Kubernetes by syncing secrets into native Kubernetes Secret objects.

**Key Features**:
- `ExternalSecret` CRD defines which Vault paths to sync
- `SecretStore` CRD configures Vault connection
- Automatic secret rotation when Vault values change
- Webhook validation for external secret resources
- Security hardened pod configuration

**Example**: Nextcloud deployment references `ExternalSecret` named `nextcloud-secret`, which pulls admin credentials from Vault path `secret/nextcloud/admin` and creates a Kubernetes secret consumed by the Nextcloud pod.

---

## 🚀 Applications

### Nextcloud (Self-Hosted Cloud Storage)

**Version**: v33.0.2 (Helm Chart v9.0.5)
**Domain**: `nextcloud.kube.home`
**Namespace**: `app-nextcloud`

File sync, sharing, and collaboration platform—think Dropbox/Google Drive but self-hosted.

**Configuration**:
- Single replica deployment
- SQLite database (internal, suitable for homelab scale)
- 3Gi persistent volume for files (`nextcloud-pvc`)
- Admin credentials sourced from Vault via ExternalSecret
- TLS certificate issued by cert-manager
- Ingress via Traefik

**Storage Evolution**: Files are stored in the persistent volume, which survives pod restarts. Backups of this PVC are critical for data safety.

**Access**: `https://nextcloud.kube.home` (requires `/etc/hosts` entry or local DNS)

---

### Vaultwarden (Password Manager)

**Version**: v1.36.0-alpine (Helm Chart v0.38.0)
**Domain**: `warden.kube.home`
**Namespace**: Assumed `app-vaultwarden`

Lightweight, Bitwarden-compatible password manager written in Rust.

**Configuration**:
- Single replica deployment
- SQLite database (default)
- 3Gi persistent volume (`vaultwarden-pvc`)
- TLS enabled via cert-manager
- Web vault enabled for browser access
- Signups allowed with email verification
- Extended logging for troubleshooting

**Access**: `https://warden.kube.home` (Bitwarden clients connect here)

**Security**: Admin token configured for administrative panel access. Production deployments should disable signups after initial user creation.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────┐
                    │   Traefik Ingress Controller    │
                    │   (TLS Termination & Routing)   │
                    └──────────────┬──────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              │                    │                     │
         ┌────▼─────┐        ┌────▼─────┐        ┌─────▼──────┐
         │  ArgoCD  │        │Nextcloud │        │Vaultwarden │
         │  (GitOps)│        │ (Files)  │        │(Passwords) │
         └────┬─────┘        └────┬─────┘        └─────┬──────┘
              │                   │                     │
              └───────────────────┼─────────────────────┘
                                  │
                         ┌────────▼─────────────┐
                         │    Cert-Manager      │
                         │ (TLS Certificates)   │
                         │  Issues certs for:   │
                         │  - ArgoCD            │
                         │  - Vault             │
                         │  - Nextcloud         │
                         │  - Vaultwarden       │
                         └────────┬─────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │        Vault              │
                    │  (Secrets Store)          │
                    │  - Gets TLS from certmgr  │
                    │  - Stores app secrets     │
                    └─────────────┬─────────────┘
                                  │
                       ┌──────────▼────────────────┐
                       │ External Secrets Operator │
                       │ (Syncs Vault → K8s)       │
                       └───────────────────────────┘
```

**Data Flow**:
1. **ArgoCD** watches this Git repo and applies manifests declaratively
2. **Cert-Manager** issues TLS certificates from internal CA (`homelab-ca`) for all services
3. **Vault** receives its TLS cert from cert-manager AND stores application secrets (encrypted at rest)
4. **External Secrets Operator** pulls secrets from Vault → creates native K8s Secrets
5. **Applications** mount secrets as environment variables or files
6. **Traefik** routes traffic based on domain names (*.kube.home), terminates TLS using certs from cert-manager

---

## 🎯 Getting Started

### Prerequisites

- **k3s** installed on your node ([k3s.io](https://k3s.io))
- **kubectl** configured to access your cluster
- **helm** v3+ installed
- **git** for cloning this repository

### Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd Kubernetes-HomeLab

# Deploy infrastructure components (order matters)
cd my-home-cluster/infra

# 1. Deploy Vault first (secrets foundation)
helm install vault ./vault -n app-vault --create-namespace

# 2. Deploy Cert-Manager (certificate foundation)
helm install cert-manager ./cert-manager -n infra-cert-manager --create-namespace

# 3. Deploy External Secrets Operator
helm install infra-external-secrets ./external-secrets -n infra-external-secrets --create-namespace

# 4. Deploy ArgoCD (GitOps controller)
helm install argocd ./argocd -n infra-argocd --create-namespace

# After ArgoCD is running, let it manage app deployments automatically
# or deploy manually:
cd ../apps
helm install nextcloud ./nextcloud -n app-nextcloud --create-namespace
helm install vaultwarden ./vaultwarden -n app-vaultwarden --create-namespace
```

---

## 🔐 Initial Setup

### 1. Initialize Vault

After Vault deployment, it must be initialized and unsealed:

```bash
# Port-forward to Vault pod
kubectl port-forward -n app-vault svc/vault 8200:8200

# Initialize (save the unseal keys and root token!)
vault operator init

# Unseal (requires 3 out of 5 unseal keys by default)
vault operator unseal <key1>
vault operator unseal <key2>
vault operator unseal <key3>

# Login with root token
vault login <root-token>

# Enable KV v2 secrets engine
vault secrets enable -path=secret kv-v2

# Store example secrets
vault kv put secret/nextcloud/admin username=admin password=<secure-password>
vault kv put secret/vaultwarden/admin token=<secure-token>
```

### 2. ArgoCD First Login

```bash
# Get initial admin password
kubectl get secret -n infra-argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port-forward to ArgoCD UI
kubectl port-forward -n infra-argocd svc/argocd-server 8080:443

# Access UI at https://localhost:8080
# Username: admin
# Password: <from above command>

# Change password immediately after first login
argocd account update-password
```

### 3. Trust Custom CA Certificate

For your browser to trust `*.kube.home` domains:

```bash
# Extract root CA certificate
kubectl get secret -n infra-cert-manager homelab-root-ca-secret -o jsonpath='{.data.ca\.crt}' | base64 -d > homelab-ca.crt

# macOS: Import to Keychain
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain homelab-ca.crt

# Linux: Copy to trusted certs
sudo cp homelab-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Restart browser after importing
```

### 4. Configure Local DNS

Add entries to `/etc/hosts`:

```
# Kubernetes HomeLab Services
<NODE-IP>  argocd.kube.home
<NODE-IP>  vault.kube.home
<NODE-IP>  nextcloud.kube.home
<NODE-IP>  warden.kube.home
```

Replace `<NODE-IP>` with your MacBook's IP address (find with `ifconfig | grep "inet "`).

---

## 💾 Backup Strategy

### Critical Data Locations

| Component | Data Type | Storage | Backup Priority |
|-----------|-----------|---------|-----------------|
| **Nextcloud** | User files | PVC `nextcloud-pvc` (3Gi) | 🔴 Critical |
| **Vaultwarden** | Password vault | PVC `vaultwarden-pvc` (3Gi) | 🔴 Critical |
| **Vault** | Secrets + encryption keys | PVC `vault-data` (10Gi) | 🔴 Critical |
| **Cert-Manager** | CA keypair | Secret `homelab-root-ca-secret` | 🟡 Important |
| **ArgoCD** | Git repo reference | Stateless (Git is source of truth) | 🟢 Low |

### Backup Procedures

#### PVC Snapshots (Recommended)

If your storage class supports snapshots:

```bash
# Create VolumeSnapshot resources
kubectl create -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: nextcloud-snapshot-$(date +%Y%m%d)
  namespace: app-nextcloud
spec:
  source:
    persistentVolumeClaimName: nextcloud-pvc
EOF
```

#### Manual Backup via tar

```bash
# Nextcloud files
kubectl exec -n app-nextcloud deployment/nextcloud -- tar czf - /var/www/html/data > nextcloud-backup-$(date +%Y%m%d).tar.gz

# Vaultwarden database
kubectl exec -n app-vaultwarden deployment/vaultwarden -- tar czf - /data > vaultwarden-backup-$(date +%Y%m%d).tar.gz

# Vault data (requires Vault to be sealed first for consistency)
kubectl exec -n app-vault vault-0 -- tar czf - /vault/data > vault-backup-$(date +%Y%m%d).tar.gz
```

#### Configuration Backup

This Git repository already serves as backup for all Kubernetes manifests. Ensure it's pushed to a remote:

```bash
git remote add origin <your-remote-repo>
git push -u origin main
```

#### CA Certificate Backup

```bash
# Export CA secret (includes private key!)
kubectl get secret -n infra-cert-manager homelab-root-ca-secret -o yaml > ca-backup-$(date +%Y%m%d).yaml

# Store this file securely offline (encrypted USB drive, password manager)
```

### Restore Procedures

```bash
# Restore PVC from backup tar
kubectl exec -n app-nextcloud deployment/nextcloud -- tar xzf - -C / < nextcloud-backup-20240815.tar.gz

# Restore Vault from backup
kubectl exec -n app-vault vault-0 -- tar xzf - -C / < vault-backup-20240815.tar.gz
# Then unseal Vault with original unseal keys
```

**Backup Schedule Recommendation**: Daily automated PVC snapshots, weekly off-site configuration backups.

---

## 🌐 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **ArgoCD UI** | `https://argocd.kube.home` | GitOps dashboard and app management |
| **Vault UI** | `https://vault.kube.home` | Secrets management interface |
| **Nextcloud** | `https://nextcloud.kube.home` | File sync and collaboration |
| **Vaultwarden** | `https://warden.kube.home` | Password manager web vault |

All services use TLS certificates issued by the internal `homelab-ca`. Ensure the CA is trusted in your browser and `/etc/hosts` is configured.

---

## 💡 Useful Commands

### Cluster Health

```bash
# Check node status
kubectl get nodes

# Check all pods across namespaces
kubectl get pods --all-namespaces

# Check Traefik ingress
kubectl get ingress --all-namespaces

# Check persistent volumes
kubectl get pv,pvc --all-namespaces
```

### ArgoCD Operations

```bash
# List applications
argocd app list

# Sync an application manually
argocd app sync nextcloud

# Check application status
argocd app get nextcloud

# View application logs
argocd app logs nextcloud
```

### Vault Operations

```bash
# Check Vault status
kubectl exec -n app-vault vault-0 -- vault status

# Unseal Vault after pod restart
kubectl exec -n app-vault vault-0 -- vault operator unseal <key>

# List secrets
kubectl exec -n app-vault vault-0 -- vault kv list secret/

# Read a secret
kubectl exec -n app-vault vault-0 -- vault kv get secret/nextcloud/admin
```

### Certificate Debugging

```bash
# Check cert-manager certificates
kubectl get certificate --all-namespaces

# Describe a certificate (shows issuance status)
kubectl describe certificate nextcloud-tls -n app-nextcloud

# Check cert-manager logs
kubectl logs -n infra-cert-manager deployment/cert-manager
```

### External Secrets Debugging

```bash
# Check ExternalSecrets status
kubectl get externalsecrets --all-namespaces

# Describe an ExternalSecret
kubectl describe externalsecret nextcloud-secret -n app-nextcloud

# Check operator logs
kubectl logs -n infra-external-secrets deployment/infra-external-secrets
```

### Troubleshooting

```bash
# Pod not starting? Check events
kubectl describe pod <pod-name> -n <namespace>

# Application errors? Check logs
kubectl logs <pod-name> -n <namespace>

# Network issues? Test DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default

# Storage issues? Check PVC binding
kubectl get pvc -n <namespace>
kubectl describe pvc <pvc-name> -n <namespace>
```

---

**Note**: This homelab demonstrates enterprise-grade patterns on constrained hardware. For production deployments, consider multi-node clusters, external databases (PostgreSQL), S3-compatible storage backends, and managed secrets services.

**Contributions**: Feel free to open issues or PRs if you have suggestions for improvements!
