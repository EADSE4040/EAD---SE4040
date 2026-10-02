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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, Preformatted, KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents
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
styles.add(ParagraphStyle(name='Copy', fontName='Helvetica', fontSize=10, leading=15, spaceAfter=8, textColor=INK))
styles.add(ParagraphStyle(name='Cell', parent=styles['Copy'], fontSize=8, leading=11, spaceAfter=0))
styles.add(ParagraphStyle(name='Source', fontName='Courier', fontSize=6.7, leading=8.6, spaceAfter=8))
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
        d.add(String(300,38,'Both clients use the API; neither connects directly to MongoDB.',fontSize=9,textAnchor='middle',fillColor=INK))
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
story.extend([Spacer(1,62),para('SOLARA','CoverTitle'),
              para('Smart Solar Microgrid','CoverTitle'),para('Trading System','CoverTitle'),
              Spacer(1,12),para('Technical Project Report','Heading2'),
              para('SE4040 | Enterprise Application Development'),
              para('BSc (Hons) in Information Technology - Software Engineering'),Spacer(1,30)])
for member in ['IT22264220 - Kojithan P.Y','IT22172600 - Baskaran V','IT22223876 - Nishara T']:
    story.append(para(member))
story += [Spacer(1,28),para('30 September 2026'),
          para('[Project repository](https://github.com/EADSE4040/EAD---SE4040)'),PageBreak()]
story.append(para('Contents','Heading1'))
toc=TableOfContents()
toc.levelStyles=[ParagraphStyle(name='TOCChapter',fontName='Helvetica',fontSize=10,leading=16,spaceBefore=6,leftIndent=0,firstLineIndent=0),
                 ParagraphStyle(name='TOCSection',fontName='Helvetica',fontSize=9,leading=13,leftIndent=15,firstLineIndent=0)]
story.extend([toc,PageBreak()])

diagram_index=0
def markdown(filename):
    global diagram_index
    lines=(ROOT/filename).read_text(encoding='utf-8-sig').splitlines()
    i=0
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('[diagram:'):
            kind=line[len('[diagram:'):-1]
            captions={'architecture':'Figure 1. Client-server architecture and central service boundary.',
                      'use-cases':'Figure 2. Actor responsibilities and supported use cases.',
                      'data-flow':'Figure 3. Reservation processing and persistent data stores.',
                      'database-model':'Figure 4. MongoDB collections and reference relationships.'}
            story.extend([diagram(kind),para(captions[kind],'Caption')])
        elif line=='[verification]':
            markdown('docs/report-verification.md')
        elif line=='[contributions]':
            markdown('docs/contributions.md')
        elif line=='[screenshots]':
            screenshots()
        elif line=='[references]':
            references()
        elif line=='[source]':
            sources()
        elif line.startswith('```'):
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
                widths={2:[150,330],3:[120,105,255]}.get(count,[480/count]*count)
                if filename=='docs/contributions.md': widths=[125,230,125]
                table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ccd8ce')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
                story.extend([table,Spacer(1,10)])
            continue
        elif line.startswith('#'):
            level=len(line)-len(line.lstrip('#'))
            title=line.lstrip('#').strip()
            if filename=='docs/report.md' and level==1 and len(story)>1 and not isinstance(story[-1],PageBreak):
                story.append(PageBreak())
            if filename=='docs/contributions.md':
                if level==1:
                    i+=1
                    continue
                level=3
            story.append(para(title,'Heading'+str(min(level,3))))
        elif line:
            line=re.sub(r'^- \[[ x]\] ', '- ',line)
            story.append(para(line))
        i+=1

def screenshots():
    # Place two portrait captures on a page; keep each desktop capture with its caption.
    mobile=[]
    desktop=[]
    for screenshot in sorted((ROOT/'docs/screenshots').glob('*.png')):
        with PILImage.open(screenshot) as im: width,height=im.size
        (mobile if height>width else desktop).append((screenshot,width,height))
    number=1
    for offset in range(0,len(mobile),2):
        cells=[]
        for shot,width,height in mobile[offset:offset+2]:
            scale=min(220/width,450/height)
            title=shot.stem.replace('android-','').replace('-',' ').capitalize()
            cells.append([Image(str(shot),width=width*scale,height=height*scale),
                          Spacer(1,10),para(f'Figure A{number}. Android: {title}.','Caption')])
            number+=1
        if len(cells)==1: cells.append('')
        table=Table([cells],colWidths=[240,240])
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.extend([table,Spacer(1,12),para('Captured application state using synthetic demonstration data.','Caption'),PageBreak()])
    for shot,width,height in desktop:
        scale=min(480/width,510/height)
        title=shot.stem.replace('-',' ').capitalize()
        story.extend([Image(str(shot),width=width*scale,height=height*scale),Spacer(1,10),
                      para(f'Figure A{number}. {title}.','Caption'),PageBreak()])
        number+=1

def references():
    # Retain stable primary references and their visible URLs for a printable report.
    readme=(ROOT/'README.md').read_text(encoding='utf-8-sig')
    for i,line in enumerate(readme.split('## References',1)[-1].splitlines()):
        match=re.search(r'\[([^]]+)\]\((https?://[^)]+)\)',line)
        if match:
            title,url=match.groups()
            story.append(para(title,'Heading3'))
            story.append(para(f'[{url}]({url})'))
    story.append(para('SE4040 Assignment 1 (2026), Smart Solar Microgrid Trading System. Module assignment brief, published 24 August 2026.'))

def sources():
    # Include readable source while excluding generated output and local secrets.
    story.append(para('The following listing contains application source as text. Dependencies, generated files, local credentials and build artifacts are excluded. Long lines are wrapped to fit the page.'))
    excluded={'.git','.tools','node_modules','bin','obj','build','dist','.gradle','artifacts','tmp','output','.codex','.agents'}
    extensions={'.cs','.java','.jsx','.js','.css','.xml','.gradle','.csproj'}
    for source in sorted(ROOT.rglob('*')):
        relative=source.relative_to(ROOT)
        if source.suffix not in extensions or any(part in excluded for part in relative.parts) or not source.is_file(): continue
        story.append(para(relative.as_posix(),'Heading3'))
        wrapped=[]
        for line in source.read_text(encoding='utf-8-sig').splitlines():
            wrapped.extend(textwrap.wrap(clean(line.expandtabs(4)),width=108,replace_whitespace=False,drop_whitespace=False) or [''])
        story.append(Preformatted('\n'.join(wrapped),styles['Source']))

markdown('docs/report.md')

def footer(canvas,doc):
    # Keep navigation consistent without placing technical status text in the footer.
    canvas.saveState()
    if doc.page>1:
        canvas.setFont('Helvetica',8); canvas.setFillColor(GREEN)
        canvas.drawString(54,A4[1]-30,'SOLARA / TECHNICAL PROJECT REPORT')
    canvas.setStrokeColor(colors.HexColor('#ccd8ce')); canvas.line(54,42,A4[0]-54,42)
    canvas.setFont('Helvetica',8); canvas.setFillColor(INK)
    canvas.drawString(54,29,'SE4040  |  September 2026')
    canvas.drawRightString(A4[0]-54,29,str(doc.page)); canvas.restoreState()

class ReportDocument(SimpleDocTemplate):
    # Resolve a clickable contents table and PDF outline during the multi-pass build.
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name == 'Heading1':
            text=flowable.getPlainText()
            if text=='Contents' or text=='Technical Project Report': return
            level=0 if flowable.style.name=='Heading1' else 1
            key='section-'+str(self.seq.nextf('section'))
            self.canv.bookmarkPage(key)
            self.notify('TOCEntry',(level,text,self.page,key))

pdf=OUT/'Solara-SE4040-Report.pdf'
doc=ReportDocument(str(pdf),pagesize=A4,leftMargin=54,rightMargin=54,topMargin=52,bottomMargin=58,title='Solara - Technical Project Report',author='Kojithan P.Y; Baskaran V; Nishara T')
doc.multiBuild(story,onFirstPage=footer,onLaterPages=footer)
print('Generated '+str(pdf))
