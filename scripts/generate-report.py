"""Build the assessment report with rendered diagrams, real evidence and source text.

Requires reportlab and Pillow. Run from any directory; output stays under artifacts.
"""
from pathlib import Path
from datetime import datetime, timezone
import html
import re
import textwrap
import json
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Preformatted
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon, Circle, Ellipse
from reportlab.graphics import renderSVG
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts'
DIAGRAMS = ROOT / 'docs' / 'diagrams'
OUT.mkdir(exist_ok=True)
DIAGRAMS.mkdir(exist_ok=True)
GREEN = colors.HexColor('#205d46')
PALE = colors.HexColor('#edf3ec')
INK = colors.HexColor('#24372f')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='CoverTitle', fontName='Helvetica-Bold', fontSize=28, leading=34, textColor=GREEN, spaceAfter=20))
styles.add(ParagraphStyle(name='Copy', fontName='Helvetica', fontSize=9, leading=13, spaceAfter=7, textColor=INK))
styles.add(ParagraphStyle(name='Cell', parent=styles['Copy'], fontSize=8, leading=11, spaceAfter=0))
styles.add(ParagraphStyle(name='Source', fontName='Courier', fontSize=6.4, leading=8.2, spaceAfter=8))
styles.add(ParagraphStyle(name='Caption', parent=styles['Copy'], fontSize=8, alignment=TA_CENTER, textColor=GREEN))
for name in ('Heading1', 'Heading2', 'Heading3'):
    styles[name].textColor = GREEN
    styles[name].keepWithNext = True

def clean(value):
    return str(value).replace('\u2014', ' - ').replace('\u2013', '-').replace('\u2011', '-').replace('\u2192', ' > ')

def inline(value):
    value = html.escape(clean(value))
    value = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', value)
    value = re.sub(r'`([^`]+)`', r'<font face="Courier">\1</font>', value)
    value = re.sub(r'\[([^]]+)\]\((https?://[^)]+)\)', r'<link href="\2" color="#205d46">\1</link>', value)
    return value

def para(value, style='Copy'):
    return Paragraph(inline(value), styles[style])

def box(d, x, y, width, height, title, lines=()):
    d.add(Rect(x, y, width, height, rx=7, ry=7, fillColor=PALE, strokeColor=GREEN, strokeWidth=1))
    d.add(String(x+width/2, y+height-20, title, textAnchor='middle', fontName='Helvetica-Bold', fontSize=11, fillColor=GREEN))
    for i, line in enumerate(lines):
        d.add(String(x+width/2, y+height-38-i*14, line, textAnchor='middle', fontName='Helvetica', fontSize=9, fillColor=INK))

def arrow(d, x1, y1, x2, y2):
    from math import atan2, cos, sin, pi
    d.add(Line(x1,y1,x2,y2,strokeColor=GREEN,strokeWidth=1.2))
    angle=atan2(y2-y1,x2-x1)
    d.add(Polygon([x2,y2,x2-7*cos(angle-pi/6),y2-7*sin(angle-pi/6),x2-7*cos(angle+pi/6),y2-7*sin(angle+pi/6)],fillColor=GREEN,strokeColor=GREEN))

def diagram(kind):
    d=Drawing(600,360)
    if kind=='architecture':
        box(d,10,240,170,85,'Staff web portal',['React + Bootstrap','Backoffice / Grid Operator'])
        box(d,10,90,170,95,'Native Android',['Java activities + SQLite','Prosumer / Grid Operator','Maps SDK + QR scanner'])
        box(d,225,165,165,110,'C# API on IIS',['JWT + role authorization','Account / Grid / Booking','Authoritative business rules'])
        box(d,435,165,155,110,'MongoDB replica set',['Users / nodes / slots','Reservations / audit','Atomic transactions'])
        arrow(d,180,270,225,240); arrow(d,180,135,225,195); arrow(d,390,220,435,220)
        d.add(String(190,294,'REST / JWT',fontSize=9,fillColor=GREEN))
        d.add(String(205,38,'Both clients use the API; neither connects directly to MongoDB.',fontSize=9,textAnchor='middle',fillColor=INK))
    elif kind=='use-cases':
        d.add(Rect(175,12,415,336,fillColor=None,strokeColor=GREEN))
        d.add(String(380,333,'Solara system boundary',textAnchor='middle',fontName='Helvetica-Bold',fontSize=10,fillColor=GREEN))
        rows=[(278,'Backoffice',['Manage users and activate accounts','Manage nodes and slots','Review reservations and dashboards']),
              (178,'Grid Operator',['Manage slots and review reservations','Scan QR and complete energy transfer','Monitor bookings and history']),
              (78,'Prosumer',['Register, edit profile and deactivate','Reserve, modify and cancel','View history, QR and nearby nodes'])]
        for y,title,lines in rows:
            d.add(Circle(85,y+20,8,fillColor=None,strokeColor=GREEN))
            for x1,y1,x2,y2 in [(85,y+12,85,y-12),(60,y,110,y),(85,y-12,65,y-35),(85,y-12,105,y-35)]:
                d.add(Line(x1,y1,x2,y2,strokeColor=GREEN))
            d.add(String(85,y-48,title,textAnchor='middle',fontSize=10,fillColor=INK))
            for i,line in enumerate(lines):
                cy=y+30-i*30
                d.add(Line(110,y,205,cy,strokeColor=GREEN,strokeWidth=0.7))
                d.add(Ellipse(390,cy,185,13,fillColor=PALE,strokeColor=GREEN))
                d.add(String(390,cy-3,line,textAnchor='middle',fontSize=9,fillColor=INK))
    elif kind=='data-flow':
        box(d,10,245,170,80,'1. Validate request',['Role / owner / active account','Seven-day / twelve-hour rules'])
        box(d,215,245,170,80,'2. Claim capacity',['Node active / slot available','Energy + battery limits'])
        box(d,420,245,170,80,'3. Persist booking',['Pending reservation','Audit record + summary'])
        arrow(d,180,285,215,285); arrow(d,385,285,420,285)
        box(d,15,140,160,65,'Users',['NIC / role / status'])
        box(d,215,140,170,65,'Nodes + slots',['Reserved kWh / count'])
        box(d,420,140,170,65,'Reservations + audit',['State / nonce / events'])
        arrow(d,95,245,95,205); arrow(d,300,245,300,205); arrow(d,505,245,505,205)
        box(d,105,20,390,80,'4. Verify QR and complete transfer',['Signed QR + current approved state + time window','Single transaction updates booking, slot counters and audit'])
        arrow(d,505,140,460,100); arrow(d,300,100,300,140)
    else:
        box(d,10,240,170,85,'Users',['_id: NIC or staff ID','unique email / role / status'])
        box(d,420,240,170,85,'SolarStationInfo',['_id: station ID','GPS / capacity / active'])
        box(d,420,100,170,90,'EnergyBookingSlots',['stationId -> node','UTC start/end / capacity'])
        box(d,215,100,170,110,'EnergyReservations',['prosumerId -> user','stationId / slotId','status / nonce / completion'])
        box(d,10,25,170,85,'AuditLog',['actor / action / entityId','UTC timestamp'])
        arrow(d,180,260,245,210); arrow(d,505,240,505,190); arrow(d,420,145,385,145); arrow(d,215,110,180,75)
    renderSVG.drawToFile(d, str(DIAGRAMS / (kind+'.svg')))
    d.scale(0.8,0.8); d.width=480; d.height=288
    return d

story=[]
story.extend([Spacer(1,55),para('SOLARA','CoverTitle'),para('Smart Solar Microgrid<br/>Trading System','CoverTitle'),para('SE4040 - Enterprise Application Development','Heading2'),Spacer(1,20)])
for member in ['IT22264220 - Kojithan P.Y','IT22172600 - Baskaran V','IT22223876 - Nishara T']:
    story.append(para(member))
story += [Spacer(1,25),para('Repository: https://github.com/EADSE4040/EAD---SE4040'),para('Generated: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')),
          para('Evidence report. Open verification and contribution items are identified explicitly. Complete those items before submission.'),PageBreak()]

diagram_index=0
def markdown(filename):
    global diagram_index
    lines=(ROOT/filename).read_text(encoding='utf-8-sig').splitlines()
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('```'):
            language=line[3:]; code=[]; i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i+=1
            if language=='mermaid':
                kinds=['architecture','use-cases','data-flow']
                if diagram_index<len(kinds): story.append(diagram(kinds[diagram_index]))
                else: story.append(para('Pending -> Approved -> Completed; pending/approved requests may become Cancelled or Expired. Rejection ends a pending request. Editing an approved request returns it to Pending and invalidates its QR.'))
                diagram_index+=1
            else:
                story.append(Preformatted('\n'.join(clean(x) for x in code),styles['Source'],maxLineLength=112))
        elif line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-: ]+',x) for x in cells): rows.append([para(x,'Cell') for x in cells])
                i+=1
            if rows:
                count=max(map(len,rows)); rows=[r+[para('','Cell')]*(count-len(r)) for r in rows]
                table=Table(rows,colWidths=[480/count]*count,repeatRows=1,hAlign='LEFT')
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ccd8ce')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
                story.extend([table,Spacer(1,10)])
            continue
        elif line.startswith('#'):
            level=len(line)-len(line.lstrip('#'))
            story.append(para(line.lstrip('#').strip(),'Heading'+str(min(level,3))))
        elif line:
            line=re.sub(r'^- \[[ x]\] ', '- ',line)
            story.append(para(line))
        i+=1

markdown('docs/design.md')
story += [para('Database relationships','Heading2'),diagram('database-model'),PageBreak()]
for filename in ['docs/verification.md','docs/contributions.md','docs/deployment/iis.md','docs/submission.md']:
    markdown(filename); story.append(PageBreak())
story.append(para('Captured deployment and persistence records','Heading1'))
for name in ['iis-configuration.json','deployment.json','android-persistence.json','android-workflow.json']:
    evidence=ROOT/'docs/evidence'/name
    if evidence.exists():
        story.append(para(name,'Heading2'))
        record=json.loads(evidence.read_text(encoding='utf-8-sig'))
        story.append(Preformatted(json.dumps(record,indent=2,ensure_ascii=True),styles['Source'],maxLineLength=112))
story.append(PageBreak())
story.append(para('Application and deployment screenshots','Heading1'))
for screenshot in sorted((ROOT/'docs/screenshots').glob('*.png')):
    story.append(para(screenshot.stem.replace('-',' ').title(),'Heading2'))
    with PILImage.open(screenshot) as im: width,height=im.size
    ratio=min(480/width,510/height)
    story.append(Image(str(screenshot),width=width*ratio,height=height*ratio))
    story.append(para('Actual captured application/evidence screen. Demonstration records are synthetic.','Caption'))
    story.append(PageBreak())
story.append(para('References','Heading1'))
readme=(ROOT/'README.md').read_text(encoding='utf-8-sig')
for line in readme.split('## References',1)[-1].splitlines():
    if line.strip(): story.append(para(line.strip()))
story.append(PageBreak())
story.append(para('Source code appendix','Heading1'))
story.append(para('Readable source text follows. Generated files, dependencies, secrets and build outputs are excluded. Long lines are wrapped for the page.'))
excluded={'.git','.tools','node_modules','bin','obj','build','dist','.gradle','artifacts'}
extensions={'.cs','.java','.jsx','.js','.css','.xml','.gradle','.csproj'}
for source in sorted(ROOT.rglob('*')):
    relative=source.relative_to(ROOT)
    if source.suffix not in extensions or any(part in excluded for part in relative.parts) or not source.is_file(): continue
    story.append(para(relative.as_posix(),'Heading3'))
    wrapped=[]
    for line in source.read_text(encoding='utf-8-sig').splitlines():
        wrapped.extend(textwrap.wrap(clean(line.expandtabs(4)),width=112,replace_whitespace=False,drop_whitespace=False) or [''])
    story.append(Preformatted('\n'.join(wrapped),styles['Source']))

def footer(canvas,doc):
    canvas.saveState(); canvas.setStrokeColor(GREEN); canvas.line(54,42,A4[0]-54,42)
    canvas.setFont('Helvetica',8); canvas.setFillColor(INK)
    canvas.drawString(54,29,'SOLARA | SE4040 | Project evidence and source')
    canvas.drawRightString(A4[0]-54,29,str(doc.page)); canvas.restoreState()

pdf=OUT/'Solara-SE4040-Report.pdf'
doc=SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=48,bottomMargin=58,title='Solara - SE4040 Project Report',author='Kojithan P.Y; Baskaran V; Nishara T')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Generated '+str(pdf))
