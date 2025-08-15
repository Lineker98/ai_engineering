from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import cm
from typing import List, Dict
from reportlab.lib.pagesizes import A4
from pathlib import Path

from ..utils.helper_functions import extrair_ia_summary, load_json


def add_title(
    text_title: str, story: List, title_style: ParagraphStyle
) -> List[Paragraph]:
    """Appends a title to a list of paragraphs.

    This function creates a new `Paragraph` object from the provided text and style,
    and then adds it to the end of the `story` list. The modified list is then returned.

    Args:
        text_title (str): The text content of the title.
        story (List): A list of `Paragraph` objects that represent the main story content.
        title_style (ParagraphStyle): A style object that defines the formatting
                                      of the title, such as font, size, and alignment.

    Returns:
        List[Paragraph]: The modified `story` list with the new title paragraph appended to it.
    """

    story.append(Paragraph(text_title, title_style))
    return story


def add_intro_paragraph(story: List, body_style: ParagraphStyle) -> List[Paragraph]:
    """Adds a fixed introductory paragraph about an SRAG report to the story list.

    Args:
        story (List): A list of `Paragraph` objects that represents the report's content.
        body_style (ParagraphStyle): A style object that defines the formatting
                                     of the paragraph's body text.

    Returns:
        List[Paragraph]: The modified `story` list with the introductory paragraph
                         added to the end.
    """
    intro = """
    Este relatório apresenta a análise epidemiológica dos casos hospitalizados de Síndrome
    Respiratória Aguda Grave (SRAG) no Brasil com dados extraídos do <b>SIVEP-Gripe</b>, 
    além de um resumo com base em fontes externas. O objetivo é fornecer uma
    visão consolidada das principais métricas como <b>evolução de casos</b>, <b>taxa de mortalidade</b>,
    <b>ocupação de UTI</b> e <b>cobertura vacinal</b>, permitindo a rápida compreensão do cenário atual e
    subsidiando ações de gestão em saúde pública.
    """
    story.append(Paragraph(intro, body_style))
    return story


def add_highlights(
    h1_text: str,
    h1_style: ParagraphStyle,
    story: List,
    high_lights: List[str],
    bullets_style: ParagraphStyle,
) -> List[Paragraph]:
    """Appends a heading and a bulleted list of highlights to the story list.

    Args:
        h1_text (str): The text for the main heading.
        h1_style (ParagraphStyle): The style object for the main heading.
        story (List): The list of Paragraph objects to which content will be added.
        high_lights (List[str]): A list of strings to be formatted as bullet points.
        bullets_style (ParagraphStyle): The style object for the bullet points.

    Returns:
        The updated story list containing the new heading and bullet points.
    """
    story.append(Paragraph(h1_text, h1_style))
    for highlight in high_lights:
        p = Paragraph(f"&bull; {highlight}", bullets_style)
        story.append(p)

    return story


def add_metodology(
    story: List,
    text_h1: str,
    h1_style: ParagraphStyle,
    contents: List[Dict],
) -> List[Paragraph]:
    """Adds a 'Methodology' section to the story list with a main heading, subtitles, and content.

    The content can be formatted as either a single paragraph or a bulleted list based on the provided style.

    Args:
        story (List): The list of Paragraph objects to append the new section to.
        text_h1 (str): The text for the main 'Methodology' heading.
        h1_style (ParagraphStyle): The style for the main heading.
        contents (List[Dict]): A list of dictionaries, where each dictionary holds the text and style information for a subsection.

    Returns:
        List[Paragraph]: The updated story list with the complete methodology section.
    """
    story.append(Paragraph(text_h1, h1_style))

    # Add metodology contents
    for content in contents:
        for field in content.values():
            # Add subtitle
            story.append(Paragraph(field["h2_text"], field["h2_style"]))

            # Add content
            if field.get("bullets_style"):
                for bullet_point in field["texto"]:
                    p = Paragraph(f"&bull; {bullet_point}", field["bullets_style"])
                    story.append(p)
            else:
                story.append(Paragraph(field["texto"], field["body_style"]))
    return story


def add_sources(
    story: List,
    h1_text: str,
    h1_style: ParagraphStyle,
    sources: List[str],
    source_style: ParagraphStyle,
) -> List[Paragraph]:
    """
    Adds a heading and a bulleted list of sources to the story list.

    Args:
        story (List): The list of Paragraph objects to which the new content will be added.
        h1_text (str): The text for the main "Sources" heading.
        h1_style (ParagraphStyle): The style object for the main heading.
        sources (List[str]): A list of strings, where each string represents a source.
        source_style (ParagraphStyle): The style object for the bulleted source entries.

    Returns:
        List[Paragraph]: The updated story list containing the new heading and bulleted sources.
    """
    story.append(Paragraph(h1_text, h1_style))
    for source in sources:
        p = Paragraph(f"&bull; {source}", source_style)
        story.append(p)
    return story


def add_metrics(
    story: List, text_h1: str, h1_style: ParagraphStyle, images: Dict
) -> List[Paragraph]:
    """
    Adds a heading and a series of images with titles and descriptions to the story list.

    Args:
        story (List): The list of Paragraph and Image objects to which new content will be added.
        text_h1 (str): The text for the main "Metrics" heading.
        h1_style (ParagraphStyle): The style object for the main heading.
        images (Dict): A dictionary containing image information, including the file path, title, and description.

    Returns:
        List[Paragraph]: The updated story list with the new heading and image content.
    """
    story.append(Paragraph(text_h1, h1_style))
    for _, image in images.items():
        story.append(Paragraph(image["image_title"], image["title_style"]))
        grafico = Image(image["path"], width=16 * cm, height=8 * cm)
        story.append(grafico)
        story.append(Paragraph(image["description"], image["description_style"]))
    return story


def add_final_summary(
    story: List,
    text_h1: str,
    h1_style: ParagraphStyle,
    content: List[str],
    content_style,
) -> List[Paragraph]:
    """Adds a heading and a series of paragraphs as a final summary to the story list.

    Args:
        story (List): The list of Paragraph objects to which new content will be added.
        text_h1 (str): The text for the main "Final Summary" heading.
        h1_style (ParagraphStyle): The style object for the main heading.
        content (List[str]): A list of strings, where each string represents a paragraph of the summary.
        content_style (ParagraphStyle): The style object for the summary paragraphs.

    Returns:
        List[Paragraph]: The updated story list with the new heading and summary content.
    """
    story.append(Paragraph(text_h1, h1_style))
    for text in content:
        story.append(Paragraph(text, content_style))
    return story


def generate_executive_report(
    overall_summary: str,
    high_lights: str,
    consensus: str,
    disagreements: str,
    sources_covered: str,
    metrics: Dict[str, str],
) -> None:
    """Generates a comprehensive executive report on SRAG in PDF format.

    This function assembles a multi-page report by combining various content sections, including a title,
    introduction, key highlights, methodology, metric assessments with images, and a final summary.
    The report is saved as 'relatorio_epidemiologico_srag.pdf'.

    Args:
        overall_summary (str): The main summary text for the final section of the report.
        high_lights (List[str]): A list of strings to be formatted as bullet points in the "Highlights" section.
        consensus (str): Text detailing points of consensus, used in the final summary.
        disagreements (str): Text detailing points of disagreement, used in the final summary.
        sources_covered (List[str]): A list of strings for the "Sources" section.
        metrics (Dict[str, str]): A dictionary containing image descriptions for each metric, which will be used in the "Metrics" section.

    Returns:
        None: This function does not return a value. It creates a PDF file as a side effect.
    """

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
        high_lights=high_lights,
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
    story = add_metodology(
        story=story, text_h1="Metodologia", h1_style=h1_style, contents=metodology
    )

    # Imagens
    images = {
        "image1": {
            "path": "src/report/imgs/case_growth_line.png",
            "image_title": "Evolução dos Casos",
            "title_style": h2_style,
            "description": metrics["case_growth"],
            "description_style": body_style,
        },
        "image2": {
            "path": "src/report/imgs/mortality_rate_line.png",
            "image_title": "Taxa de Mortalidade",
            "title_style": h2_style,
            "description": metrics["mortality_rate"],
            "description_style": body_style,
        },
        "image3": {
            "path": "src/report/imgs/uti_utilization_rate_line.png",
            "image_title": "Taxa de utilização de UTI",
            "title_style": h2_style,
            "description": metrics["uti_utilization_rate"],
            "description_style": body_style,
        },
        "image4": {
            "path": "src/report/imgs/vaccination_rate_line.png",
            "image_title": "Cobertura Vacinal",
            "title_style": h2_style,
            "description": metrics["vaccination_rate"],
            "description_style": body_style,
        },
        "image5": {
            "path": "src/report/imgs/daily_cases_line.png",
            "image_title": "Número de casos diário - 30 dias",
            "title_style": h2_style,
            "description": metrics["daily_cases"],
            "description_style": body_style,
        },
        "image6": {
            "path": "src/report/imgs/monthly_cases_line.png",
            "image_title": "Número de casos mensal - 12 meses",
            "title_style": h2_style,
            "description": metrics["monthly_cases"],
            "description_style": body_style,
        },
    }

    story = add_metrics(
        story=story, text_h1="Avaliação de Métricas", h1_style=h1_style, images=images
    )

    # Resumo Final
    story = add_final_summary(
        story=story,
        text_h1="Visão integrada atual",
        h1_style=h1_style,
        content=[overall_summary, disagreements, consensus],
        content_style=body_style,
    )

    story = add_sources(
        story=story,
        h1_text="Fontes consultadas",
        h1_style=h1_style,
        sources=sources_covered,
        source_style=bullets_style,
    )
    doc.build(story)
    print("Relatório 'relatorio_srag.pdf' gerado com sucesso!")


def run():
    """Executes the complete workflow to generate the executive report.

    This function serves as the main entry point for the report generation process.
    It loads executive summary data from a JSON file, extracts metrics summaries,
    and then calls `generate_executive_report` to create the final PDF document.
    It relies on the `load_json` and `extrair_ia_summary` helper functions to prepare the data.

    Args:
        None: This function does not take any arguments.

    Returns:
        None: This function does not return a value. Its primary purpose is to generate a PDF file as a side effect.
    """
    base_dir = Path("src/report")
    summaries_path = base_dir / "summaries" / "news_summaries.json"
    metrics_path = base_dir / "metrics" / "static_metrics.json"

    executive_summary = load_json(json_path=summaries_path)
    executive_summary = executive_summary.get("executive_summary", {})

    overall_summary = executive_summary.get("overall_summary", {})
    high_lights = executive_summary.get("highlights", {})
    consensus = executive_summary.get("consensus", {})
    disagreements = executive_summary.get("disagreements", {})
    sources_covered = executive_summary.get("sources_covered", {})

    metrics_summaries = extrair_ia_summary(metrics_path)
    generate_executive_report(
        overall_summary=overall_summary,
        high_lights=high_lights,
        consensus=consensus,
        disagreements=disagreements,
        sources_covered=sources_covered,
        metrics=metrics_summaries,
    )
