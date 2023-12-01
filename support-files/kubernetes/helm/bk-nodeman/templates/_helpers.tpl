{{/*
Expand the name of the chart.
*/}}
{{- define "bk-nodeman.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "bk-nodeman.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "bk-nodeman.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "bk-nodeman.labels" -}}
helm.sh/chart: {{ include "bk-nodeman.chart" . }}
{{ include "bk-nodeman.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "bk-nodeman.selectorLabels" -}}
app.kubernetes.io/name: {{ include "bk-nodeman.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "bk-nodeman.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "bk-nodeman.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Return true if cert-manager required annotations for TLS signed certificates are set in the Ingress annotations
Ref: https://cert-manager.io/docs/usage/ingress/#supported-annotations
*/}}
{{- define "bk-nodeman.ingress.certManagerRequest" -}}
{{ if or (hasKey . "cert-manager.io/cluster-issuer") (hasKey . "cert-manager.io/issuer") }}
    {{- true -}}
{{- end -}}
{{- end -}}


{{- define "bk-nodeman.saas-api.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "saas-api" }}
{{- end -}}

{{- define "bk-nodeman.saas-web.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "saas-web" }}
{{- end -}}

{{- define "bk-nodeman.backend-api.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-api" }}
{{- end -}}

{{- define "bk-nodeman.backend-celery-beat.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-celery-beat" }}
{{- end -}}

{{- define "bk-nodeman.backend-common-worker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-common-worker" }}
{{- end -}}

{{- define "bk-nodeman.backend-common-pworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-common-pworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-dworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-dworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-bworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-bworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-baworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-baworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-psworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-psworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-paworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-paworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-pworker.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-pworker" }}
{{- end -}}

{{- define "bk-nodeman.backend-sync-host.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-sync-host" }}
{{- end -}}

{{- define "bk-nodeman.backend-sync-host-re.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-sync-host-re" }}
{{- end -}}

{{- define "bk-nodeman.backend-sync-process.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-sync-process" }}
{{- end -}}

{{- define "bk-nodeman.backend-sync-watch.fullname" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "backend-sync-watch" }}
{{- end -}}


{{- define "bk-nodeman.migrate-job.db" -}}
{{- printf "%s-%s-%d"  (include "bk-nodeman.fullname" .) "migrate-db" .Release.Revision }}
{{- end -}}

{{- define "bk-nodeman.migrate-job.file-sync" -}}
{{- printf "%s-%s-%d"  (include "bk-nodeman.fullname" .) "migrate-file-sync" .Release.Revision }}
{{- end -}}

{{- define "bk-nodeman.migrate-job.db.pure" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "migrate-db" }}
{{- end -}}

{{- define "bk-nodeman.migrate-job.file-sync.pure" -}}
{{- printf "%s-%s"  (include "bk-nodeman.fullname" .) "migrate-file-sync" }}
{{- end -}}

{{/*用于标记或匹配需要采集 metrics 指标的 svc*/}}
{{- define "bk-nodeman.labels.serviceMonitor" -}}
processType: "metrics"
{{- end -}}


{{/*
返回证书路径
*/}}
{{- define "bk-nodeman.env.gseCertPath" -}}
{{ .Values.config.gseCertPath | default ( printf "/data/bk%s/cert" .Values.config.bkAppRunEnv ) }}
{{- end -}}

{{/*
通用卷声明
*/}}
{{- define "bk-nodeman.volumes" -}}
- name: gse-cert
  configMap:
    name: "{{ include "bk-nodeman.fullname" . }}-gse-cert-configmap"
{{- if .Values.volumes }}
{{ toYaml .Values.volumes }}
{{- end }}
{{- end }}


{{/*
通用卷挂载声明
*/}}
{{- define "bk-nodeman.volumeMounts" -}}
- name: gse-cert
  mountPath: {{ include "bk-nodeman.env.gseCertPath" . }}
{{- if .Values.volumeMounts }}
{{ toYaml .Values.volumeMounts }}
{{- end }}
{{- end }}


{{/*
后台环境变量
*/}}
{{- define "bk-nodeman.backend.env" -}}
env:
  {{- if .Values.extraEnvVars }}
  {{- include "common.tplvalues.render" (dict "value" .Values.extraEnvVars "context" $) | nindent 2 }}
  {{- end }}
  {{- if .Values.backendExtraEnvVars }}
  {{- include "common.tplvalues.render" (dict "value" .Values.backendExtraEnvVars "context" $) | nindent 2 }}
  {{- end -}}
{{/* 以最高优先级覆盖变量 BK_BACKEND_CONFIG，防止后台配置被修改 */}}
  - name: "BK_BACKEND_CONFIG"
    value: "true"
envFrom:
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "db-env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "redis-env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "rabbitmq-env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "backend-env-configmap" }}"
  {{- if .Values.extraEnvVarsCM }}
  - configMapRef:
      name: "{{ .Values.extraEnvVarsCM }}"
  {{- end }}
  {{- if .Values.extraEnvVarsSecret }}
  - secretRef:
      name: "{{ .Values.extraEnvVarsSecret }}"
  {{- end }}
{{- end }}


{{/*
SaaS 环境变量
*/}}
{{- define "bk-nodeman.saas.env" -}}
{{- with .Values.extraEnvVars -}}
env:
{{- toYaml . | nindent 2 }}
{{- end }}
envFrom:
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "db-env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "env-configmap" }}"
  - configMapRef:
      name: "{{ printf "%s-%s" (include "bk-nodeman.fullname" .) "redis-env-configmap" }}"
  {{- if .Values.extraEnvVarsCM }}
  - configMapRef:
      name: "{{ .Values.extraEnvVarsCM }}"
  {{- end }}
  {{- if .Values.extraEnvVarsSecret }}
  - secretRef:
      name: "{{ .Values.extraEnvVarsSecret }}"
  {{- end }}
{{- end }}

{{- define "bk-nodeman.backend.initContainers" -}}
initContainers:
  - name: "{{ include "bk-nodeman.migrate-job.file-sync.pure" . }}"
    image: "{{ .Values.global.imageRegistry | default .Values.images.k8sWaitFor.registry }}/{{ .Values.images.k8sWaitFor.repository }}:{{ .Values.images.k8sWaitFor.tag }}"
    imagePullPolicy: "{{ .Values.images.k8sWaitFor.pullPolicy }}"
    args: ["job", "{{ include "bk-nodeman.migrate-job.file-sync" . }}"]
    volumeMounts:
      {{- include "bk-nodeman.volumeMounts" . | nindent 6 }}
    resources:
      {{- toYaml .Values.migrateJob.fileSync.resources | nindent 6 }}
{{- end }}
