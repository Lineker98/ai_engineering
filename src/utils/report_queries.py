# queries.py
"""
SQLs pré-definidas para construção do report
"""

SQL_CASE_GROWTH = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as ym,
         count(*) as casos
  from srag_data
  where DT_SIN_PRI is not null
  group by ym
)
select
  ym,
  casos,
  lag(casos) over (order by ym) as casos_prev,
  round(100.0 * (casos - lag(casos) over (order by ym))
        / nullif(lag(casos) over (order by ym), 0), 2) as taxa_aumento_pct
from agg
order by ym;
""".strip()

SQL_MORTALITY = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as ym,
         sum(case when EVOLUCAO in (1,2,3) then 1 else 0 end) as casos_validos,
         sum(case when EVOLUCAO = 2 then 1 else 0 end) as obitos_srag,
         sum(case when EVOLUCAO in (2,3) then 1 else 0 end) as obitos_totais
  from srag_data
  where DT_SIN_PRI is not null
  group by ym
)
select
  ym,
  casos_validos,
  obitos_srag,
  round(100.0 * obitos_srag / nullif(casos_validos, 0), 2) as taxa_mortalidade_pct,
  round(100.0 * obitos_totais / nullif(casos_validos, 0), 2) as taxa_mortalidade_incl_outras_pct
from agg
order by ym;
""".strip()

SQL_ICU = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as ym,
         sum(case when UTI in (1,2) then 1 else 0 end) as casos_com_info_uti,
         sum(case when UTI = 1 then 1 else 0 end) as uti_sim
  from srag_data
  where DT_SIN_PRI is not null
  group by ym
)
select
  ym,
  casos_com_info_uti,
  uti_sim,
  round(100.0 * uti_sim / nullif(casos_com_info_uti, 0), 2) as taxa_ocupacao_uti_pct
from agg
order by ym;
""".strip()

SQL_VACCINATION = """
with agg as (
  select strftime('%Y-%m', date(DT_SIN_PRI)) as ym,
         sum(case when VACINA_COV in (1,2) then 1 else 0 end) as casos_com_info_vac,
         sum(case when VACINA_COV = 1 then 1 else 0 end) as vacinados
  from srag_data
  where DT_SIN_PRI is not null
  group by ym
)
select
  ym,
  casos_com_info_vac,
  vacinados,
  round(100.0 * vacinados / nullif(casos_com_info_vac, 0), 2) as taxa_vacinacao_casos_pct
from agg
order by ym;
""".strip()
