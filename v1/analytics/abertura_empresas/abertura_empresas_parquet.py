from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
import pyspark.sql.functions as sf

empresas_schema = StructType([
    StructField("cnpj_basico",                 StringType(), True),
    StructField("razao_social",                StringType(), True),
    StructField("natureza_juridica",           StringType(), True),
    StructField("qualificacao_do_responsavel", StringType(), True),
    StructField("capital_social_da_empresa",   StringType(), True),
    StructField("porte_da_empresa",            StringType(), True),
    StructField("ente_federativo_responsavel", StringType(), True),
])

estabelecimentos_schema = StructType([
    StructField("cnpj_basico",                StringType(), True),
    StructField("cnpj_ordem",                 StringType(), True),
    StructField("cnpj_dv",                    StringType(), True),
    StructField("identificador_matriz_filial", StringType(), True),
    StructField("nome_fantasia",              StringType(), True),
    StructField("situacao_cadastral",         StringType(), True),
    StructField("data_situacao_cadastral",    StringType(), True),
    StructField("motivo_situacao_cadastral",  StringType(), True),
    StructField("nome_da_cidade_no_exterior", StringType(), True),
    StructField("pais",                       StringType(), True),
    StructField("data_inicio_atividade",      StringType(), True),
    StructField("cnae_fiscal_principal",      StringType(), True),
    StructField("cnae_fiscal_secundaria",     StringType(), True),
    StructField("tipo_logradouro",            StringType(), True),
    StructField("logradouro",                 StringType(), True),
    StructField("numero",                     StringType(), True),
    StructField("complemento",                StringType(), True),
    StructField("bairro",                     StringType(), True),
    StructField("cep",                        StringType(), True),
    StructField("uf",                         StringType(), True),
    StructField("municipio",                  StringType(), True),
    StructField("ddd_1",                      StringType(), True),
    StructField("telefone_1",                 StringType(), True),
    StructField("ddd_2",                      StringType(), True),
    StructField("telefone_2",                 StringType(), True),
    StructField("ddd_fax",                    StringType(), True),
    StructField("fax",                        StringType(), True),
    StructField("correio_eletronico",         StringType(), True),
    StructField("situacao_especial",          StringType(), True),
    StructField("data_situacao_especial",     StringType(), True),
])

spark = SparkSession.builder \
      .config("spark.jars.packages",
              "org.apache.hadoop:hadoop-aws:3.4.0,"
              "software.amazon.awssdk:bundle:2.20.18") \
      .config("spark.driver.memory", "4g") \
      .config("spark.executor.memory", "4g") \
      .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
      .config("spark.hadoop.fs.s3a.access.key", "admin") \
      .config("spark.hadoop.fs.s3a.secret.key", "password123") \
      .config("spark.hadoop.fs.s3a.path.style.access", "true") \
      .config("spark.hadoop.fs.s3a.aws.credentials.provider",
              "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
      .getOrCreate()

emp = spark.read.option("delimiter", ";").schema(empresas_schema).csv("s3a://contabilizei/raw/empresas/*")
est = spark.read.option("delimiter", ";").schema(estabelecimentos_schema).csv("s3a://contabilizei/raw/estabelecimentos/*")

result = est.join(emp, "cnpj_basico", "inner")\
    .select(emp.cnpj_basico, emp.razao_social, est.uf, sf.substring(est.data_inicio_atividade, 1, 6).alias("ano_mes"))
result.coalesce(1).write.mode("overwrite").parquet("./output")
