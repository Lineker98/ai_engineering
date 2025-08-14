from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import black
from typing import List, Dict
from reportlab.lib.pagesizes import A4


def add_title(text_title: str, story: List, title_style: ParagraphStyle) -> List:
    story.append(Paragraph(text_title, title_style))
    return story


def add_intro_paragraph(story: List, body_style: ParagraphStyle) -> List:
    intro = """
    Este relatório apresenta a análise epidemiológica dos casos hospitalizados de Síndrome
    Respiratória Aguda Grave (SRAG) no Brasil com dados extraídos do <b>SIVEP-Gripe</b> para o
    período de 01/07/2025 a 31/07/2025, além de fontes externas. O objetivo é fornecer uma
    visão consolidada das principais métricas como <b>evolução de casos</b>, taxa de mortalidade,
    ocupação de UTI e cobertura vacinal, permitindo a rápida compreensão do cenário atual e
    subsidiando ações de gestão em saúde pública.
    """
    story.append(Paragraph(intro, body_style))
    return story


def add_highlights(
    h1_text: str, h1_style: ParagraphStyle, story: List, bullets_style: ParagraphStyle
) -> List:
    story.append(Paragraph(h1_text, h1_style))
    bullet_points = [
        ("Taxa de crescimento de casos:", "Algum texto depois"),
        ("Mortalidade acumulada:", "Algum texto depois"),
        ("Ocupação de UTI:", "Algum texto depois"),
        ("Cobertura vacinal:", "Algum texto depois"),
    ]
    for bullet, texto in bullet_points:
        # Criamos a string formatada com a tag <b> para o negrito
        texto_formatado = f"&bull; <b>{bullet}</b> {texto}"
        p = Paragraph(texto_formatado, bullets_style)
        story.append(p)

    return story


def add_metodology(
    story: List,
    text_h1: str,
    h1_style: ParagraphStyle,
    contents: List[Dict],
) -> List:
    story.append(Paragraph(text_h1, h1_style))
    
    # Add metodology contents
    for content in contents:
        for field in content.values():
            # Add subtitle
            story.append(Paragraph(field['h2_text'], field['h2_style']))
            
            # Add content
            if field.get('bullets_style'):
                for bullet_point in field['texto']:
                    p = Paragraph(f"&bull; {bullet_point}", field['bullets_style'])
                    story.append(p)
            else:
                story.append(Paragraph(field['texto'], field['body_style']))
    return story

def add_metrics(story: List, text_h1: str, h1_style: ParagraphStyle, images: Dict) -> List:
    story.append(Paragraph(text_h1, h1_style))
    for _, image in images.items():
        story.append(Paragraph(image['image_title'], image['title_style']))
        grafico = Image(image['path'], width=16*cm, height=8*cm)
        story.append(grafico)
        story.append(Paragraph(image['description'], image['description_style']))
    return story
        

def add_final_summary(story: List, text_h1: str, h1_style: ParagraphStyle, content: str, content_style) -> List:
    story.append(Paragraph(text_h1, h1_style))
    story.append(Paragraph(content, content_style))
    return story
            

def generate_executive_report():

    styles = getSampleStyleSheet()

    # 1. SETUP DO DOCUMENTO
    doc = SimpleDocTemplate(
        "relatorio_epidemiologico_srag.pdf",
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    # 2. DEFINIÇÃO DE ESTILOS
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "estilo_titulo",
        parent=styles["h1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    h1_style = ParagraphStyle(
        "h1_style",
        parent=styles["h2"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        spaceBefore=20,
        spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "h2_style",
        parent=styles["h3"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "body_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )
    bullets_style = ParagraphStyle(
        "bullets_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=14,
        leftIndent=20,
        spaceAfter=4,
    )

    # A 'Story' é uma lista que conterá todos os nossos conteúdos
    story = []

    # 3. Aidicionando conteúdo à story

    # Título
    story = add_title(
        text_title="Relatório Epidemiológico de SRAG",
        story=story,
        title_style=estilo_titulo,
    )

    # Paragrafo introdutório
    story = add_intro_paragraph(story=story, body_style=body_style)

    # Cabeçalho Principais destaques
    story = add_highlights(
        h1_text="Principais dstaques",
        h1_style=h1_style,
        story=story,
        bullets_style=bullets_style,
    )

    # Metodologia
    metodology = [
        {
            "fonte_de_dados": {
                "h2_text": "Fonte de Dados",
                "h2_style": h2_style,
                "texto": """Os dados utilizados neste relatório foram extraídos do <b>SIVEP-Gripe</b>
                (Sistema de Informação da Vigilância Epidemiológica da Gripe) em <b>data_extracao</b>, contemplando registros da 
                <b>Ficha de Registro Individual – Casos de Síndrome Respiratória Aguda Grave Hospitalizados</b>. 
                A extração foi realizada a partir do conjunto de dados disponibilizado pelo  <b>OpenDATASUS </b>""",
                "body_style": body_style,
            },
            "dados_utilizados": {
                "h2_text": "Dados Utilizados",
                "h2_style": h2_style,
                "texto": [
                    "Data dos primeiros Sintomas",
                    "Desfecho do caso (Cura, Óbito ou óbito por outras causas)",
                    "Internação em UTI",
                    "Classificação Final do Caso (SRAG por Influenza, COVID-19 etc)",
                ],
                "bullets_style": bullets_style,
            },
        }
    ]
    story = add_metodology(story=story, text_h1="Metodologia", h1_style=h1_style, contents=metodology)
    
    # Imagens
    images = {
        "image1": {
            'path': "src/report/imgs/case_growth_line.png",
            "image_title": "Evolução dos Casos",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        },
        
        "image2": {
            'path': "src/report/imgs/mortality_rate_line.png",
            "image_title": "Taxa de Mortalidade",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        },
        
        "image3": {
            'path': "src/report/imgs/uti_utilization_rate_line.png",
            "image_title": "Taxa de utilização de UTI",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        },
        
        "image4": {
            'path': "src/report/imgs/vaccination_rate_line.png",
            "image_title": "Cobertura Vacinal",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        },
        
        "image5": {
            'path': "src/report/imgs/casos_diarios_30d_covid.png",
            "image_title": "Número de casos diário - 30 dias",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        },
        
        "image6": {
            'path': "src/report/imgs/casos_mensais_12m_covid.png",
            "image_title": "Número de casos mensal - 12 meses",
            "title_style": h2_style,
            "description": "texto explicativo sobre o gráfico",
            "description_style": body_style
        }
    }
    
    story = add_metrics(story=story, text_h1="Avaliação de Métricas", h1_style=h1_style, images=images)
    
    # Resumo Final
    story = add_final_summary(story=story, text_h1="Visão Integrada", h1_style=h1_style, content="gerado por IA", content_style=body_style)
    doc.build(story)
    print("Relatório 'relatorio_srag.pdf' gerado com sucesso!")

if __name__ == "__main__":
    generate_executive_report()
