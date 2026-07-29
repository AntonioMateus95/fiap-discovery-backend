#!/bin/sh
set -e

CONFIG_DIR="${LANGFLOW_CONFIG_DIR:-/app/config}"

if [ ! -f "$CONFIG_DIR/langflow.db" ]; then
  echo "Nenhum langflow.db encontrado em $CONFIG_DIR; carregando o fluxo padrão (Contabilizei) na primeira inicialização."
  export LANGFLOW_LOAD_FLOWS_PATH=/app/default_flows
fi

exec "$@"
