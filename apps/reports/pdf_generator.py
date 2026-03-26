"""
Générateur de rapports PDF professionnels Fortal Bank.
Utilise ReportLab pour produire un rapport complet avec :
  - Page de couverture (logo, date, périmètre)
  - Résumé exécutif (KPIs clés)
  - Graphiques (distribution fraudes, top villes, évolution)
  - Tableau des transactions suspectes
  - Recommandations
"""

import io
import os
from datetime import timedelta
from pathlib import Path

from django.utils import timezone
from django.conf import settings
from django.db.models import Count, Sum, Avg, Q

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.platypus import Image as RLImage
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

# Palette Fortal Bank
C_BG        = colors.HexColor('#0D0F0E') # Fond des pages
C_CARD      = colors.HexColor('#131714') # Fond des tableaux et encadrés
C_BORDER    = colors.HexColor('#222824') # Bordures des tableaux
C_GREEN     = colors.HexColor('#00C853') # Couleur principale (titres, accents, statut normal)
C_GREEN_DIM = colors.HexColor('#007A33') # Vert atténué (arrière-plan des badges verts)
C_RED       = colors.HexColor('#C62828') # Alertes critiques et transactions frauduleuses
C_AMBER     = colors.HexColor('#F59E0B') # Alertes de niveau élevé
C_YELLOW    = colors.HexColor('#EAB308') # Alertes de niveau moyen
C_WHITE     = colors.HexColor('#F0F2F0') # Texte principal
C_GRAY      = colors.HexColor('#8A9A8D') # Texte secondaire et en-têtes de colonnes
C_DARK      = colors.HexColor('#1A1F1C') # Fond alterné des lignes de tableaux


def build_cover_page(elements, styles, period_start, period_end, stats):
    """Construit la page de couverture du rapport."""

    # En-tête vert plein
    header_table = Table([['']], colWidths=[19*cm], rowHeights=[3.5*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_GREEN),
        ('ROUNDEDCORNERS', [8]),
    ]))
    elements.append(header_table)

    elements.append(Spacer(1, 1.5*cm))

    # Titre principal
    elements.append(Paragraph(
        '<font color="#00C853" size="11">FORTAL BANK</font>',
        ParagraphStyle('brand', fontName='Helvetica-Bold', fontSize=11, spaceAfter=4, textColor=C_GREEN)
    ))
    elements.append(Paragraph(
        'Rapport de Détection<br/>de Fraudes Bancaires',
        ParagraphStyle('maintitle', fontName='Helvetica-Bold', fontSize=28, leading=34, spaceAfter=16, textColor=C_WHITE)
    ))
    elements.append(Paragraph(
        f'Période du {period_start.strftime("%d %B %Y")} au {period_end.strftime("%d %B %Y")}',
        ParagraphStyle('period', fontName='Helvetica', fontSize=12, spaceAfter=6, textColor=C_GRAY)
    ))
    elements.append(Paragraph(
        f'Généré le {timezone.now().strftime("%d/%m/%Y à %H:%M")}',
        ParagraphStyle('gendate', fontName='Helvetica', fontSize=10, textColor=C_GRAY)
    ))

    elements.append(Spacer(1, 1.5*cm))
    elements.append(HRFlowable(width='100%', thickness=1, color=C_BORDER))
    elements.append(Spacer(1, 1*cm))

    # KPIs de couverture
    kpi_data = [
        ['TRANSACTIONS', 'FRAUDES', 'TAUX DE FRAUDE', 'MONTANT BLOQUÉ'],
        [
            f"{stats['total_txn']:,}",
            f"{stats['total_fraud']:,}",
            f"{stats['fraud_rate']:.2f}%",
            f"{int(stats['fraud_amount']):,} F",
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[4.75*cm]*4)
    kpi_table.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,0), 7),
        ('TEXTCOLOR',   (0,0), (-1,0), C_GRAY),
        ('FONTNAME',    (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,1), (-1,1), 22),
        ('TEXTCOLOR',   (0,1), (0,1), C_GREEN),
        ('TEXTCOLOR',   (1,1), (1,1), C_RED),
        ('TEXTCOLOR',   (2,1), (2,1), C_AMBER),
        ('TEXTCOLOR',   (3,1), (3,1), C_YELLOW),
        ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_DARK, C_CARD]),
        ('TOPPADDING',  (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('ROUNDEDCORNERS', [6]),
    ]))
    elements.append(kpi_table)
    elements.append(PageBreak())


def build_executive_summary(elements, styles, stats):
    """Section résumé exécutif."""
    elements.append(Paragraph('1. Résumé Exécutif', styles['Heading1']))
    elements.append(Spacer(1, 6))

    summary_text = f"""
    Durant la période analysée, le système de détection de fraudes Fortal Bank a traité
    <b>{stats['total_txn']:,} transactions</b> pour un volume total de
    <b>{int(stats['total_amount']):,} FCFA</b>.
    Le moteur ML (Isolation Forest, One-Class SVM, Random Forest) a identifié
    <b>{stats['total_fraud']:,} transactions frauduleuses</b>, représentant
    <b>{stats['fraud_rate']:.2f}%</b> du volume total.
    Le montant total des transactions bloquées s'élève à
    <b><font color="#C62828">{int(stats['fraud_amount']):,} FCFA</font></b>.
    """
    elements.append(Paragraph(summary_text.strip(), styles['BodyText']))
    elements.append(Spacer(1, 12))

    # Tableau des alertes par niveau
    alert_data = [
        ['Niveau', 'Nombre', 'Montant moyen', 'Action requise'],
    ]
    for level, count, avg in stats.get('alerts_by_level', []):
        action = {'CRITIQUE': 'Blocage immédiat', 'ELEVE': 'Investigation sous 2h', 'MOYEN': 'Surveillance renforcée'}.get(level, 'Analyse')
        alert_data.append([level, str(count), f"{int(avg):,} FCFA", action])

    if len(alert_data) > 1:
        alert_table = Table(alert_data, colWidths=[3.5*cm, 2.5*cm, 5*cm, 8*cm])
        level_colors = {'CRITIQUE': C_RED, 'ELEVE': C_AMBER, 'MOYEN': C_YELLOW}
        style = [
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 9),
            ('BACKGROUND',  (0,0), (-1,0), C_DARK),
            ('TEXTCOLOR',   (0,0), (-1,0), C_GRAY),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_CARD, C_BG]),
            ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
            ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',  (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TEXTCOLOR',   (0,0), (-1,-1), C_WHITE),
        ]
        # Couleur par niveau
        for i, row in enumerate(alert_data[1:], 1):
            color = level_colors.get(row[0], C_WHITE)
            style.append(('TEXTCOLOR', (0, i), (0, i), color))
            style.append(('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'))

        alert_table.setStyle(TableStyle(style))
        elements.append(alert_table)

    elements.append(Spacer(1, 16))


def build_fraud_chart(stats):
    """Génère un graphique en barres des fraudes par jour."""
    drawing = Drawing(480, 200)

    # Fond
    drawing.add(Rect(0, 0, 480, 200, fillColor=C_DARK, strokeColor=C_BORDER, strokeWidth=1))

    fraud_trend = stats.get('fraud_trend', [])
    if not fraud_trend:
        drawing.add(String(240, 100, 'Données insuffisantes', textAnchor='middle', fillColor=C_GRAY))
        return drawing

    max_val = max(d['count'] for d in fraud_trend) or 1
    bar_w   = min(20, 400 // len(fraud_trend))
    spacing = 400 // len(fraud_trend)
    x_start = 40

    for i, day in enumerate(fraud_trend):
        x       = x_start + i * spacing
        bar_h   = (day['count'] / max_val) * 140
        y_bar   = 30

        drawing.add(Rect(x, y_bar, bar_w, bar_h,
                         fillColor=C_RED, strokeColor=None))
        drawing.add(String(x + bar_w//2, y_bar - 12, day['date'],
                           textAnchor='middle', fillColor=C_GRAY, fontSize=7))
        if day['count'] > 0:
            drawing.add(String(x + bar_w//2, y_bar + bar_h + 3, str(day['count']),
                               textAnchor='middle', fillColor=C_WHITE, fontSize=7))

    # Titre
    drawing.add(String(240, 188, 'Fraudes détectées par jour',
                       textAnchor='middle', fillColor=C_WHITE, fontSize=10, fontName='Helvetica-Bold'))
    return drawing


def build_city_table(elements, styles, stats):
    """Tableau des villes avec le plus de fraudes."""
    elements.append(Paragraph('3. Analyse Géographique — Top Villes', styles['Heading1']))
    elements.append(Spacer(1, 6))

    city_data = [['Ville', 'Transactions', 'Fraudes', 'Taux', 'Montant bloqué (FCFA)']]
    for city in stats.get('cities', []):
        rate = (city['fraud_count'] / city['count'] * 100) if city['count'] > 0 else 0
        city_data.append([
            city['city'],
            f"{city['count']:,}",
            f"{city['fraud_count']:,}",
            f"{rate:.1f}%",
            f"{int(city.get('fraud_amount') or 0):,}",
        ])

    table = Table(city_data, colWidths=[4*cm, 3*cm, 2.5*cm, 2.5*cm, 7*cm])
    table.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('BACKGROUND',  (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), C_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_CARD, C_BG]),
        ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('ALIGN',       (1,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TEXTCOLOR',   (0,0), (-1,-1), C_WHITE),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 16))


def build_top_fraud_transactions(elements, styles, transactions):
    """Tableau des transactions frauduleuses les plus significatives."""
    elements.append(PageBreak())
    elements.append(Paragraph('4. Transactions Frauduleuses — Top 20', styles['Heading1']))
    elements.append(Spacer(1, 6))

    data = [['ID', 'Montant (FCFA)', 'Type', 'Ville', 'Score', 'Statut', 'Date']]
    for txn in transactions[:20]:
        data.append([
            str(txn.transaction_id)[:8].upper(),
            f"{int(txn.amount):,}",
            txn.get_transaction_type_display()[:12],
            txn.city[:12] if txn.city else '-',
            f"{(txn.fraud_score or 0):.0%}",
            txn.status,
            txn.timestamp.strftime('%d/%m %H:%M') if txn.timestamp else '-',
        ])

    table = Table(data, colWidths=[2.2*cm, 3.2*cm, 2.8*cm, 2.5*cm, 1.8*cm, 2.5*cm, 3*cm])
    style = [
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 8),
        ('BACKGROUND',  (0,0), (-1,0), C_DARK),
        ('TEXTCOLOR',   (0,0), (-1,0), C_GRAY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_CARD, C_BG]),
        ('GRID',        (0,0), (-1,-1), 0.5, C_BORDER),
        ('ALIGN',       (1,0), (-1,-1), 'CENTER'),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',  (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TEXTCOLOR',   (0,0), (-1,-1), C_WHITE),
    ]
    for i, row in enumerate(data[1:], 1):
        status = row[5]
        if status == 'BLOQUEE':
            style.append(('TEXTCOLOR', (5, i), (5, i), C_RED))
            style.append(('FONTNAME',  (5, i), (5, i), 'Helvetica-Bold'))
        elif status == 'SUSPECTE':
            style.append(('TEXTCOLOR', (5, i), (5, i), C_AMBER))

    table.setStyle(TableStyle(style))
    elements.append(table)


def build_recommendations(elements, styles, stats):
    """Section recommandations basées sur les données."""
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('5. Recommandations', styles['Heading1']))
    elements.append(Spacer(1, 6))

    recs = [
        ('Renforcement des contrôles nocturnes',
         f"Les transactions nocturnes (00h-05h) représentent une part disproportionnée des fraudes. "
         f"Recommandation : Implémenter une authentification renforcée (OTP) pour toutes les transactions nocturnes dépassant 50 000 FCFA."),
        ('Surveillance IP étrangères',
         f"Les transactions initiées depuis des adresses IP hors du Sénégal présentent un taux de fraude élevé. "
         f"Recommandation : Activer le blocage automatique ou la confirmation 2FA pour toutes les connexions étrangères."),
        ('Plafonds adaptatifs par profil client',
         f"Le ratio montant/moyenne est l'un des signaux prédictifs les plus forts. "
         f"Recommandation : Implémenter des plafonds dynamiques basés sur l'historique individuel de chaque client."),
        ('Alertes sur nouveaux appareils',
         f"Les prises de contrôle de compte via de nouveaux appareils sont fréquentes. "
         f"Recommandation : Systématiser les notifications de connexion depuis un nouvel appareil avec validation par SMS."),
    ]

    for title, body in recs:
        rec_data = [[f'• {title}', '']]
        rec_table = Table([[Paragraph(f'<b>{title}</b>', ParagraphStyle('rt', fontName='Helvetica-Bold', fontSize=9, textColor=C_GREEN)),
                            Paragraph(body, ParagraphStyle('rb', fontName='Helvetica', fontSize=8.5, textColor=C_GRAY, leading=13))]],
                          colWidths=[4.5*cm, 14.5*cm])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,-1), C_DARK),
            ('TOPPADDING',  (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('VALIGN',      (0,0), (-1,-1), 'TOP'),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [C_CARD]),
        ]))
        elements.append(rec_table)
        elements.append(Spacer(1, 6))


def generate_fraud_report(period_days: int = 30) -> bytes:
    """
    Génère le rapport PDF complet et retourne le contenu en bytes.

    Args:
        period_days: Nombre de jours couverts par le rapport

    Returns:
        bytes: Contenu du fichier PDF
    """
    from apps.transactions.models import Transaction, Alert

    period_end   = timezone.now()
    period_start = period_end - timedelta(days=period_days)

    # Collecte des statistiques
    qs = Transaction.objects.filter(timestamp__range=[period_start, period_end])

    total_txn   = qs.count()
    total_fraud = qs.filter(status__in=['SUSPECTE', 'BLOQUEE']).count()
    total_amount = qs.aggregate(s=Sum('amount'))['s'] or 0
    fraud_amount = qs.filter(status='BLOQUEE').aggregate(s=Sum('amount'))['s'] or 0
    fraud_rate   = (total_fraud / total_txn * 100) if total_txn > 0 else 0

    # Alertes par niveau
    alerts_by_level = []
    for level in ['CRITIQUE', 'ELEVE', 'MOYEN']:
        count = Alert.objects.filter(level=level, created_at__range=[period_start, period_end]).count()
        avg   = qs.filter(fraud_score__isnull=False, alert__level=level).aggregate(a=Avg('amount'))['a'] or 0
        if count > 0:
            alerts_by_level.append((level, count, avg))

    # Top villes
    cities = list(
        qs.values('city')
        .annotate(
            count=Count('id'),
            fraud_count=Count('id', filter=Q(status__in=['SUSPECTE', 'BLOQUEE'])),
            fraud_amount=Sum('amount', filter=Q(status='BLOQUEE')),
        )
        .order_by('-fraud_count')[:10]
    )

    # Tendance fraudes par jour
    from django.db.models.functions import TruncDate
    fraud_trend = list(
        qs.filter(status__in=['SUSPECTE', 'BLOQUEE'])
        .annotate(date=TruncDate('timestamp'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    fraud_trend_data = [
        {'date': d['date'].strftime('%d/%m'), 'count': d['count']}
        for d in fraud_trend
    ]

    # Top transactions frauduleuses
    top_fraud_txns = list(
        qs.filter(status__in=['SUSPECTE', 'BLOQUEE'])
        .order_by('-fraud_score', '-amount')[:25]
    )

    stats = {
        'total_txn':       total_txn,
        'total_fraud':     total_fraud,
        'total_amount':    float(total_amount),
        'fraud_amount':    float(fraud_amount),
        'fraud_rate':      fraud_rate,
        'alerts_by_level': alerts_by_level,
        'cities':          cities,
        'fraud_trend':     fraud_trend_data,
    }

    # Construction du PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f'Rapport Fraudes — Fortal Bank',
    )

    # Styles personnalisés fond sombre
    styles = getSampleStyleSheet()
    # Modification directe des styles existants (évite KeyError si déjà défini)
    styles['Heading1'].fontName  = 'Helvetica-Bold'
    styles['Heading1'].fontSize  = 13
    styles['Heading1'].textColor = C_GREEN
    styles['Heading1'].spaceBefore = 16
    styles['Heading1'].spaceAfter  = 6
    styles['BodyText'].fontName  = 'Helvetica'
    styles['BodyText'].textColor = C_WHITE
    styles['BodyText'].fontSize  = 9.5
    styles['BodyText'].leading   = 15

    elements = []

    # Fond sombre global via canvas — géré par la page setup
    def dark_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG) # couleur de fond des pages
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        # Pied de page
        canvas.setFillColor(C_GRAY)
        canvas.setFont('Helvetica', 7)
        canvas.drawCentredString(A4[0]/2, 1.2*cm, f'Fortal Bank — Rapport Confidentiel — Page {doc.page}')
        canvas.restoreState()

    # Pages
    build_cover_page(elements, styles, period_start, period_end, stats)
    build_executive_summary(elements, styles, stats)

    # Section graphique fraudes
    elements.append(Paragraph('2. Évolution des Fraudes', styles['Heading1']))
    elements.append(Spacer(1, 6))
    chart = build_fraud_chart(stats)
    elements.append(chart)
    elements.append(Spacer(1, 16))

    build_city_table(elements, styles, stats)
    build_top_fraud_transactions(elements, styles, top_fraud_txns)
    build_recommendations(elements, styles, stats)

    doc.build(elements, onFirstPage=dark_page, onLaterPages=dark_page)
    buffer.seek(0)
    return buffer.getvalue()
