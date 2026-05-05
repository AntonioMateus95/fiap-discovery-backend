# Contabilizei - Importação de Dados CNPJ

Este repositório contém scripts e configurações para importar os dados abertos de CNPJ da Receita Federal do Brasil para um banco de dados PostgreSQL utilizando o `pgloader`.

## Pré-requisitos

- PostgreSQL instalado e configurado
- pgloader instalado (veja instruções abaixo)
- Acesso à internet para download dos arquivos de dados

## Instalação do pgloader

### Linux

#### Ubuntu/Debian

```bash
# Adicione o repositório oficial do pgloader
sudo apt-get update
sudo apt-get install -y pgloader
```

#### Fedora/RHEL/CentOS

```bash
# Via dnf/yum
sudo dnf install pgloader
# ou
sudo yum install pgloader
```

#### Arch Linux

```bash
sudo pacman -S pgloader
```

#### Compilação a partir do código-fonte

Se preferir compilar a partir do código-fonte:

```bash
# Instale as dependências
sudo apt-get install -y build-essential sbcl unzip libsqlite3-dev make curl \
     gawk freetds-dev libzip-dev

# Clone o repositório
git clone https://github.com/dimitri/pgloader.git
cd pgloader

# Compile
make pgloader
sudo make install
```

### Windows

#### Opção 1: Usando WSL (Windows Subsystem for Linux)

Recomendado para Windows. Instale o WSL e siga as instruções para Linux acima.

1. Instale o WSL2:
   ```powershell
   wsl --install
   ```

2. Após instalar o WSL, abra o terminal Linux e siga as instruções de instalação para Linux.

#### Opção 2: Usando Chocolatey

```powershell
choco install pgloader
```

#### Opção 3: Download binário

1. Acesse a página de releases do pgloader: https://github.com/dimitri/pgloader/releases
2. Baixe a versão mais recente para Windows
3. Extraia o arquivo e adicione ao PATH do sistema

#### Opção 4: Usando Docker

```bash
docker pull dimitri/pgloader
```

Para usar com Docker:
```bash
docker run --rm -v /caminho/para/dados:/data dimitri/pgloader pgloader [comandos]
```

## Download dos Arquivos de Dados

Os arquivos grandes de dados CNPJ da Receita Federal podem ser baixados diretamente do site oficial:

**URL dos Dados Abertos CNPJ:**
https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/

Os arquivos estão organizados por mês/ano em diretórios nomeados como `YYYY-MM/`. Baixe os arquivos necessários e coloque-os na pasta `dados/` deste repositório.

### Estrutura de arquivos esperada

Os scripts de load esperam arquivos com os seguintes padrões de nome:
- `K3241.K03200Y[0-9].D60110.EMPRECSV` - Dados de empresas
- `K3241.K03200Y[0-9].D60110.ESTABELE` - Dados de estabelecimentos
- Outros arquivos conforme definido nos scripts `.load`

## Uso

1. Certifique-se de que o PostgreSQL está rodando e que o banco de dados `contabilizei_db` foi criado.

2. Coloque os arquivos de dados na pasta `dados/`.

3. Execute os scripts de load na ordem apropriada:

```bash
# Exemplo: carregar dados de estabelecimentos
pgloader load/estabelecimentos.load

# Carregar dados de empresas
pgloader load/empresas.load

# E assim por diante para os outros arquivos
```

## Estrutura do Projeto

```
contabilizei/
├── dados/              # Arquivos CSV de dados CNPJ (não versionados)
├── load/               # Scripts de configuração do pgloader
│   ├── empresas.load
│   ├── estabelecimentos.load
│   ├── natureza_juridica.load
│   ├── motivo_situacao_cadastral.load
│   ├── paises.load
│   ├── qualificacao_socios.load
│   └── simples.load
└── README.md
```

## Notas Importantes

- Os arquivos de dados são muito grandes (vários GB). Certifique-se de ter espaço em disco suficiente.
- O processo de importação pode levar várias horas dependendo do tamanho dos dados e da performance do sistema.
- Os arquivos de dados usam codificação Windows-1252 (CP1252), que é tratada automaticamente pelos scripts de load.
- Certifique-se de que o banco de dados PostgreSQL tem configurações adequadas de memória e conexões para lidar com a carga de dados.

## Referências

- [pgloader - Documentação Oficial](https://pgloader.readthedocs.io/)
- [Dados Abertos CNPJ - Receita Federal](https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj/)

```bash
docker run -p 9000:9000 -p 9090:9090 --name minio_server -v ./minio_data:/data -e "MINIO_ROOT_USER=root" -e "MINIO_ROOT_PASSWORD=password" quay.io/minio/minio server /data --console-address :9090

docker run -p 9083:9083 --env SERVICE_NAME=metastore --env HIVE_CUSTOM_CONF_DIR=/opt/hive/conf -v ./hive_condig:/opt/hive/conf --name hive_metastore apache/hive:4.1.0

docker run -p 8080:8080 --name presto_server -v ./presto_catalog:/opt/presto-server/etc/catalog prestodb/presto
```