"""
Export Service
--------------
Converts a Resource's structured_output JSON into PDF, DOCX, or PPTX files.

PDF  – WeasyPrint (renders an HTML template to PDF)
DOCX – python-docx (programmatic Word document)
PPTX – python-pptx (programmatic PowerPoint, slides only)
"""

import io
import json
from typing import Any

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from pptx import Presentation
from pptx.util import Inches, Pt as PptPt
from pptx.dml.color import RGBColor as PptRGB
from pptx.enum.text import PP_ALIGN

# Brand colour used for accents
BRAND_RGB = (59, 130, 246)  # blue-500


# ---------------------------------------------------------------------------
# PDF export – WeasyPrint
# ---------------------------------------------------------------------------

def export_pdf(resource: Any) -> bytes:
    """Render resource to HTML then convert to PDF bytes via WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed or its system dependencies are missing. "
            "Install WeasyPrint and ensure libcairo / libpango are available."
        ) from exc

    data = json.loads(resource.structured_output)
    html_content = _render_print_html(resource, data)
    css = CSS(string=_print_css())
    return HTML(string=html_content).write_pdf(stylesheets=[css])


def _print_css() -> str:
    return """
    @page { margin: 2cm; size: A4; }
    body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; color: #1f2937; line-height: 1.5; }
    h1 { font-size: 20pt; color: #1e3a5f; margin-bottom: 4pt; }
    h2 { font-size: 14pt; color: #1e40af; margin-top: 16pt; margin-bottom: 6pt; border-bottom: 1pt solid #93c5fd; padding-bottom: 3pt; }
    h3 { font-size: 12pt; color: #374151; margin-top: 10pt; margin-bottom: 4pt; }
    .meta { color: #6b7280; font-size: 9pt; margin-bottom: 12pt; }
    .section-card { border: 1pt solid #e5e7eb; border-radius: 6pt; padding: 10pt; margin-bottom: 10pt; }
    .question { margin-bottom: 8pt; }
    .marks { color: #6b7280; font-style: italic; font-size: 9pt; }
    .answer-space { border-bottom: 1pt solid #d1d5db; margin-top: 4pt; height: 12pt; }
    ul { margin: 4pt 0; padding-left: 18pt; }
    li { margin-bottom: 2pt; }
    table { width: 100%; border-collapse: collapse; margin-top: 8pt; }
    th { background: #eff6ff; text-align: left; padding: 6pt; font-size: 10pt; border: 1pt solid #bfdbfe; }
    td { padding: 6pt; border: 1pt solid #e5e7eb; font-size: 10pt; vertical-align: top; }
    .notes { background: #f9fafb; border-left: 3pt solid #93c5fd; padding: 6pt 10pt; font-size: 9pt; color: #4b5563; margin-top: 4pt; }
    """


def _render_print_html(resource: Any, data: dict) -> str:
    """Build an HTML string representing the resource for PDF rendering."""
    rtype = resource.type

    sections_html = ""
    if rtype == "lesson":
        sections_html = _lesson_html(data)
    elif rtype == "worksheet":
        sections_html = _worksheet_html(data)
    elif rtype == "scheme":
        sections_html = _scheme_html(data)
    elif rtype == "slides":
        sections_html = _slides_html(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>{resource.title}</title></head>
<body>
  <h1>{resource.title}</h1>
  <p class="meta">{resource.subject} &bull; {resource.key_stage} &bull; {resource.topic}</p>
  {sections_html}
</body>
</html>"""


def _lesson_html(data: dict) -> str:
    objs = "".join(f"<li>{o}</li>" for o in data.get("learning_objectives", []))
    resources = "".join(f"<li>{r}</li>" for r in data.get("resources_needed", []))
    diff = data.get("differentiation", {})

    sections = ""
    for s in data.get("sections", []):
        notes = f'<div class="notes">Teacher notes: {s["teacher_notes"]}</div>' if s.get("teacher_notes") else ""
        sections += f"""
        <div class="section-card">
          <h3>{s.get('title','')} <small style="color:#9ca3af;">({s.get('duration','')})</small></h3>
          <p>{s.get('activity','')}</p>
          {notes}
        </div>"""

    return f"""
    <h2>Learning Objectives</h2><ul>{objs}</ul>
    <h2>Lesson Sections</h2>{sections}
    <h2>Resources Needed</h2><ul>{resources}</ul>
    <h2>Differentiation</h2>
    <p><strong>Support:</strong> {diff.get('support','')}</p>
    <p><strong>Extension:</strong> {diff.get('extension','')}</p>
    <h2>Assessment</h2><p>{data.get('assessment','')}</p>"""


def _worksheet_html(data: dict) -> str:
    html = f"<p><strong>Instructions:</strong> {data.get('instructions','')}</p>"
    for section in data.get("sections", []):
        qs = ""
        for q in section.get("questions", []):
            lines = "".join(f'<div class="answer-space"></div>' for _ in range(q.get("answer_lines", 3)))
            qs += f"""
            <div class="question">
              <p><strong>Q{q['number']}.</strong> {q['question']}
                <span class="marks">({q.get('marks',1)} mark{'s' if q.get('marks',1)>1 else ''})</span>
              </p>
              {lines}
            </div>"""
        html += f"""
        <div class="section-card">
          <h3>{section.get('title','')}</h3>
          {qs}
        </div>"""
    return html


def _scheme_html(data: dict) -> str:
    html = f"<p>{data.get('overview','')}</p><h2>Weekly Overview</h2>"
    html += "<table><tr><th>Week</th><th>Topic</th><th>Objectives</th><th>Activities</th><th>Assessment</th></tr>"
    for w in data.get("weeks", []):
        objs = "<br>".join(w.get("objectives", []))
        acts = "<br>".join(w.get("key_activities", []))
        html += f"<tr><td><strong>Week {w['week']}</strong></td><td>{w.get('topic','')}</td><td>{objs}</td><td>{acts}</td><td>{w.get('assessment','')}</td></tr>"
    html += "</table>"
    return html


def _slides_html(data: dict) -> str:
    html = f"<p>{data.get('slide_count', 0)} slides</p>"
    for slide in data.get("slides", []):
        bullets = "".join(f"<li>{b}</li>" for b in slide.get("bullet_points", []))
        notes = f'<div class="notes">Speaker notes: {slide["speaker_notes"]}</div>' if slide.get("speaker_notes") else ""
        html += f"""
        <div class="section-card">
          <h3>Slide {slide['number']}: {slide.get('title','')}</h3>
          <ul>{bullets}</ul>
          {notes}
        </div>"""
    return html


# ---------------------------------------------------------------------------
# DOCX export – python-docx
# ---------------------------------------------------------------------------

def export_docx(resource: Any) -> bytes:
    data = json.loads(resource.structured_output)
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    rtype = resource.type
    if rtype == "lesson":
        _docx_lesson(doc, resource, data)
    elif rtype == "worksheet":
        _docx_worksheet(doc, resource, data)
    elif rtype == "scheme":
        _docx_scheme(doc, resource, data)
    else:
        _docx_generic(doc, resource, data)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def _docx_lesson(doc: Document, resource: Any, data: dict) -> None:
    _add_heading(doc, data.get("title", resource.title), 1)
    doc.add_paragraph(
        f"Subject: {resource.subject}  |  Key Stage: {resource.key_stage}  "
        f"|  Duration: {data.get('duration', '60 minutes')}"
    ).runs[0].italic = True

    _add_heading(doc, "Learning Objectives", 2)
    for obj in data.get("learning_objectives", []):
        doc.add_paragraph(obj, style="List Bullet")

    _add_heading(doc, "Lesson Sections", 2)
    for s in data.get("sections", []):
        doc.add_heading(f"{s.get('title','')}  ({s.get('duration','')})", 3)
        doc.add_paragraph(s.get("activity", ""))
        if s.get("teacher_notes"):
            note_para = doc.add_paragraph(f"Teacher notes: {s['teacher_notes']}")
            note_para.runs[0].italic = True
            note_para.runs[0].font.color.rgb = RGBColor(75, 85, 99)

    _add_heading(doc, "Resources Needed", 2)
    for r in data.get("resources_needed", []):
        doc.add_paragraph(r, style="List Bullet")

    diff = data.get("differentiation", {})
    if diff:
        _add_heading(doc, "Differentiation", 2)
        doc.add_paragraph(f"Support: {diff.get('support', '')}")
        doc.add_paragraph(f"Extension: {diff.get('extension', '')}")

    _add_heading(doc, "Assessment", 2)
    doc.add_paragraph(data.get("assessment", ""))


def _docx_worksheet(doc: Document, resource: Any, data: dict) -> None:
    _add_heading(doc, data.get("title", resource.title), 1)
    doc.add_paragraph(
        f"Subject: {resource.subject}  |  Key Stage: {resource.key_stage}  |  Topic: {resource.topic}"
    ).runs[0].italic = True
    doc.add_paragraph()
    doc.add_paragraph(f"Instructions: {data.get('instructions', '')}").runs[0].bold = True

    q_num = 0
    for section in data.get("sections", []):
        _add_heading(doc, section.get("title", ""), 2)
        for q in section.get("questions", []):
            q_num += 1
            marks = q.get("marks", 1)
            para = doc.add_paragraph()
            run = para.add_run(f"Q{q['number']}. ")
            run.bold = True
            para.add_run(f"{q['question']} ({marks} mark{'s' if marks > 1 else ''})")
            for _ in range(q.get("answer_lines", 3)):
                line_para = doc.add_paragraph("_" * 80)
                line_para.paragraph_format.space_before = Pt(2)
                line_para.paragraph_format.space_after = Pt(2)
                line_para.runs[0].font.color.rgb = RGBColor(209, 213, 219)


def _docx_scheme(doc: Document, resource: Any, data: dict) -> None:
    _add_heading(doc, data.get("title", resource.title), 1)
    doc.add_paragraph(
        f"Subject: {resource.subject}  |  Key Stage: {resource.key_stage}  |  Duration: {data.get('duration','6 weeks')}"
    ).runs[0].italic = True
    doc.add_paragraph(data.get("overview", ""))

    _add_heading(doc, "Weekly Overview", 2)
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Week", "Topic", "Objectives", "Activities", "Assessment"]):
        hdr[i].text = h
        hdr[i].paragraphs[0].runs[0].bold = True

    for w in data.get("weeks", []):
        row = table.add_row().cells
        row[0].text = str(w.get("week", ""))
        row[1].text = w.get("topic", "")
        row[2].text = "\n".join(w.get("objectives", []))
        row[3].text = "\n".join(w.get("key_activities", []))
        row[4].text = w.get("assessment", "")


def _docx_generic(doc: Document, resource: Any, data: dict) -> None:
    _add_heading(doc, data.get("title", resource.title), 1)
    doc.add_paragraph(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# PPTX export – python-pptx (slides type only)
# ---------------------------------------------------------------------------

def export_pptx(resource: Any) -> bytes:
    data = json.loads(resource.structured_output)
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)

    slides_data = data.get("slides", [])
    if not slides_data:
        raise ValueError("No slides found in structured output. PPTX export is only available for Slide Outline resources.")

    blank_layout = prs.slide_layouts[6]  # completely blank

    for slide_data in slides_data:
        slide = prs.slides.add_slide(blank_layout)
        _build_pptx_slide(slide, slide_data, prs)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _build_pptx_slide(slide: Any, data: dict, prs: Presentation) -> None:
    content_type = data.get("content_type", "content")

    # Background rectangle (white)
    bg = slide.shapes.add_shape(1, Inches(0), Inches(0), prs.slide_width, prs.slide_height)
    bg.fill.solid()
    bg.fill.fore_color.rgb = PptRGB(255, 255, 255)
    bg.line.fill.background()

    # Top accent bar (brand blue)
    bar_h = Inches(0.08)
    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), prs.slide_width, bar_h)
    bar.fill.solid()
    bar.fill.fore_color.rgb = PptRGB(*BRAND_RGB)
    bar.line.fill.background()

    # Slide number chip
    num_box = slide.shapes.add_textbox(Inches(0.2), Inches(0.15), Inches(0.5), Inches(0.35))
    num_tf = num_box.text_frame
    num_p = num_tf.paragraphs[0]
    num_run = num_p.add_run()
    num_run.text = str(data.get("number", ""))
    num_run.font.size = PptPt(10)
    num_run.font.color.rgb = PptRGB(107, 114, 128)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.6), Inches(12.3), Inches(1.2))
    tf = title_box.text_frame
    tf.word_wrap = True
    title_para = tf.paragraphs[0]
    title_run = title_para.add_run()
    title_run.text = data.get("title", "")
    title_run.font.size = PptPt(28) if content_type == "title" else PptPt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = PptRGB(30, 58, 95)

    # Bullet points
    content_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), Inches(8.8), Inches(4.5))
    content_tf = content_box.text_frame
    content_tf.word_wrap = True

    for i, bullet in enumerate(data.get("bullet_points", [])):
        if i == 0:
            para = content_tf.paragraphs[0]
        else:
            para = content_tf.add_paragraph()
        para.level = 0
        run = para.add_run()
        run.text = f"• {bullet}"
        run.font.size = PptPt(16)
        run.font.color.rgb = PptRGB(31, 41, 55)
        para.space_before = PptPt(4)

    # Speaker notes
    if data.get("speaker_notes"):
        notes_box = slide.shapes.add_textbox(Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.7))
        notes_tf = notes_box.text_frame
        notes_tf.word_wrap = True
        notes_para = notes_tf.paragraphs[0]
        notes_run = notes_para.add_run()
        notes_run.text = f"Notes: {data['speaker_notes']}"
        notes_run.font.size = PptPt(9)
        notes_run.font.italic = True
        notes_run.font.color.rgb = PptRGB(107, 114, 128)

        # Divider above notes
        divider = slide.shapes.add_shape(1, Inches(0.5), Inches(6.5), Inches(12.3), Inches(0.01))
        divider.fill.solid()
        divider.fill.fore_color.rgb = PptRGB(229, 231, 235)
        divider.line.fill.background()
