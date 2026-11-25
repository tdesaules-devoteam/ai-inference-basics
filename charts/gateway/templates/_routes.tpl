{{- define "gateway.browserRoutes" -}}
{{- list
  (dict "name" "requester" "path" "/scalar" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "grafana" "path" "/grafana" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "terminal" "path" "/ttyd" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "code" "path" "/code" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "headlamp" "path" "/headlamp" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "oauth2" "path" "/oauth2" "service" "oauth2-proxy" "namespace" "oauth2-proxy" "port" 80)
  (dict "name" "dex" "path" "/dex" "service" "dex" "namespace" "dex" "port" 5556) | toYaml }}
{{- end }}
