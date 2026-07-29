# Use the official Langflow image as the base
FROM langflowai/langflow:latest

# Switch to root user temporarily to install packages
USER root

# Install your required pip package (e.g., 'transformers')
# Use the path to the virtual environment's pip executable

RUN /app/.venv/bin/pip install clickhouse-sqlalchemy

# Fluxo padrão do Langflow, carregado automaticamente quando o container
# sobe sem um langflow.db existente (ver entrypoint.sh)
COPY langflow/V202606160017__correcao_tipo_input_componentes_sql.json /app/default_flows/contabilizei.json

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch back to the default user for security
USER user

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["langflow", "run"]
