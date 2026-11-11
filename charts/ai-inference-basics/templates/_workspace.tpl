{{- define "ai-inference-basics.workspaceConfig" -}}
config.kdl: |
  web_server_ip "127.0.0.1"
  web_server_port 7681
  default_shell "/bin/bash"
  show_startup_tips false
  show_release_notes false
  web_client {
    base_url "/terminal-{{ .participant }}"
  }
Caddyfile: |
  :8081 {
    handle_path /terminal-{{ .participant }}/* {
      reverse_proxy 127.0.0.1:7681 {
        header_down Set-Cookie "Path=/" "Path=/terminal-{{ .participant }}/; Secure"
      }
    }
  }
  :8080 {
    handle_path /preview-{{ .participant }}/* {
      reverse_proxy 127.0.0.1:18080
    }
    handle {
      reverse_proxy 127.0.0.1:18080
    }
  }
{{- end }}
