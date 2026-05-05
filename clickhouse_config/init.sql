CREATE TABLE IF NOT EXISTS contabilizei.abertura_empresas_parquet
  (
      cnpj_basico  String,
      razao_social String,
      uf           String,
      ano_mes      String
  )
  ENGINE = S3(
      'http://minio:9000/contabilizei/analytics/abertura_empresas/*',
	  'admin',
	  'password123',
	  'Parquet'
  );