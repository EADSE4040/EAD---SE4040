"""Generate four source-grounded Solara design guides with vector diagrams."""
from pathlib import Path
import html
import json
import math
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'pdf'
QA = ROOT / 'tmp' / 'pdfs' / 'system-guides'
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts')
pdfmetrics.registerFont(TTFont('Guide', str(FONT / 'arial.ttf')))
pdfmetrics.registerFont(TTFont('GuideBold', str(FONT / 'arialbd.ttf')))
pdfmetrics.registerFontFamily('Guide', normal='Guide', bold='GuideBold')
INK = colors.HexColor('#193b33')
GREEN = colors.HexColor('#246b53')
PALE = colors.HexColor('#edf5ef')
BLUE = colors.HexColor('#eaf1fa')
GOLD = colors.HexColor('#fff4db')
LINE = colors.HexColor('#cbd9d2')
MUTED = colors.HexColor('#53675f')
W, H = landscape(A4)
CW = W - 84
styles = {
    'title': ParagraphStyle('title', fontName='GuideBold', fontSize=25, leading=30, textColor=INK, spaceAfter=12),
    'sub': ParagraphStyle('sub', fontName='Guide', fontSize=11, leading=16, textColor=MUTED, spaceAfter=10),
    'body': ParagraphStyle('body', fontName='Guide', fontSize=10.2, leading=14.5, textColor=INK, spaceAfter=7),
    'cell': ParagraphStyle('cell', fontName='Guide', fontSize=9.1, leading=12.4, textColor=INK),
    'small': ParagraphStyle('small', fontName='Guide', fontSize=8.4, leading=11.8, textColor=MUTED, spaceAfter=5),
    'box': ParagraphStyle('box', fontName='Guide', fontSize=9.3, leading=12.2, textColor=INK, alignment=TA_CENTER),
    'heading': ParagraphStyle('heading', fontName='GuideBold', fontSize=13, leading=17, textColor=GREEN, spaceBefore=7, spaceAfter=6),
    'code': ParagraphStyle('code', fontName='Courier', fontSize=9, leading=13, textColor=INK, spaceAfter=7),
}

def p(text, kind='body'):
    return Paragraph(text, styles[kind])

def table(headers, rows, widths=None):
    data = [[p('<b>'+html.escape(str(v))+'</b>', 'cell') for v in headers]]
    data += [[p(str(v), 'cell') for v in row] for row in rows]
    t = Table(data, colWidths=[CW*x for x in widths] if widths else None, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PALE), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), .4, LINE), ('LEFTPADDING', (0,0), (-1,-1), 9),
        ('RIGHTPADDING', (0,0), (-1,-1), 9), ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fafcfb')]),
    ]))
    return t

class Diagram(Flowable):
    """Coordinates use a top-left origin; content is rendered as sharp vector artwork."""
    def __init__(self, height=320):
        super().__init__()
        self.width, self.height = CW, height
        self.ops = []

    def box(self, x, y, w, h, title, body='', fill=PALE):
        self.ops.append(('box', x,y,w,h,title,body,fill)); return self

    def arrow(self, points, label='', lx=None, ly=None, dashed=False):
        self.ops.append(('arrow', points,label,lx,ly,dashed)); return self

    def label(self, x,y,w,text, kind='small'):
        self.ops.append(('label',x,y,w,text,kind)); return self

    def draw(self):
        c = self.canv
        for op in self.ops:
            if op[0] == 'box':
                _,x,y,w,h,title,body,fill = op
                c.setFillColor(fill); c.setStrokeColor(LINE); c.setLineWidth(.7)
                c.roundRect(x,self.height-y-h,w,h,7,stroke=1,fill=1)
                text = '<b>'+title+'</b>' + ('<br/>'+body if body else '')
                para = p(text, 'box'); _,ph = para.wrap(w-16,h)
                if ph > h-12: raise ValueError(f'Diagram box overflows: {title}: {ph} > {h-12}')
                para.drawOn(c,x+8,self.height-y-(h+ph)/2)
            elif op[0] == 'arrow':
                _,points,label,lx,ly,dashed = op
                c.setStrokeColor(GREEN); c.setFillColor(GREEN); c.setLineWidth(1.1)
                c.setDash(4,3) if dashed else c.setDash()
                path=c.beginPath(); path.moveTo(points[0][0],self.height-points[0][1])
                for x,y in points[1:]: path.lineTo(x,self.height-y)
                c.drawPath(path); c.setDash()
                x,y=points[-1]; px,py=points[-2]; angle=math.atan2(y-py,x-px)
                a=c.beginPath(); a.moveTo(x,self.height-y)
                for delta in (-.5,.5):
                    a.lineTo(x-7*math.cos(angle+delta),self.height-y+7*math.sin(angle+delta))
                a.close(); c.drawPath(a,fill=1,stroke=0)
                if label:
                    para=p(label,'small'); _,ph=para.wrap(145,40)
                    para.drawOn(c,lx,self.height-ly-ph)
            else:
                _,x,y,w,text,kind = op
                para=p(text,kind); _,ph=para.wrap(w,100)
                para.drawOn(c,x,self.height-y-ph)

def footer(c, doc):
    c.setStrokeColor(LINE); c.line(42,35,W-42,35)
    c.setFillColor(MUTED); c.setFont('Guide',8)
    c.drawString(42,22,'SOLARA  /  '+doc.guide_name+'  /  Current implementation - 10 October 2026')
    c.drawRightString(W-42,22,str(doc.page))

class Guide:
    def __init__(self, filename, name):
        self.filename, self.name, self.story, self.sections = filename,name,[],[]
    def page(self, title, subtitle='', items=()):
        if self.story: self.story.append(PageBreak())
        self.sections.append(title)
        self.story += [p(title,'title')]
        if subtitle: self.story += [p(subtitle,'sub')]
        self.story += list(items)
    def build(self):
        doc=SimpleDocTemplate(str(OUT/self.filename),pagesize=(W,H),rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,
                              title='Solara - '+self.name,author='Solara project documentation',allowSplitting=1)
        doc.guide_name=self.name
        doc.build(self.story,onFirstPage=footer,onLaterPages=footer)
        return {'file':self.filename,'sections':self.sections,'expected_pages':len(self.sections)}

def notes(*lines):
    return [p(line) for line in lines]

def heading(text): return p(text,'heading')

def sources(paths):
    return [heading('Implementation references'),p('These are repository paths, not external product documentation. The code is the source of truth for this guide.','small'),
            *[p(html.escape(path),'small') for path in paths]]

def role_diagram():
    d=Diagram(280)
    d.box(0,0,230,64,'Prosumer / customer','Native Android application',BLUE)
    d.box(263,0,230,64,'Backoffice / Admin','React staff portal',PALE)
    d.box(526,0,230,64,'Grid Operator','Web portal + Android scanner',GOLD)
    d.box(0,96,230,174,'Personal energy journey','Register and maintain profile<br/>Browse active nodes / Sri Lanka map<br/>Select published slot and energy<br/>Create / modify / cancel own booking<br/>Track status and show approved QR',BLUE)
    d.box(263,96,230,174,'Administration + operations','Create staff / active prosumers<br/>Activate or deactivate accounts<br/>Register and manage nodes<br/>Publish and manage slots<br/>Book for a prosumer; review bookings<br/>Verify and complete transfers',PALE)
    d.box(526,96,230,174,'Station operations','View prosumer records<br/>Edit existing node specifications<br/>Publish and manage slots<br/>Book for a prosumer via web<br/>Approve / reject and cancel bookings<br/>Scan QR and record actual energy',GOLD)
    for x in (115,378,641): d.arrow([(x,64),(x,96)])
    return d

def workflow_diagram():
    d=Diagram(324)
    for x,w,t,fill in [(0,172,'PROSUMER',BLUE),(194,172,'ADMIN / OPERATOR',GOLD),(388,174,'API + DATABASE',PALE),(584,172,'STATION / TRANSFER',PALE)]:
        d.box(x,0,w,30,t,fill=fill)
    d.box(0,49,172,48,'1. Register','NIC, email, profile')
    d.box(194,49,172,48,'2. Activate customer','Admin only')
    d.box(194,113,172,56,'3. Prepare supply','Admin adds node;<br/>staff publishes future slot')
    d.box(0,113,172,56,'4. Choose and reserve','Slot + energy + direction')
    d.box(388,113,174,56,'5. Save Pending','Validate; hold capacity;<br/>write booking + audit')
    d.box(194,189,172,52,'6. Review booking','Approve or reject')
    d.box(388,189,174,52,'7. Approved QR','Server signs payload')
    d.box(0,265,172,48,'8. Present QR','Customer Android screen')
    d.box(584,189,172,52,'9. Staff scans QR','Live verification')
    d.box(584,265,172,48,'10. Record actual kWh','Complete in slot window')
    d.box(388,265,174,48,'11. Completed','Release holds; save history')
    d.arrow([(172,73),(194,73)])
    d.arrow([(280,97),(280,113)])
    d.arrow([(194,141),(172,141)])
    d.arrow([(172,156),(184,156),(184,174),(376,174),(376,141),(388,141)])
    d.arrow([(475,169),(475,183),(280,183),(280,189)])
    d.arrow([(366,215),(388,215)])
    d.arrow([(388,226),(378,226),(378,254),(86,254),(86,265)])
    d.arrow([(172,289),(182,289),(182,322),(574,322),(574,215),(584,215)])
    d.arrow([(670,241),(670,265)])
    d.arrow([(584,289),(562,289)])
    return d

def lifecycle_diagram():
    d=Diagram(290)
    d.box(0,86,140,60,'Pending','Energy + count held',BLUE)
    d.box(239,86,160,60,'Approved','Current QR is valid',PALE)
    d.box(609,86,147,60,'Completed','Actual transfer saved',PALE)
    d.box(0,202,140,56,'Rejected','Staff refuses request',GOLD)
    d.box(239,202,160,56,'Cancelled','Owner / staff withdraws',GOLD)
    d.box(475,202,160,56,'Expired','End time has passed',GOLD)
    d.arrow([(140,116),(239,116)],'Staff approves',150,90)
    d.arrow([(399,116),(609,116)],'Valid QR + actual kWh<br/>during scheduled window',422,70)
    d.arrow([(319,86),(319,26),(70,26),(70,86)],'Modify: return to Pending;<br/>replace QR; 12h notice',110,0)
    d.arrow([(46,146),(46,202)])
    d.arrow([(140,136),(205,136),(205,230),(239,230)])
    d.arrow([(319,146),(319,202)])
    d.arrow([(399,136),(555,136),(555,202)])
    d.arrow([(140,126),(190,126),(190,272),(555,272),(555,258)],dashed=True)
    d.label(55,166,130,'Pending-only review','small')
    d.label(361,162,155,'Expiry worker: every minute','small')
    d.label(280,273,210,'Pending also expires after slot end','small')
    return d

def sequence(names, messages, height=320):
    d=Diagram(height)
    n=len(names); bw=min(155,(CW-30*(n-1))/n); gap=(CW-n*bw)/(n-1) if n>1 else 0
    centers=[]
    for i,name in enumerate(names):
        x=i*(bw+gap); centers.append(x+bw/2)
        d.box(x,0,bw,43,name,fill=BLUE if i==0 else PALE)
        d.arrow([(x+bw/2,48),(x+bw/2,height-8)],dashed=True)
    for index,(src,dst,text) in enumerate(messages):
        y=73+index*((height-92)/max(1,len(messages)-1))
        d.arrow([(centers[src],y),(centers[dst],y)])
        left=min(centers[src],centers[dst]); width=abs(centers[src]-centers[dst])-10
        d.label(left+5,y-23,max(width,100),str(index+1)+'. '+text,'small')
    return d

def architecture_diagram():
    d=Diagram(310)
    d.box(0,0,225,68,'Staff browser','React 19.3 + Bootstrap 5.3<br/>Vite build / sessionStorage',BLUE)
    d.box(0,94,225,70,'Android device','Native Java 17 UI<br/>MapLibre + ZXing',BLUE)
    d.box(0,205,225,65,'Device-local SQLite','Encrypted session (AES-GCM)<br/>Reference cache',GOLD)
    d.box(285,20,220,63,'ASP.NET Core / .NET 10','JSON REST + JWT authentication<br/>Role authorization / validation')
    d.box(285,113,220,67,'Application services','Account / Grid / Reservation<br/>Central business rules')
    d.box(285,213,220,63,'Hosted background services','Indexes / first-admin bootstrap<br/>Reservation expiry every minute')
    d.box(565,112,191,82,'MongoDB replica set','5 named collections<br/>Snapshot + majority transactions<br/>Counters and history',GOLD)
    d.box(565,0,191,68,'External basemap','OpenFreeMap tiles<br/>OpenStreetMap data',BLUE)
    d.arrow([(225,34),(285,51)])
    d.arrow([(225,120),(254,120),(254,62),(285,62)])
    d.arrow([(115,164),(115,205)])
    d.arrow([(395,83),(395,113)])
    d.arrow([(505,147),(565,147)])
    d.arrow([(505,246),(548,246),(548,180),(565,180)])
    d.arrow([(225,145),(244,145),(244,5),(545,5),(545,34),(565,34)])
    d.label(0,284,CW,'Client-to-API: JSON REST; HTTPS for release. Database access is server-only. Maps are fetched directly by Android.','small')
    return d

def class_diagram():
    d=Diagram(300)
    d.box(0,0,220,60,'API controllers','Auth / Users / Stations<br/>Slots / Reservations',BLUE)
    d.box(267,0,220,60,'Request / view DTOs','DataAnnotations validation<br/>Safe UserView / BookingView',BLUE)
    d.box(0,94,220,144,'AccountService','Login / Register / CreateStaff<br/>Get / List / Profile / SetStatus<br/>DeactivateSelf')
    d.box(267,94,220,144,'GridService','Stations / Slots / Create / Update<br/>Active / CreateSlot / UpdateSlot<br/>DeleteSlot / Touch / NoOverlap')
    d.box(534,94,222,144,'ReservationService','Create / Update / Cancel / Decide<br/>Qr / Verify / Complete / List<br/>Dashboard / Claim / Release<br/>Owned / ValidateQr')
    d.box(267,260,220,35,'MongoStore','')
    d.arrow([(110,60),(110,94)])
    d.arrow([(110,60),(110,76),(377,76),(377,94)])
    d.arrow([(110,76),(645,76),(645,94)])
    d.arrow([(110,238),(110,278),(267,278)])
    d.arrow([(377,238),(377,260)])
    d.arrow([(645,238),(645,278),(487,278)])
    d.arrow([(534,210),(487,210)])
    d.arrow([(267,30),(220,30)])
    return d

def data_diagram():
    d=Diagram(305)
    d.box(0,0,225,110,'User / Users','PK: Id (NIC for prosumer)<br/>Name / Email / PasswordHash<br/>Role / Status / TokenVersion<br/>Phone / Address / CreatedAt',BLUE)
    d.box(531,0,225,110,'Station / SolarStationInfo','PK: Id<br/>Name / Address / GPS<br/>CapacityKw / BatterySlots<br/>Schedule / Active / Revision',BLUE)
    d.box(267,143,220,130,'Reservation / EnergyReservations','PK: Id<br/>Refs: ProsumerId, StationId, SlotId<br/>Start / End / EnergyKwh / Direction<br/>Status / QrNonce / Revision<br/>CompletedBy / At / TransferredKwh',PALE)
    d.box(531,170,225,110,'EnergySlot / EnergyBookingSlots','PK: Id; ref: StationId<br/>Start / End / CapacityKwh<br/>MaxBookings / ReservedKwh<br/>ReservedCount / Active',PALE)
    d.box(0,170,225,110,'AuditEntry / AuditLog','PK: Id; ref: ActorId<br/>Action / EntityId / At<br/>EntityId may refer to any<br/>business entity',GOLD)
    d.arrow([(112,110),(112,130),(330,130),(330,143)])
    d.label(115,113,185,'1 user : many reservations')
    d.arrow([(531,80),(436,80),(436,143)])
    d.label(314,82,210,'1 station : many reservations')
    d.arrow([(644,110),(644,170)])
    d.label(650,133,105,'1 : many slots')
    d.arrow([(531,221),(487,221)])
    d.label(466,286,290,'1 slot : many reservations (capacity limited)')
    return d

manifest=[]
g=Guide('01-solara-roles-and-workflows.pdf','Roles and workflows')
g.page('Roles and the complete workflow','01 / Plain-English guide to the current Solara implementation',[
    role_diagram(),Spacer(1,10),p('<b>Read in this order:</b> role permissions, setup, booking journey, lifecycle, QR transfer, and practical examples.'),
    p('User means Prosumer. Admin means Backoffice. Energy generation capacity uses kW; booked and transferred energy uses kWh. Physical battery/grid equipment is outside this software implementation.','small')])
g.page('Who can do what?','Permissions below describe the server API. The next page explains where each feature appears in the UI.',[
    table(['Function','Prosumer','Admin / Backoffice','Grid Operator'],[
        ['Register / profile / deactivate','Self-register; own profile; self-deactivate','Own profile; create staff and prosumers; activate/deactivate accounts','Own profile; view prosumer records'],
        ['Station / node management','View active nodes and map','Create, edit, activate, deactivate, archive','Edit existing nodes; cannot create or activate'],
        ['Trading slot management','View future slots','Publish, edit and archive unreserved slots','Publish, edit and archive unreserved slots'],
        ['Create reservation','For self only','For a selected active prosumer','For a selected active prosumer'],
        ['Modify / cancel reservation','Own Pending/Approved bookings; 12h notice','Any Pending/Approved booking; 12h notice','Any Pending/Approved booking; 12h notice'],
        ['Approve / reject request','No','Pending bookings before start','Pending bookings before start'],
        ['QR and transfer completion','Display own approved QR','Retrieve QR; verify; complete transfer','Retrieve QR; scan/verify; complete transfer'],
        ['History / dashboard','Own reservations; active-node count','All reservations and operational counts','All reservations and operational counts'],
    ],[.25,.25,.25,.25])])
g.page('Which application does each role use?','A permission in the API does not imply that every client displays a button for it.',[
    table(['Client / role','Visible functionality','Important distinction'],[
        ['Prosumer Android','Register/login; overview; create/modify/cancel bookings; details/history; approved QR; map; profile; account deactivation; connection settings','Booking status applies immediately when selected. Text search has a Search button.'],
        ['Admin web portal','Overview; reservations; node and slot management; user administration; profile; QR payload verification and completion','Prosumer login is directed to Android. Admin can create staff and active prosumer accounts.'],
        ['Grid Operator web portal','Overview; create/review/edit/cancel reservations; edit nodes; manage slots; verify/complete transfers; own profile','Create reservation selects an active prosumer. No customer-confirmation step is implemented.'],
        ['Staff Android','Operational dashboard/history; reservation details and review; QR camera scan/manual payload; complete transfer; map/profile','The current Android UI hides New reservation for staff. Staff create bookings through the web portal.'],
    ],[.20,.45,.35]),
    heading('Customer consent and staff-assisted booking'),
    p('The usual journey starts with a prosumer request. The current API also permits either staff role to create a Pending reservation on behalf of an active prosumer. It does not collect or enforce customer consent. For assisted phone/in-person requests, consent is an operating procedure rather than a software approval step.')])
g.page('End-to-end workflow diagram','Main successful path; alternate outcomes are explained on the following page.',[
    workflow_diagram(),p('Admin account activation and station registration are setup actions. Grid Operators can publish slots and review bookings. Staff-assisted creation enters the same Pending state as a customer-created request.','small')])
g.page('Reservation lifecycle','Pending and Approved both hold energy capacity and one booking/battery allocation.',[
    lifecycle_diagram(),
    table(['Action','Rule / effect'],[
        ['Modify','Owner or staff; old and new start must satisfy 12h notice. Revalidate new slot, release old hold, claim new hold, return to Pending and invalidate old QR.'],
        ['Terminal outcomes','Rejected, Cancelled, Completed and Expired release the reservation hold. History remains. Terminal reservations cannot be modified or cancelled.'],
    ],[.20,.80])])
g.page('Cancel, reject and expiry','These actions have different meanings and time rules.',[
    table(['Action','Who / eligible state','When / result'],[
        ['Cancel','Prosumer owner or either staff role; Pending or Approved','At least 12h before start; status Cancelled; capacity released; QR invalidated.'],
        ['Reject','Either staff role; Pending only','Before slot start; status Rejected; capacity released. This is the staff review decision.'],
        ['Expire','Background worker; Pending or Approved','After slot end; runs every minute and handles up to 500 candidates per pass; status Expired; capacity released.'],
        ['Complete','Either staff role; Approved only','Valid current QR, within start/end, positive actual energy no greater than reserved; status Completed.'],
    ],[.17,.36,.47]),
    heading('What date is the reservation for?'),
    p('A booking inherits the selected trading slot\'s start and end. The prosumer does not choose a separate appointment date. A new reservation start must be in the future and no more than seven days from server time. Exactly seven days is accepted.'),
    p('Example: selecting a slot on 12 October, 10:00-12:00 creates a booking for that window, even when the request is submitted on 10 October.')])
g.page('QR verification and energy transfer','The server creates a signed payload. Android draws the QR image; staff scan or enter its payload.',[
    sequence(['Customer Android','Staff scanner / web','REST API','MongoDB'],[
        (0,2,'GET approved booking /qr'),(2,0,'Signed v1 payload; render QR'),(1,2,'POST /reservations/verify'),
        (2,3,'Check current status and QR nonce'),(2,1,'Show verified booking details'),
        (1,2,'POST /complete + actual kWh'),(2,3,'Commit Completed + release hold + audit'),(2,1,'Return final transfer summary'),
    ],295),
    p('<b>Verification is not completion.</b> Verification can happen before the slot starts; completion must happen during the scheduled window. The current QR cannot complete a booking twice. For a 10 kWh reservation, 8 kWh may be recorded; 12 kWh is rejected.','small')])
g.page('Drop off, charging and the full-island map','Energy direction is a booking attribute; the physical transfer mechanism is not implemented.',[
    table(['Term / feature','Meaning in this project'],[
        ['DropOff','Energy from prosumer to microgrid/station. A compatible battery discharge or connected-grid export could implement this physically, but neither hardware model is specified in code.'],
        ['Charging','Energy from microgrid/station to the prosumer battery/storage. It is not explicitly an EV-car charging system.'],
        ['Energy measurements','Staff manually enter actual transferred kWh. No meter telemetry, inverter command, charger protocol, pricing or payment workflow is implemented.'],
        ['Prosumer map','Loads GET /stations without radius parameters. Shows active registered nodes across Sri Lanka and opens with the island in view. Location permission only displays the user position.'],
        ['Map freshness / limits','Refresh reloads station data; offline cache is labelled. Server station listing currently caps at 500 records. Demo/synthetic pins are not evidence of real stations.'],
    ],[.24,.76]),*sources(['backend/SolarTrading.Api/Controllers/ApiControllers.cs','backend/SolarTrading.Api/Services/ReservationService.cs and BusinessRules.cs','frontend/android/app/src/main/java/com/solara/microgrid/MainActivity.java and MapActivity.java','frontend/web/src/main.jsx'])])
manifest.append(g.build())

g=Guide('02-solara-system-architecture.pdf','System architecture and technology stack')
g.page('System architecture','02 / Deployment containers, communication paths and the technology stack',[
    architecture_diagram(),p('Solara is a client-server application with one central API and one authoritative MongoDB database. The API contains modular services, not separately deployed microservices.','small')])
g.page('Technology stack','Versions below are declared by the project manifests, not a claim about latest upstream releases.',[
    table(['Layer','Technology / project version','Purpose'],[
        ['Web interface','React + React DOM 19.3.0; Bootstrap 5.3.8; lucide-react ^0.468.0','Staff dashboards, operational forms, account administration and payload verification.'],
        ['Web build','Vite ^8.0.0; Node.js 22.12+ prerequisite; npm','Development server and production static bundle. API base URL supplied through VITE_API_URL.'],
        ['Android','Native Java 17; minSdk 26; compileSdk/targetSdk 36; workspace Gradle 8.13','Activities and native widgets. No React Native or Flutter dependency.'],
        ['Map / QR','MapLibre Android OpenGL 13.5.2; OpenFreeMap / OSM; ZXing embedded 4.3.0 + core 3.5.3','Map renderer, public basemap, QR rendering and camera scan.'],
        ['API','C#; ASP.NET Core / .NET 10; JWT Bearer package 10.0.12','REST controllers, dependency injection, validation, authorization, hosted workers.'],
        ['Authoritative data','MongoDB 8.0+ replica set prerequisite; MongoDB.Driver 3.12.0','Transactions across reservations, capacity counters and transactional audit events.'],
        ['Local data / security','Android SQLiteOpenHelper; Android Keystore AES-GCM; browser sessionStorage','Encrypted Android session, reference cache, browser-tab session state.'],
        ['Hosting / checks','Windows IIS + .NET 10 Hosting Bundle; Kestrel for local dev; .NET test runner; Vite build; Gradle lint','Deployment and verification. Exact installed tool versions may differ from manifest ranges.'],
    ],[.17,.44,.39])])
g.page('Runtime request architecture','Thin controllers delegate decisions to services; MongoDB remains unreachable from the client.',[
    sequence(['Browser / Android','ASP.NET pipeline','Application service','MongoDB replica set'],[
        (0,1,'HTTPS JSON + Bearer JWT'),(1,3,'Validate current user and token version'),(1,2,'Authorize role; bind validated DTO'),
        (2,3,'Read / conditional writes / transaction'),(3,2,'Commit or business conflict'),(2,1,'Safe view DTO / DomainException'),(1,0,'JSON result / Problem Details'),
    ],300),
    p('Pipeline order: error wrapper and response headers; CORS; authentication; authorization; rate limiter; mapped controllers. DatabaseInitializer and ReservationExpiryService run inside the API host.','small')])
g.page('Development and IIS deployment','These are configured deployment paths; this document does not assert that the services are live at reading time.',[
    table(['Component','Development','IIS / release path'],[
        ['Web portal','Vite at http://127.0.0.1:5173','IIS static bundle; local assessment web binding http://127.0.0.1:8081.'],
        ['REST API','dotnet run / Kestrel; http://localhost:5080/api','ASP.NET Core behind IIS; local assessment API binding http://127.0.0.1:8080/api.'],
        ['Database','Workspace Mongo at 127.0.0.1:27018, replicaSet=rs0','Configured Mongo connection string; production needs authenticated, restricted access and resilient replica-set deployment.'],
        ['Android emulator','http://10.0.2.2:5080/api for local dev','App default debug endpoint is http://10.0.2.2:8080/api for local IIS; adjustable in Connection settings.'],
        ['Physical Android device','USB adb reverse can map device localhost:5080 to the development API','Use a reachable trusted HTTPS endpoint for release. Debug alone permits HTTP.'],
        ['Release configuration','Ignored appsettings.Local.json and local tools','JWT/QR secrets and Mongo settings via secured host configuration; VITE_API_URL is baked into the web build.'],
    ],[.19,.35,.46]),
    p('The publish script prepares artifacts; it is not automatic production deployment. IIS sites use separate application pools. A local single-member replica set enables transactions but does not provide multi-server availability.','small')])
g.page('Trust boundaries and system scope','Implemented controls and explicit boundaries',[
    table(['Boundary','Implemented behavior / limit'],[
        ['Client to API','JWT signature, issuer, audience and expiry validation; account Active status and TokenVersion checked for every authenticated request. Staff roles and prosumer ownership enforced server-side.'],
        ['Credentials and QR','ASP.NET password hashing. JWT and QR use independent keys of at least 32 bytes. QR uses HMAC-SHA256 and a current booking nonce; QR verification requires live database state.'],
        ['API to database','Pooled singleton MongoClient; snapshot read concern and majority write concern for transactions. Clients never receive Mongo connection credentials.'],
        ['Device local storage','Session JSON encrypted with a non-exportable Keystore key. Reference cache is not uniformly encrypted; cached data cannot authorize mutations or transfers.'],
        ['Maps / hardware','Basemap calls go to OpenFreeMap. Registered pins come from the API. No real-time energy meter, charger, payment gateway or notification provider is integrated.'],
    ],[.24,.76]),*sources(['backend/SolarTrading.Api/Program.cs and SolarTrading.Api.csproj','backend/SolarTrading.Api/Repositories/MongoStore.cs','frontend/web/package.json and src/api.js','frontend/android/app/build.gradle and ApiClient.java / LocalStore.java','scripts/start-local.ps1, scripts/publish.ps1 and docs/deployment/iis.md'])])
manifest.append(g.build())

g=Guide('03-solara-high-level-design.pdf','High-level design (HLD)')
g.page('High-level design','03 / Responsibilities, data flows, rules and operational behavior',[
    role_diagram(),p('<b>Goal:</b> let active prosumers reserve published microgrid energy slots and let staff govern supply, review requests and verify completion. The central API owns all business decisions.'),
    p('Read this guide for module boundaries and behavior. Read the separate LLD for classes, fields, endpoint contracts and transaction algorithms.','small')])
g.page('Subsystem decomposition','One API deployment with cohesive service modules and two clients.',[
    table(['Subsystem','Responsibility','Main data / interactions'],[
        ['Account and identity','NIC-based registration, login, staff creation, activation, profile edits and session revocation','Users; safe UserView; JWT validation queries current account state.'],
        ['Grid supply','Node specifications, active state, future slots, overlap protection, node/battery constraints','SolarStationInfo + EnergyBookingSlots; stations feed both portal and mobile map.'],
        ['Reservation management','Create, modify, cancel, staff review, summaries, search, paging and dashboard','EnergyReservations + held slot counters; ownership and time rules.'],
        ['Transfer verification','Signed approved QR; live validation; one-time actual-energy completion','Current reservation nonce/status; scheduled window; completion actor/time/energy.'],
        ['Background maintenance','Index/bootstrap startup and periodic expiry of abandoned reservations','Mongo indexes; optional first Backoffice; expire and release holds every minute.'],
        ['Client presentation','Staff portal; native prosumer flow; operator scanning; full-island map; reference cache','REST only; browser sessionStorage; Android SQLite + Keystore.'],
    ],[.21,.40,.39])])
g.page('Logical data flow','Reservation creation moves through validation, capacity claim and persistence in one transaction.',[
    d:=Diagram(280),
    p('The arrows carry application data, not physical electricity. The station and slot records describe availability; they do not command hardware.','small')])
d.box(0,85,150,72,'Authenticated client','Slot / energy / direction<br/>Staff: target prosumer',BLUE)
d.box(205,0,190,70,'1. Validate caller + account','Prosumer owns target;<br/>active prosumer required')
d.box(205,100,190,70,'2. Claim capacity','Active station and slot;<br/>conditional counter update')
d.box(205,200,190,70,'3. Persist booking','Pending + copied slot times<br/>+ transactional audit')
d.box(478,0,278,58,'Users','Current account state / target identity',GOLD)
d.box(478,102,278,58,'Stations + EnergyBookingSlots','Availability / revision / reserved counters',GOLD)
d.box(478,202,278,58,'EnergyReservations + AuditLog','Booking state / history / actor action',GOLD)
d.arrow([(150,109),(181,109),(181,35),(205,35)])
d.arrow([(300,70),(300,100)]); d.arrow([(300,170),(300,200)])
for y in (35,135,235): d.arrow([(395,y),(478,y)])
d.arrow([(205,240),(75,240),(75,157)])
g.page('Supply setup and availability rules','Configuration is protected against concurrent reservations.',[
    table(['Operation','Business constraint','Outcome'],[
        ['Register / edit node','Valid GPS; finite capacity; positive battery slots; reducing batteries must not conflict with active slot booking limits','Store station metadata. CapacityKw is generation power; it is not directly substituted for slot kWh.'],
        ['Deactivate / archive node','Reject if any Pending or Approved reservation exists','Set Active=false; preserve station and booking history. Only Backoffice can perform lifecycle changes.'],
        ['Publish slot','Active node; future start; end after start; positive energy; booking limit within node battery slots; no overlapping active slot at same node','Store a future interval and capacity. Touch station revision to serialize conflicting writes.'],
        ['Edit / archive slot','Cannot edit or archive when ReservedCount > 0','Keep old booking contracts stable; archived slot keeps historical references.'],
        ['List/map supply','Prosumers see active nodes and future active slots from active nodes','Mobile map calls unfiltered /stations; full island viewport. Listings are capped at 500 records.'],
    ],[.22,.43,.35]),
    p('Availability: free energy = CapacityKwh - ReservedKwh; free bookings = MaxBookings - ReservedCount. Both DropOff and Charging use the same reservation counters in the current implementation.','small')])
g.page('Reservation policy and state design','The server uses UTC instants; clients display local time.',[
    lifecycle_diagram(),
    p('New booking: now &lt; start &lt;= now + 7 days. Modify/cancel: start &gt;= now + 12 hours. Modification must satisfy notice for both old and selected new slot. Review: only Pending and before start. Completion: start &lt;= now &lt;= end, Approved and valid QR.','small'),
    p('Actual transfer energy is positive and at most reserved energy. Cancellation, rejection, expiry and completion release the full reservation hold; completion records actual energy separately. The slot counters model current holds, not cumulative physical throughput.','small')])
g.page('Security, consistency and failure behavior','These describe implemented controls; they are not performance or uptime guarantees.',[
    table(['Concern','Current design'],[
        ['Authorization / ownership','Role attributes guard staff-only actions. Prosumer reservation reads/writes must match ActorId. UsersController restricts operators to prosumer records.'],
        ['Concurrent booking','Conditional slot update checks both count and energy; booking, counter and audit writes commit together. Mongo transaction retry handles conflicts. Station revision writes serialize supply/booking races.'],
        ['Session revocation','Account activation/deactivation increments TokenVersion. Old JWTs fail current-version validation. Android encrypts session; web stores it per tab.'],
        ['Input / transport','DTO validation + finite-value domain checks. Release Android requires HTTPS; configured CORS origins govern browser access. Login and registration limited to 20 requests/minute per IP.'],
        ['Errors / offline','Problem Details for business failures; database errors return 503. Offline map/reference cache is labelled. Booking and transfer mutations need the central API.'],
        ['Audit and expiry','Many operational mutations log actor/action/entity in the same transaction. Not every creation/profile action is audited. Expiry processes up to 500 candidates per pass; it is not an immediate real-time scheduler.'],
    ],[.23,.77])])
g.page('Capacity planning and known design limits','Current behavior versus possible future extensions',[
    table(['Current limit / behavior','Implication','Possible extension - not implemented'],[
        ['One API host, Mongo transactions','Simple deployment; database must be a replica set. Single-member local setup has no host redundancy.','Load-balanced API instances and multi-member Mongo deployment with coordinated operations.'],
        ['Node/user/slot list limit: 500; reservations paginated','Suitable for current project scale; map is not an unlimited catalogue. View() joins user and station per booking.','Paginate catalogues; batch booking joins; geospatial indexes if scale requires them.'],
        ['Staff-assisted booking without consent check','Staff can create a Pending booking for an active customer.','Explicit customer confirmation and consent history.'],
        ['Shared holds for both energy directions','No separate import/export inventory or network constraints. Completion releases reserved energy counters.','Direction-specific supply model and metered cumulative throughput.'],
        ['Manual actual-energy entry; no prices/payments','QR proves booking authenticity, not a hardware measurement or financial settlement.','Meter/charger integration, pricing, settlement and notifications.'],
    ],[.28,.36,.36]),*sources(['backend/SolarTrading.Api/Services/AccountService.cs, GridService.cs and ReservationService.cs','backend/SolarTrading.Api/Services/BusinessRules.cs and ReservationExpiryService.cs','backend/SolarTrading.Api/Program.cs and Repositories/MongoStore.cs','frontend/android/app/src/main/java/com/solara/microgrid/MapActivity.java'])])
manifest.append(g.build())

g=Guide('04-solara-low-level-design.pdf','Low-level design (LLD)')
g.page('Low-level component design','04 / Classes, storage schemas, APIs and transaction algorithms',[
    class_diagram(),p('DI lifetimes: MongoStore and TimeProvider are singleton; AccountService, GridService and ReservationService are scoped; startup and expiry tasks are hosted services. BusinessRules exposes static domain checks.','small'),
    p('Controllers share ApiController.Actor and Role from JWT claims. DTOs bind JSON and validate contracts; UserView and BookingView omit password hashes and QR nonces.','small')])
g.page('MongoDB entity relationships','References are string IDs managed by application logic; MongoDB does not enforce relational foreign keys.',[
    data_diagram(),p('User.Id is normalized NIC for prosumers and a 32-character generated GUID string for staff. Station, slot, reservation and audit identifiers also use GUID strings without hyphens. CompletedBy references a staff user.','small')])
g.page('Schema: accounts, stations and slots','Field names are C# properties; JSON responses use camelCase.',[
    table(['Entity / collection','Fields and types','Rules / indexing'],[
        ['User / Users','Id:string; Nic:string?; Name, Email, Phone, Address, PasswordHash, Role, Status:string; TokenVersion:int; CreatedAt:DateTime','Unique Email index; normalized lowercase email. Prosumer Id/Nic uppercase. Status Pending / Active / Deactivated. Role Prosumer / Backoffice / GridOperator.'],
        ['Station / SolarStationInfo','Id, Name, Address, Schedule:string; Latitude, Longitude, CapacityKw:double; BatterySlots, Revision:int; Active:bool','Latitude -90..90; longitude -180..180; capacity 0.01..1,000,000; batteries 1..10,000. Active defaults true. Revision increments to conflict with simultaneous operations.'],
        ['EnergySlot / EnergyBookingSlots','Id, StationId:string; Start, End:DateTime; CapacityKwh, ReservedKwh:double; MaxBookings, ReservedCount:int; Active:bool','Index StationId + Start. Capacity 0.01..1,000,000; count 1..10,000 and not above BatterySlots; no active interval overlap at a station.'],
    ],[.22,.43,.35]),
    heading('What the database is not storing'),
    p('There is no separate charger, vehicle, meter telemetry, tariff, invoice, payment, notification or customer-consent entity. Node Schedule is a text description; slot timestamps enforce actual booking windows.')])
g.page('Schema: reservations, audit and local cache','Reservation times are copied from the selected slot to preserve the booking contract.',[
    table(['Entity / store','Fields / relationships','Behavior'],[
        ['Reservation / EnergyReservations','Id, ProsumerId, StationId, SlotId:string; Start/End/CreatedAt/UpdatedAt:DateTime; EnergyKwh:double; Direction/Status/QrNonce:string; Revision:int; CompletedBy:string?; CompletedAt:DateTime?; TransferredKwh:double?','Indexes: ProsumerId + Status + Start; StationId + Status. Terminal history remains. Current QR nonce cleared when invalidated.'],
        ['AuditEntry / AuditLog','Id, ActorId, Action, EntityId:string; At:DateTime','Operational actor/action/entity log. Expiry uses actor system. Many mutations audit transactionally; coverage is not universal.'],
        ['Android / solara.db','cache(name TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at INTEGER NOT NULL)','Session is encrypted JSON encoded as Base64 IV:ciphertext. Station reference caches are plain JSON values. Sign-out clears cache rows.'],
        ['Web / sessionStorage','solara.session JSON: token + safe user + expiry','Per-tab session persistence. Logout removes key and resets in-memory data. No server-side browser session table.'],
    ],[.23,.43,.34]),
    p('Android key alias: solara.session. AES/GCM/NoPadding with a non-exportable Android Keystore secret key; unreadable session data is discarded. SQLite is a cache, not an offline transaction authority.','small')])
g.page('API contracts: identity and grid supply','All paths are relative to /api. P = active Prosumer; A = Backoffice; O = GridOperator; S = A or O.',[
    table(['Method / route','Role','Request / operation'],[
        ['POST /auth/register; POST /auth/login','Public','RegisterRequest (NIC/profile/password); LoginRequest (email/password). Register creates Pending; login requires Active.'],
        ['GET, PUT /auth/me; POST /auth/me/deactivate','Any; P for deactivate','Own UserView / ProfileRequest (name, phone, address). Self-deactivation revokes sessions.'],
        ['GET /users; POST /users/staff; POST /users/prosumers','S; A for create','Filtered safe accounts; O sees prosumers only. StaffRequest defines role; RegisterRequest creates active prosumer.'],
        ['PUT /users/{id}; POST /users/{id}/activate or deactivate','A','Edit prosumer profile; change account state and increment token version. Self-administration via this lifecycle endpoint is blocked.'],
        ['GET /stations; POST /stations; PUT /stations/{id}','Any; A create; S edit','StationRequest: name,address,latitude,longitude,capacityKw,batterySlots,schedule. GET optionally supports radius; mobile no longer supplies it.'],
        ['POST /stations/{id}/activate or deactivate; DELETE /stations/{id}','A','Soft lifecycle, history retained; deactivation blocked by Pending/Approved reservations.'],
        ['GET /slots; POST /stations/{id}/slots; PUT, DELETE /slots/{id}','Any list; S mutate','SlotRequest: start/end with offset, capacityKwh, maxBookings. Reserved slots cannot edit/archive.'],
    ],[.43,.14,.43])])
g.page('API contracts: reservations and QR','Creation returns Pending; approval is a separate staff action.',[
    table(['Method / route','Role','Contract / result'],[
        ['GET /reservations','Any','status/search/from/to/page/pageSize; own records for P. Result items,total,page,pageSize. Page size clamped 1..100.'],
        ['GET /reservations/dashboard','Any','pending, approvedFuture, completed, activeNodes. Reservation counts scoped to owner for P.'],
        ['POST /reservations','Any','slotId,energyKwh,direction (DropOff|Charging), optional prosumerId. P target is always actor; staff must specify active prosumer.'],
        ['PUT /reservations/{id}; POST /{id}/cancel','Owner or S','Update uses ReservationRequest; status returns Pending and QR is invalidated. Cancel requires 12h notice.'],
        ['POST /reservations/{id}/approve or reject','S','Pending-only decision before start; approval issues nonce; rejection releases capacity.'],
        ['GET /reservations/{id}/qr','Owner or S','qrCode,reservationId,expiresAt; valid Approved booking only. Android renders QR bitmap.'],
        ['POST /reservations/verify; POST /reservations/complete','S','QrRequest {qrCode}; CompleteRequest {qrCode,transferredKwh}. Returns safe BookingView.'],
        ['GET /health','Public','Mongo ping; healthy/database/utc fields. A database error is reported through error middleware.'],
    ],[.42,.14,.44])])
g.page('Create and modify: transaction algorithms','MongoStore.Transaction uses WithTransactionAsync with snapshot reads and majority writes.',[
    table(['Create reservation','Modify reservation'],[
        ['1. Choose target: actor for Prosumer; supplied prosumerId for staff. Reject missing target.','1. Load booking; enforce prosumer ownership. Require Pending/Approved state and old-start 12h notice.'],
        ['2. Begin transaction; require target to exist as an Active Prosumer.','2. Require original prosumer active; decrement old slot holds inside the transaction.'],
        ['3. Claim: read active slot; touch active station revision; atomically require ReservedCount &lt; MaxBookings and ReservedKwh &lt;= CapacityKwh - requested energy.','3. Claim selected new slot using the same conditional update. New start must be within 7 days and satisfy 12h notice.'],
        ['4. Increment ReservedCount by 1 and ReservedKwh by requested energy. Validate future start within 7 days; copy slot start/end into reservation.','4. Replace slot/station/time/energy/direction; set Pending; clear QrNonce; increment Revision and UpdatedAt.'],
        ['5. Insert Pending reservation and Reservation:Create audit; commit. Return joined BookingView.','5. Save booking + Reservation:Update audit; commit. Any failure rolls back release and claim together.'],
    ],[.50,.50]),
    p('Cancelled/rejected/completed/expired reservations decrement the original held count and reserved energy. A failure after an attempted capacity update rolls back the entire transaction. Clients do not implement a separate capacity check as authority.','small')])
g.page('Concurrency and reservation invariants','A conditional write prevents oversubscription even when multiple clients see the same displayed availability.',[
    sequence(['Customer A','Customer B','API / transactions','Slot counters'],[
        (0,2,'Request last available capacity'),(1,2,'Request same capacity concurrently'),
        (2,3,'Conditional claim in transaction A'),(3,2,'A claims; counter update committed'),
        (2,3,'B retries conflict / rechecks counters'),(3,2,'B rejected: insufficient capacity'),
    ],270),
    p('<b>Invariants:</b> held count cannot exceed MaxBookings; held kWh cannot exceed CapacityKwh. Pending and Approved both hold capacity. Changes across booking/counter/audit commit atomically. Node revision writes also conflict with simultaneous deactivation and slot changes.','small'),
    p('This is a transaction-level guarantee, not HTTP request deduplication. No client idempotency key is implemented; repeated creation requests can create separate bookings if capacity allows.','small')])
g.page('QR payload and completion algorithm','A QR is a signed reference to live state, not a self-contained authorization ticket.',[
    p('Payload format: <b>v1.&lt;reservationId&gt;.&lt;nonce&gt;.&lt;signature&gt;</b>'),
    table(['Stage','Implementation'],[
        ['Approve / issue','Pending before start; require active prosumer; generate 16 random bytes as 32 hex characters. Increment reservation revision. QR endpoint signs v1.id.nonce with a dedicated HMAC-SHA256 key.'],
        ['Signature verification','Require four components: v1; 32-character booking ID; 32-character nonce; 64-character signature. Decode signature and compare HMAC in constant time.'],
        ['Live state validation','Booking exists; status Approved; nonce equals the QR nonce; now is not after end. For completion, now must also be at or after start.'],
        ['Complete transaction','Recheck live QR; actual energy positive/finite and &lt;= reserved. Release full hold; set Completed, CompletedBy, CompletedAt, TransferredKwh; clear nonce; increment revision; write audit.'],
        ['Replay / stale QR','Changed, cancelled, rejected, expired or completed booking cannot use the previous QR to complete. Verify can run before start; Complete cannot.'],
    ],[.24,.76]),
    p('The caller manually records actual kWh. Signature validity does not validate a meter reading, customer identity beyond the booking, or any payment.','small')])
g.page('Client implementation and validation details','These describe the latest workspace changes as well as existing behavior.',[
    table(['Component','Implementation detail'],[
        ['React Field / Modal','Shared number input: min=1 and step=1 for non-coordinate web fields; coordinates step=any. Modal turns numeric FormData into numbers and submits through src/api.js. Existing fractional API values are not rounded automatically.'],
        ['Numeric API distinction','Energy/power DTOs remain double with positive ranges; counts remain int. Android/API may still accept fractional energy. The web whole-number choice does not change physical units or backend schema.'],
        ['Android MainActivity','Status Spinner OnItemSelectedListener rebuilds the booking view when selected status changes. Initial selection is compared with current filter to avoid repeat reload. Search text retained; Search button handles explicit text search.'],
        ['Stale UI responses','MainActivity generation increments when shell changes; callbacks from previous screen generations are ignored. Reservation pagination loads 20 rows per page.'],
        ['Android MapActivity','GET /stations, no radius arguments; valid coordinates become GeoJSON features and a CircleLayer. Country bounds fit Sri Lanka plus returned station points; location update only changes the user indicator.'],
        ['Android ApiClient','Single worker executor; HttpURLConnection; 15s connect/read timeouts; Bearer token; JSON request/response; UI-thread callback. Executor stopped on close.'],
    ],[.26,.74])])
g.page('Validation, errors and verification boundaries','Use these cases to explain or verify the design; proposed checks below are not claims that they were run for this PDF.',[
    table(['Case','Expected result'],[
        ['Past or &gt;7-day booking start; &lt;12h modification/cancel','Reject per server clock; exact 7-day and 12h boundaries accepted.'],
        ['Maximum bookings exceeds node BatterySlots; slot overlap','Reject; changing dates/energy does not bypass battery count or overlap rules.'],
        ['Concurrent claim of last capacity; node deactivation race','At most supported holds commit; transaction conflict retries and active-node touch protect consistency.'],
        ['Prosumer reads or edits another booking; inactive session','Ownership denial; JWT rejected after deactivation/token-version change.'],
        ['Tampered/old QR; early completion; excessive actual kWh','Reject signature/state/window/energy violations. Second completion fails live state check.'],
        ['Map offline; status change; no location permission','Label cached map; status selection loads matching records; all active stations remain independent of user location.'],
    ],[.51,.49]),
    p('Error families: 400 validation/rules; 401 unauthenticated or invalid token; 403 role/ownership/inactive-login denial; 404 missing entity; 409 capacity/state conflict; 429 auth rate limit; 503 Mongo failure; 500 unexpected error.','small'),
    p('Repository validation entry points: backend/SolarTrading.Tests, npm run build in frontend/web, and Gradle assembleDebug lintDebug. No code changes or new test execution are implied by creating these guides.','small'),
    *sources(['backend/SolarTrading.Api/Models/Entities.cs and DTOs/Requests.cs','backend/SolarTrading.Api/Controllers/ApiControllers.cs and Repositories/MongoStore.cs','backend/SolarTrading.Api/Services/*.cs and Program.cs','frontend/web/src/main.jsx; Android MainActivity.java, MapActivity.java, LocalStore.java and ApiClient.java'])])
manifest.append(g.build())
(QA/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
