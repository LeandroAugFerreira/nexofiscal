"""Documentos locais de demonstração; não geram chave oficial, assinatura ou tributos."""
import base64
from io import BytesIO
from html import escape
from decimal import Decimal
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from xml.etree.ElementTree import Element, SubElement, tostring
import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, KeepTogether
from app.models.entities import Academy, Service, Charge

BRAND="NexoFiscal"
WATERMARK="DOCUMENTO SIMULADO — SEM VALIDADE FISCAL"
REFERENCE="Modelo demonstrativo inspirado na organização do DANFSe (NT 008/2026)."


def amount(value):
    text=format(Decimal(str(value)),",.2f")
    return "R$ "+text.replace(",","_").replace(".",",").replace("_",".")


def address(data):
    a=data.get("address") or {}
    return ", ".join(str(a.get(k)) for k in ("street","number","complement","neighborhood") if a.get(k)) or "Não informado"


def municipality(data):
    a=data.get("address") or {}
    return " / ".join(str(a.get(k)) for k in ("city","state") if a.get(k)) or "Não informado"


def federal_document(data):
    value=str(data.get('cnpj') or data.get('cpf') or '')
    if len(value)==14:return f'{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}'
    if len(value)==11:return f'{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}'
    return value or 'Não informado'


def person(data):
    return {k:getattr(data,k,None) for k in ("name","legal_name","cpf","cnpj","trade_name","municipal_registration","email","phone","address","tax_regime")}


def snapshot(db,invoice,client):
    issuer=db.get(Academy,invoice.academy_id)
    service=db.get(Service,invoice.service_id) if invoice.service_id else None
    return {"version":"nexofiscal-demo-1","identifier":invoice.identifier,"created_at":invoice.created_at.isoformat(),
        "competence":invoice.competence or (db.get(Charge,invoice.charge_id).competence if invoice.charge_id else "Não informado"),"amount":format(invoice.amount,".2f"),
        "description":invoice.service_description,"origin":invoice.origin,"issuer":person(issuer),"client":person(client),
        "service":service.name if service else invoice.service_description,"environment":"demonstracao",
        "verification":"Não existe chave de acesso fiscal oficial","qr_payload":f"NEXOFISCAL | DEMONSTRACAO | {invoice.identifier} | SEM VALIDADE FISCAL"}


def qr_png(data):
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=4,border=3)
    qr.add_data(data["qr_payload"]);qr.make(fit=True)
    output=BytesIO();qr.make_image(fill_color="black",back_color="white").save(output,format="PNG")
    return output.getvalue()


def display_time(data):
    instant=datetime.fromisoformat(data['created_at'])
    if instant.tzinfo is None:instant=instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M:%S')


def fields(data):
    issuer,client=data["issuer"],data["client"]
    return [
        ("PRESTADOR / EMITENTE",[("Razão social",issuer.get("legal_name") or issuer.get("name")),("CPF / CNPJ",federal_document(issuer)),("Inscrição municipal",issuer.get("municipal_registration") or "Não informado"),("Endereço",address(issuer)),("Município / UF",municipality(issuer)),("CEP",(issuer.get("address") or {}).get("cep") or "Não informado"),("E-mail",issuer.get("email") or "Não informado"),("Telefone",issuer.get("phone") or "Não informado"),("Regime informado",issuer.get("tax_regime") or "Não configurado")]),
        ("TOMADOR / CLIENTE",[("Nome / razão social",client.get("name")),("CPF / CNPJ",federal_document(client)),("Inscrição municipal",client.get("municipal_registration") or "Não informado"),("Endereço",address(client)),("Município / UF",municipality(client)),("CEP",(client.get("address") or {}).get("cep") or "Não informado"),("E-mail",client.get("email") or "Não informado"),("Telefone",client.get("phone") or "Não informado"),("Tipo de cliente","Pessoa jurídica" if client.get("cnpj") else "Pessoa física")]),
        ("TRIBUTAÇÃO MUNICIPAL - ISSQN",[("Enquadramento / código de serviço","Não parametrizado"),("Alíquota de ISS","Não calculada"),("ISS devido / retido","Não calculado"),("Base de cálculo tributária","Não calculada"),("Município de incidência","Não definido para emissão oficial"),("Retenção","Não avaliada no simulador")]),
        ("TRIBUTAÇÃO FEDERAL / IBS / CBS",[("PIS / COFINS / IR / CSLL","Não calculados"),("IBS / CBS","Não calculados"),("Tributos aproximados","Não apurados")]),
    ]


def html_document(data,cancelled=False):
    def cell(label,value):
        return f'<div class="field"><span>{escape(label)}</span><strong>{escape(str(value or "Não informado"))}</strong></div>'
    sections=""
    for title,rows in fields(data):
        sections+=f'<section><h2>{escape(title)}</h2><div class="grid">'+"".join(cell(k,v) for k,v in rows)+"</div></section>"
    # Serviço é colocado entre o tomador e a tributação.
    pivot='<section><h2>TRIBUTAÇÃO MUNICIPAL'
    service=f'<section><h2>SERVIÇO PRESTADO</h2><div class="description">{escape(data["description"]).replace(chr(10),"<br>")}</div></section>'
    sections=sections.replace(pivot,service+pivot)
    qr=base64.b64encode(qr_png(data)).decode()
    status="CANCELADA - SIMULAÇÃO" if cancelled else "DEMONSTRAÇÃO"
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(data['identifier'])} | NexoFiscal</title><style>
@page{{size:A4;margin:12mm}}*{{box-sizing:border-box}}body{{margin:0;background:#edf1f7;color:#16243a;font:11px Arial,sans-serif}}article{{position:relative;background:white;max-width:800px;margin:28px auto;padding:30px;border:1px solid #d7dfe9}}header{{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;border-bottom:2px solid #223c67;padding-bottom:14px}}header h1{{font-size:24px;margin:0 0 4px;letter-spacing:-.6px}}header p{{margin:3px 0;font-size:10px;color:#52627a}}header h3{{margin:0;font-size:14px}}.warning{{border:1px solid #d49730;color:#8b4b08;background:#fff8e9;padding:11px;text-align:center;font-weight:bold;margin:14px 0;font-size:11px}}.watermark{{position:absolute;top:45%;left:5%;width:90%;text-align:center;transform:rotate(-27deg);font-size:54px;color:rgba(31,57,104,.13);font-weight:bold;pointer-events:none;z-index:2}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0}}.field{{padding:9px;border-right:1px solid #d8dfe9;border-bottom:1px solid #d8dfe9;min-width:0}}.field span{{display:block;font-size:8px;color:#64728a;margin-bottom:5px}}.field strong{{font-size:10px;font-weight:500;overflow-wrap:anywhere}}section{{position:relative;border:1px solid #d8dfe9;border-bottom:0;margin-top:12px}}h2{{font-size:10px;margin:0;background:#edf1f6;padding:8px 9px;border-bottom:1px solid #d8dfe9;letter-spacing:.4px}}.identity{{display:grid;grid-template-columns:1fr 110px;gap:14px;margin-top:14px}}.identity .grid{{border:1px solid #d8dfe9;border-bottom:0;border-right:0}}.qr{{text-align:center;font-size:8px;color:#64728a}}.qr img{{width:86px;height:86px}}.description{{padding:13px;min-height:58px;font-size:11px;line-height:1.6;white-space:normal;overflow-wrap:anywhere;border-bottom:1px solid #d8dfe9}}.totals{{display:grid;grid-template-columns:repeat(3,1fr);margin-top:12px;border:1px solid #d8dfe9;background:#f4f7fb}}.totals .field strong{{font-size:17px;font-weight:bold}}footer{{margin-top:16px;font-size:9px;line-height:1.7;color:#64728a;border-top:1px solid #d8dfe9;padding-top:12px}}@media(max-width:620px){{article{{margin:0;padding:18px;border:0}}header{{flex-wrap:wrap}}.grid{{grid-template-columns:1fr 1fr}}.identity{{grid-template-columns:1fr}}.qr{{display:none}}.totals{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}article{{border:0;margin:0;padding:0;max-width:none}}section{{break-inside:avoid}}.watermark{{position:fixed}}}}
</style></head><body><article><div class="watermark">{status}</div><header><div><h1>NexoFiscal</h1><p>Gestão e emissão de NFS-e</p></div><div><h3>DEMONSTRATIVO DE NFS-e</h3><p>Apresentação inspirada no DANFSe</p><p>Ambiente local de portfólio</p></div></header><div class="warning">{WATERMARK}{' | SIMULAÇÃO CANCELADA' if cancelled else ''}</div><div class="identity"><div class="grid">{cell('Identificador demonstrativo',data['identifier'])}{cell('Número fiscal oficial','Não emitido')}{cell('Competência',data['competence'])}{cell('Data / hora - Brasília',display_time(data))}{cell('Ambiente','Demonstração local')}{cell('Chave de acesso','Não gerada pelo simulador')}</div><div class="qr"><img alt="QR interno de demonstração" src="data:image/png;base64,{qr}"><p>QR interno. Não valida documento fiscal oficial.</p></div></div>{sections}<div class="totals">{cell('Valor dos serviços',amount(data['amount']))}{cell('Tributos','Não calculados')}{cell('Valor documentado na simulação',amount(data['amount']))}</div><section><h2>INFORMAÇÕES COMPLEMENTARES</h2><div class="description">Simulação de portfólio. Não houve transmissão a prefeitura, Sefin ou SEFAZ. Não substitui nota fiscal, DPS, assinatura digital ou autorização governamental. {escape(data.get('historical_notice') or ('Documento cancelado, conservado como registro histórico.' if cancelled else 'Os dados cadastrais foram preservados no momento da geração.'))}</div></section><footer>{REFERENCE} NexoFiscal não é um emissor oficial neste ambiente.<br>Identificador {escape(data['identifier'])} - {WATERMARK}</footer></article></body></html>'''


def pdf_document(data,cancelled=False):
    output=BytesIO()
    document=SimpleDocTemplate(output,pagesize=A4,rightMargin=12*mm,leftMargin=12*mm,topMargin=11*mm,bottomMargin=16*mm,title=f"{data['identifier']} | NexoFiscal - Demonstracao",author=BRAND)
    width=A4[0]-24*mm
    label_style=ParagraphStyle('Label',fontName='Helvetica',fontSize=6.8,leading=8,textColor=colors.HexColor('#5f6f85'))
    value_style=ParagraphStyle('Value',fontName='Helvetica',fontSize=7.5,leading=9.5,textColor=colors.HexColor('#16243a'))
    heading_style=ParagraphStyle('Section',fontName='Helvetica-Bold',fontSize=8,leading=11,textColor=colors.HexColor('#223c67'))
    warning_style=ParagraphStyle('Warning',fontName='Helvetica-Bold',fontSize=8.5,leading=12,textColor=colors.HexColor('#964b0b'),alignment=TA_CENTER)
    def paragraph(value,style=value_style):
        return Paragraph(escape(str(value or 'Não informado')).replace('\n','<br/>'),style)
    def field(label,value):
        return [paragraph(label,label_style),Spacer(1,3),paragraph(value)]
    def grid(rows,columns=3):
        cells=[field(k,v) for k,v in rows]
        while len(cells)%columns:
            cells.append('')
        table=Table([cells[i:i+columns] for i in range(0,len(cells),columns)],colWidths=[width/columns]*columns)
        table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d5dce7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        return table
    def section(title,rows):
        banner=Table([[paragraph(title,heading_style)]],colWidths=[width]);banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf1f6')),('BOX',(0,0),(-1,-1),.4,colors.HexColor('#d5dce7')),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        return [Spacer(1,6),banner,grid(rows)]
    title=ParagraphStyle('Title',fontName='Helvetica-Bold',fontSize=20,leading=23,textColor=colors.HexColor('#1d355f'))
    sub=ParagraphStyle('Sub',fontName='Helvetica',fontSize=8,leading=11,textColor=colors.HexColor('#65748a'))
    header=Table([[[paragraph('NexoFiscal',title),paragraph('Gestão e emissão de NFS-e',sub)],[paragraph('DEMONSTRATIVO DE NFS-e',heading_style),paragraph('Apresentação inspirada no DANFSe',sub),paragraph('Ambiente local de portfólio',sub)]]],colWidths=[width*.57,width*.43])
    header.setStyle(TableStyle([('LINEBELOW',(0,0),(-1,-1),1.5,colors.HexColor('#223c67')),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    story=[header,Spacer(1,10),paragraph(WATERMARK.replace('—','-')+(' | SIMULAÇÃO CANCELADA' if cancelled else ''),warning_style),Spacer(1,9)]
    meta=grid([('Identificador demonstrativo',data['identifier']),('Número fiscal oficial','Não emitido'),('Competência',data['competence']),('Data / hora - Brasília',display_time(data)),('Ambiente','Demonstração local'),('Chave de acesso','Não gerada')])
    # QR é um identificador textual interno, não uma URL oficial ou chave fiscal.
    qr=Image(BytesIO(qr_png(data)),width=22*mm,height=22*mm)
    qrt=Table([[qr],[paragraph('QR interno de demonstração. Não valida NFS-e.',label_style)]],colWidths=[28*mm])
    meta_width=width-31*mm
    meta=Table([[meta,qrt]],colWidths=[meta_width,31*mm])
    # A grade de identificação recebe largura própria para evitar transbordamento.
    left_rows=[('Identificador demonstrativo',data['identifier']),('Número fiscal oficial','Não emitido'),('Competência',data['competence']),('Data / hora - Brasília',display_time(data)),('Ambiente','Demonstração local'),('Chave de acesso','Não gerada')]
    cells=[field(k,v) for k,v in left_rows]
    left=Table([cells[:3],cells[3:]],colWidths=[meta_width/3]*3)
    left.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d5dce7')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    meta=Table([[left,qrt]],colWidths=[meta_width,31*mm]);meta.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]));story.append(meta)
    blocks=fields(data)
    for name,rows in blocks[:2]:
        story.extend(section(name,rows))
    story.extend(section('SERVIÇO PRESTADO',[('Serviço',data['service']),('Competência',data['competence']),('Valor dos serviços',amount(data['amount']))]))
    desc=Table([[paragraph(data['description'])]],colWidths=[width]);desc.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.4,colors.HexColor('#d5dce7')),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.append(desc)
    for name,rows in blocks[2:]:
        story.extend(section(name,rows))
    story.extend(section('VALORES DOCUMENTADOS NA SIMULAÇÃO',[('Valor dos serviços',amount(data['amount'])),('Tributos','Não calculados'),('Valor documentado',amount(data['amount']))]))
    story.append(Spacer(1,9));story.append(paragraph('INFORMAÇÕES COMPLEMENTARES',heading_style));story.append(Spacer(1,4))
    story.append(paragraph('Simulação de portfólio. Não houve transmissão a prefeitura, Sefin ou SEFAZ. Não substitui nota fiscal, DPS, assinatura digital ou autorização governamental. '+(data.get('historical_notice') or 'Os dados foram preservados na geração.')+(' SIMULAÇÃO CANCELADA - registro histórico.' if cancelled else ''),sub))
    def page_marks(canvas,doc):
        canvas.saveState();canvas.setFillColor(colors.HexColor('#c6ceda'));canvas.setFillAlpha(.55);canvas.translate(A4[0]/2,A4[1]/2);canvas.rotate(32);canvas.setFont('Helvetica-Bold',44);canvas.drawCentredString(0,0,'CANCELADA - SIMULAÇÃO' if cancelled else 'DEMONSTRAÇÃO');canvas.restoreState()
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d5dce7'));canvas.line(12*mm,12*mm,A4[0]-12*mm,12*mm);canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#627189'));canvas.drawString(12*mm,8*mm,f"NexoFiscal | {data['identifier']} | SEM VALIDADE FISCAL");canvas.drawRightString(A4[0]-12*mm,8*mm,f'Página {doc.page}');canvas.restoreState()
    document.build(story,onFirstPage=page_marks,onLaterPages=page_marks)
    return output.getvalue()


def xml_document(data):
    root=Element('DocumentoDemonstrativoNFS',{ 'xmlns':'urn:nexofiscal:demonstracao:v1','semValidadeFiscal':'true','assinaturaDigital':'ausente'})
    for key in ('identifier','environment','created_at','competence','amount','description'):
        SubElement(root,key).text=str(data[key])
    for group in ('issuer','client'):
        node=SubElement(root,group)
        for key,value in data[group].items():
            if key=='address':
                addr=SubElement(node,'address')
                for k,v in (value or {}).items():SubElement(addr,k).text=str(v)
            elif value is not None:SubElement(node,key).text=str(value)
    SubElement(root,'aviso').text=WATERMARK
    SubElement(root,'tributos').text='Não calculados. XML local demonstrativo, incompatível com transmissão oficial.'
    return tostring(root,encoding='unicode',xml_declaration=True)
