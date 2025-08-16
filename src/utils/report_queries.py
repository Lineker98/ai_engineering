"""
SQLs pré-definidas para construção do report
"""

SQL_CASE_GROWTH = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as date_month,
         count(*) as casos
  from srag_data
  where DT_SIN_PRI is not null
  group by date_month
)
select
  date_month,
  casos,
  lag(casos) over (order by date_month) as casos_prev,
  round(100.0 * (casos - lag(casos) over (order by date_month))
        / nullif(lag(casos) over (order by date_month), 0), 2) as taxa_aumento_pct
from agg
where date_month >= strftime('%Y-%m', date('now', '-12 months'))
order by date_month;
""".strip()

SQL_MORTALITY = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as date_month,
         sum(case when EVOLUCAO in (1,2,3) then 1 else 0 end) as casos_validos,
         sum(case when EVOLUCAO = 2 then 1 else 0 end) as obitos_srag,
         sum(case when EVOLUCAO in (2,3) then 1 else 0 end) as obitos_totais
  from srag_data
  where DT_SIN_PRI is not null
  group by date_month
)
select
  date_month,
  casos_validos,
  obitos_srag,
  round(100.0 * obitos_srag / nullif(casos_validos, 0), 2) as taxa_mortalidade_pct,
  round(100.0 * obitos_totais / nullif(casos_validos, 0), 2) as taxa_mortalidade_incl_outras_pct
from agg
where date_month >= strftime('%Y-%m', date('now', '-12 months'))
order by date_month;
""".strip()

SQL_UTI = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as date_month,
         sum(case when UTI in (1, 2) then 1 else 0 end) as casos_com_info_uti,
         sum(case when UTI = 1 then 1 else 0 end) as uti_sim
  from srag_data
  where DT_SIN_PRI is not null
  group by date_month
)
select
  date_month,
  casos_com_info_uti,
  uti_sim,
  round(100.0 * uti_sim / nullif(casos_com_info_uti, 0), 2) as taxa_ocupacao_uti_pct
from agg
where date_month >= strftime('%Y-%m', date('now', '-12 months'))
order by date_month;
""".strip()

SQL_VACCINATION = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as date_month,
         sum(case when VACINA_COV in (1,2) then 1 else 0 end) as casos_com_info_vac,
         sum(case when VACINA_COV = 1 then 1 else 0 end) as vacinados
  from srag_data
  where DT_SIN_PRI is not null
  group by date_month
)
select
  date_month,
  casos_com_info_vac,
  vacinados,
  round(100.0 * vacinados / nullif(casos_com_info_vac, 0), 2) as taxa_vacinacao_casos_pct
from agg
where date_month >= strftime('%Y-%m', date('now', '-12 months'))
order by date_month;
""".strip()

SQL_CASOS_DIARIOS_30_DIAS = """
with 
  base_data as (
    select date(dt_sin_pri) as data_sintoma
    from srag_data
    where dt_sin_pri is not null
  ),
  ultima_data as (
    select max(data_sintoma) as data_maxima
    from base_data
  ),
  ultimos_30_dias as (
    select data_sintoma
    from base_data, ultima_data
    where data_sintoma between date(data_maxima, '-29 days') and data_maxima
)
select
    data_sintoma as data, 
    count(*) as casos_diarios
from ultimos_30_dias
group by data_sintoma
order by data_sintoma
""".strip()


SQL_CASOS_MENSAIS_12_MESES = """
with 
  base_data as (
    select date(dt_sin_pri) as data_sintoma
    from srag_data
    where dt_sin_pri is not null
  ),
  
  ultima_data as (
    select max(data_sintoma) as data_maxima
    from base_data
  ),
  
  ultimos_12_meses as (
    select data_sintoma
    from base_data, ultima_data
    where data_sintoma between date(data_maxima, '-11 months') and data_maxima
  ),
  
  agg as (
    select strftime('%Y-%m', data_sintoma) as date_month
    from ultimos_12_meses
  )
  
select
    date_month,
    count(*) as casos_mensais
from agg
group by date_month
order by date_month
"""
