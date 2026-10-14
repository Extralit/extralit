{{- define "extralit.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Truncated to 52 chars so suffixes like -postgresql still fit the 63-char DNS limit; the release name is used alone if it already contains the chart name.
*/}}
{{- define "extralit.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 52 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 52 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 52 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
StatefulSet names get "-0" and a revision hash appended in labels, so they must stay within 52 chars.
*/}}
{{- define "extralit.postgresqlName" -}}
{{- printf "%s-postgresql" (include "extralit.fullname" . | trunc 41 | trimSuffix "-") }}
{{- end }}

{{/*
ECK rejects Elasticsearch names longer than 36 chars.
*/}}
{{- define "extralit.elasticsearchName" -}}
{{- include "extralit.fullname" . | trunc 36 | trimSuffix "-" }}
{{- end }}

{{/*
Required co-location of server and worker pods on the node holding the ReadWriteOnce volume.
A pod that matches its own term may schedule when no other pod matches, so fresh installs work.
*/}}
{{- define "extralit.rwoAffinity" -}}
{{- if include "extralit.rwoPersistence" . }}
affinity:
  podAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - topologyKey: kubernetes.io/hostname
        labelSelector:
          matchLabels:
            {{- include "extralit.selectorLabels" . | nindent 12 }}
          matchExpressions:
            - key: app.kubernetes.io/component
              operator: In
              values: [server, worker]
{{- end }}
{{- end }}

{{- define "extralit.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "extralit.labels" -}}
helm.sh/chart: {{ include "extralit.chart" . }}
{{ include "extralit.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "extralit.selectorLabels" -}}
app.kubernetes.io/name: {{ include "extralit.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "extralit.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "extralit.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "extralit.basePath" -}}
{{- with trimAll "/" .Values.extralit.baseUrl }}/{{ . }}{{ end }}
{{- end }}

{{- define "extralit.rwoPersistence" -}}
{{- if and .Values.extralit.persistence.enabled (eq .Values.extralit.persistence.accessMode "ReadWriteOnce") }}true{{ end }}
{{- end }}

{{- define "extralit.scheduling" -}}
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.tolerations }}
tolerations:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}

{{- define "extralit.image" -}}
{{ .Values.extralit.image.repository }}:{{ .Values.extralit.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Returns .value, else the value already stored under .key in the release Secret, else a random string.
*/}}
{{- define "extralit.secretValue" -}}
{{- if .value }}
{{- .value }}
{{- else }}
{{- $existing := lookup "v1" "Secret" .ctx.Release.Namespace (printf "%s-secrets" (include "extralit.fullname" .ctx)) }}
{{- $existing.data | default dict | dig .key "" | b64dec | default (randAlphaNum 32) }}
{{- end }}
{{- end }}

{{- define "extralit.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis:6379/0" (include "extralit.fullname" .) }}
{{- else }}
{{- .Values.externalRedis.url }}
{{- end }}
{{- end }}

{{/*
Environment shared by the server and worker containers.
*/}}
{{- define "extralit.env" -}}
{{- $secret := printf "%s-secrets" (include "extralit.fullname" .) }}
{{- if .Values.elasticsearch.useOperator }}
- name: ELASTIC_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "extralit.elasticsearchName" . }}-es-elastic-user
      key: elastic
- name: EXTRALIT_ELASTICSEARCH
  value: "http://elastic:$(ELASTIC_PASSWORD)@{{ include "extralit.elasticsearchName" . }}-es-http:9200"
{{- else }}
- name: EXTRALIT_ELASTICSEARCH
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: elasticsearch-url
- name: EXTRALIT_ELASTICSEARCH_SSL_VERIFY
  value: {{ .Values.externalElasticsearch.sslVerify | quote }}
{{- end }}
- name: EXTRALIT_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: database-url
- name: EXTRALIT_REDIS_URL
  value: {{ include "extralit.redisUrl" . | quote }}
- name: EXTRALIT_REDIS_USE_CLUSTER
  value: {{ and (not .Values.redis.enabled) .Values.externalRedis.useCluster | quote }}
- name: EXTRALIT_AUTH_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: auth-secret-key
{{- if .Values.extralit.persistence.enabled }}
- name: EXTRALIT_HOME_PATH
  value: {{ .Values.extralit.persistence.mountPath | quote }}
{{- end }}
{{- if .Values.storage.url }}
- name: EXTRALIT_STORAGE_URL
  value: {{ .Values.storage.url | quote }}
{{- end }}
{{- if .Values.storage.s3.accessKey }}
- name: EXTRALIT_S3_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: s3-access-key
- name: EXTRALIT_S3_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: s3-secret-key
{{- end }}
{{- if .Values.storage.s3.region }}
- name: EXTRALIT_S3_REGION
  value: {{ .Values.storage.s3.region | quote }}
{{- end }}
{{- with include "extralit.basePath" . }}
- name: EXTRALIT_BASE_URL
  value: {{ . | quote }}
{{- end }}
{{- with .Values.extralit.extraEnv }}
{{ toYaml . }}
{{- end }}
{{- end }}
