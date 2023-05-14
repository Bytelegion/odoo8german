# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the top level of this module for full copyright and licensing details.

from openerp import fields, models, _
from openerp.exceptions import Warning


class EcofiExportColumns(models.AbstractModel):
    _name = 'ecofi.export.columns'

    def get_legal_datev_header(self, ecofi):
        """
        Get the required legal header for finance tax authorities
        See "DATEV Schnittstellen-Entwicklungsleitfaden" for details
        """

        def to_datev_date(date):
            return fields.Date.from_string(date).strftime("%Y%m%d")

        def to_datev_datetime(datetime):
            return fields.Date.from_string(datetime).strftime("%Y%m%d%H%M%S")

        create_date = '{dt}000'.format(dt=to_datev_datetime(fields.Datetime.now()))
        date_from = to_datev_date(ecofi.date_from or fields.Date.today())
        date_to = to_datev_date(ecofi.date_to or fields.Date.today())

        if not ecofi.company_id.currency_id.name:
            raise Warning(_(u'Please ensure that your company has a valid currency set.'))

        if not ecofi.company_id.datev_client_no or not ecofi.company_id.datev_consultant_no:
            raise Warning(_(u'Please set a client and consultant number in the DATEV settings.'))

        fiscal_date_str = self.env['account.fiscalyear'].search([('company_id', '=', ecofi.company_id.id), ('state', '=', 'draft')], limit=1).date_start
        fiscal_date = fields.Date.from_string(fiscal_date_str).strftime("%Y%m%d")

        # Datetime-Format: JJJJMMTTHHMMSS | Trennzeichen: Semicolon
        ret_list = [
            u'EXTF',  # External Format [length: 4, type: string]
            u'510',  # DATEV Version Number [length: 3, type: int]
            u'21',  # Data-Category [length: 2, type: int]
            u'Buchungsstapel',  # Formatname [length: X, type: string]
            u'7',  # Formatversion [length: 1, type: int]
            create_date,  # Creation date [type: datetime]
            u'',  # Import date [type: datetime]
            u'',  # Source [type: string]
            u'',  # Exported by [length: X, type: string]
            u'',  # Imported by [type: string]
            unicode(ecofi.company_id.datev_consultant_no),  # Consultant Number von [length: 7, type: int]
            unicode(ecofi.company_id.datev_client_no),  # Client number [length: 5, type: int]
            fiscal_date,  # Wirtschaftsjahresbeginn [type: date]
            u'4',  # Sachkontennummernlänge [length: 1, type: int]
            date_from,  # Date from [type: datetime]
            date_to,  # Date to [type: datetime]
            u'',  # Description [length: 30, type: string]
            u'',  # Diktatkürzel [length: 2, type: string]
            u'',  # Booking type [length: 1, type: int]
            u'',  # Rechnungslegungszweck [length: 2, type: int]
            u'',  # Festschreibung [length: 1, type: int-bool]
            ecofi.company_id.currency_id.name,  # Currency [length: 3, type: string]
            u'',  # Reserved [type: int]
            u'',  # Derivatskennzeichen [type: string]
            u'',  # Reserved [type: int]
            u'',  # Reserved [type: int]
            ecofi.company_id.skr_no,  # SKR [type: string, z.B. 03]
            u'',  # Branchen-lösung-Id [type: int]
            u'',  # Reserved [type: int]
            u'',  # Reserved [ype: int]
            u'',  # Anwendungsinformation [length: 16, type: string]
        ]
        return [e.encode('cp1252', 'ignore') for e in ret_list]

    @staticmethod
    def get_datev_column_headings():
        """ Method that creates the Datev CSV header line
        """
        ret_list = [
            u'Umsatz (ohne Soll-/Haben-Kennzeichen)',
            u'Soll-/Haben-Kennzeichen',
            u'WKZ Umsatz',
            u'Kurs',
            u'Basisumsatz',
            u'WKZ Basisumsatz',
            u'Konto',
            u'Gegenkonto (ohne BU-Schlüssel)',
            u'BU-Schlüssel',
            u'Belegdatum',
            u'Belegfeld 1',
            u'Belegfeld 2',
            u'Skonto',
            u'Buchungstext',
            u'Postensperre',
            u'Diverse Adressnummer',
            u'Geschäftspartnerbank',
            u'Sachverhalt',
            u'Zinssperre',
            u'Beleglink',
            u'Beleginfo - Art 1',
            u'Beleginfo - Inhalt 1',
            u'Beleginfo - Art 2',
            u'Beleginfo - Inhalt 2',
            u'Beleginfo - Art 3',
            u'Beleginfo - Inhalt 3',
            u'Beleginfo - Art 4',
            u'Beleginfo - Inhalt 4',
            u'Beleginfo - Art 5',
            u'Beleginfo - Inhalt 5',
            u'Beleginfo - Art 6',
            u'Beleginfo - Inhalt 6',
            u'Beleginfo - Art 7',
            u'Beleginfo - Inhalt 7',
            u'Beleginfo - Art 8',
            u'Beleginfo - Inhalt 8',
            u'KOST1 - Kostenstelle',
            u'KOST2 - Kostenstelle',
            u'Kost-Menge',
            u'EU-Land u. UStID',
            u'EU-Steuersatz',
            u'Abw. Versteuerungsart',
            u'Sachverhalt L+L',
            u'Funktionsergänzung L+L',
            u'BU 49 Hauptfunktionstyp',
            u'BU 49 Hauptfunktionsnummer',
            u'BU 49 Funktionsergänzung',
            u'Zusatzinformation - Art 1',
            u'Zusatzinformation- Inhalt 1',
            u'Zusatzinformation - Art 2',
            u'Zusatzinformation- Inhalt 2',
            u'Zusatzinformation - Art 3',
            u'Zusatzinformation- Inhalt 3',
            u'Zusatzinformation - Art 4',
            u'Zusatzinformation- Inhalt 4',
            u'Zusatzinformation - Art 5',
            u'Zusatzinformation- Inhalt 5',
            u'Zusatzinformation - Art 6',
            u'Zusatzinformation- Inhalt 6',
            u'Zusatzinformation - Art 7',
            u'Zusatzinformation- Inhalt 7',
            u'Zusatzinformation - Art 8',
            u'Zusatzinformation- Inhalt 8',
            u'Zusatzinformation - Art 9',
            u'Zusatzinformation- Inhalt 9',
            u'Zusatzinformation - Art 10',
            u'Zusatzinformation- Inhalt 10',
            u'Zusatzinformation - Art 11',
            u'Zusatzinformation- Inhalt 11',
            u'Zusatzinformation - Art 12',
            u'Zusatzinformation- Inhalt 12',
            u'Zusatzinformation - Art 13',
            u'Zusatzinformation- Inhalt 13',
            u'Zusatzinformation - Art 14',
            u'Zusatzinformation- Inhalt 14',
            u'Zusatzinformation - Art 15',
            u'Zusatzinformation- Inhalt 15',
            u'Zusatzinformation - Art 16',
            u'Zusatzinformation- Inhalt 16',
            u'Zusatzinformation - Art 17',
            u'Zusatzinformation- Inhalt 17',
            u'Zusatzinformation - Art 18',
            u'Zusatzinformation- Inhalt 18',
            u'Zusatzinformation - Art 19',
            u'Zusatzinformation- Inhalt 19',
            u'Zusatzinformation - Art 20',
            u'Zusatzinformation- Inhalt 20',
            u'Stück',
            u'Gewicht',
            u'Zahlweise',
            u'Forderungsart',
            u'Veranlagungsjahr',
            u'Zugeordnete Fälligkeit',
            u'Skontotyp',
            u'Auftragsnummer',
            u'Buchungstyp',
            u'Ust-Schlüssel (Anzahlungen)',
            u'EU-Land (Anzahlungen)',
            u'Sachverhalt L+L (Anzahlungen)',
            u'EU-Steuersatz (Anzahlungen)',
            u'Erlöskonto (Anzahlungen)',
            u'Herkunft-Kz',
            u'Leerfeld',
            u'KOST-Datum',
            u'Mandatsreferenz',
            u'Skontosperre',
            u'Gesellschaftername',
            u'Beteiligtennummer',
            u'Identifikationsnummer',
            u'Zeichnernummer',
            u'Postensperre bis',
            u'Bezeichnung SoBil-Sachverhalt',
            u'Kennzeichen SoBil-Buchung',
            u'Festschreibung',
            u'Leistungsdatum',
            u'Datum Zuord.Steuerperiode'
        ]
        return [e.encode('cp1252', 'ignore') for e in ret_list]

    @staticmethod
    def get_datev_export_line(datev_dict):
        ret_list = [
            datev_dict['Umsatz'],
            datev_dict['Sollhaben'],
            datev_dict['Waehrung'],
            datev_dict['Kurs'],
            datev_dict['Basiswaehrungsbetrag'],
            datev_dict['Basiswaehrungskennung'],
            datev_dict['Konto'],
            datev_dict['Gegenkonto'],
            datev_dict['Buschluessel'],
            datev_dict['Datum'],
            datev_dict['Beleg1'],
            datev_dict['Beleg2'],
            datev_dict['Skonto'],
            datev_dict['Buchungstext'],
            u'',  # Postensperre
            u'',  # Diverse Adressnummer
            u'',  # Geschäftspartnerbank
            u'',  # Sachverhalt
            u'',  # Zinssperre
            u'',  # Beleglink
            u'',  # Beleginfo - Art 1
            u'',  # Beleginfo - Inhalt 1
            u'',  # Beleginfo - Art 2
            u'',  # Beleginfo - Inhalt 2
            u'',  # Beleginfo - Art 3
            u'',  # Beleginfo - Inhalt 3
            u'',  # Beleginfo - Art 4
            u'',  # Beleginfo - Inhalt 4
            u'',  # Beleginfo - Art 5
            u'',  # Beleginfo - Inhalt 5
            u'',  # Beleginfo - Art 6
            u'',  # Beleginfo - Inhalt 6
            u'',  # Beleginfo - Art 7
            u'',  # Beleginfo - Inhalt 7
            u'',  # Beleginfo - Art 8
            u'',  # Beleginfo - Inhalt 8
            datev_dict['Kost1'],
            datev_dict['Kost2'],
            datev_dict['Kostmenge'],
            datev_dict['EulandUSTID'],
            datev_dict['EUSteuer'],
            u'',  # Abw. Versteuerungsart
            u'',  # Sachverhalt L+L
            u'',  # Funktionsergänzung L+L
            u'',  # BU 49 Hauptfunktionstyp
            u'',  # BU 49 Hauptfunktionsnummer
            u'',  # BU 49 Funktionsergänzung
            u'',  # Zusatzinformation - Art 1
            u'',  # Zusatzinformation- Inhalt 1
            u'',  # Zusatzinformation - Art 2
            u'',  # Zusatzinformation- Inhalt 2
            u'',  # Zusatzinformation - Art 3
            u'',  # Zusatzinformation- Inhalt 3
            u'',  # Zusatzinformation - Art 4
            u'',  # Zusatzinformation- Inhalt 4
            u'',  # Zusatzinformation - Art 5
            u'',  # Zusatzinformation- Inhalt 5
            u'',  # Zusatzinformation - Art 6
            u'',  # Zusatzinformation- Inhalt 6
            u'',  # Zusatzinformation - Art 7
            u'',  # Zusatzinformation- Inhalt 7
            u'',  # Zusatzinformation - Art 8
            u'',  # Zusatzinformation- Inhalt 8
            u'',  # Zusatzinformation - Art 9
            u'',  # Zusatzinformation- Inhalt 9
            u'',  # Zusatzinformation - Art 10
            u'',  # Zusatzinformation- Inhalt 10
            u'',  # Zusatzinformation - Art 11
            u'',  # Zusatzinformation- Inhalt 11
            u'',  # Zusatzinformation - Art 12
            u'',  # Zusatzinformation- Inhalt 12
            u'',  # Zusatzinformation - Art 13
            u'',  # Zusatzinformation- Inhalt 13
            u'',  # Zusatzinformation - Art 14
            u'',  # Zusatzinformation- Inhalt 14
            u'',  # Zusatzinformation - Art 15
            u'',  # Zusatzinformation- Inhalt 15
            u'',  # Zusatzinformation - Art 16
            u'',  # Zusatzinformation- Inhalt 16
            u'',  # Zusatzinformation - Art 17
            u'',  # Zusatzinformation- Inhalt 17
            u'',  # Zusatzinformation - Art 18
            u'',  # Zusatzinformation- Inhalt 18
            u'',  # Zusatzinformation - Art 19
            u'',  # Zusatzinformation- Inhalt 19
            u'',  # Zusatzinformation - Art 20
            u'',  # Zusatzinformation- Inhalt 20
            u'',  # Stück
            u'',  # Gewicht
            u'',  # Zahlweise
            u'',  # Forderungsart
            u'',  # Veranlagungsjahr
            u'',  # Zugeordnete Fälligkeit
            u'',  # Skontotyp
            u'',  # Auftragsnummer
            u'',  # Buchungstyp
            u'',  # Ust-Schlüssel (Anzahlungen)
            u'',  # EU-Land (Anzahlungen)
            u'',  # Sachverhalt L+L (Anzahlungen)
            u'',  # EU-Steuersatz (Anzahlungen)
            u'',  # Erlöskonto (Anzahlungen)
            u'',  # Herkunft-Kz
            u'',  # Leerfeld
            u'',  # KOST-Datum
            u'',  # Mandatsreferenz
            u'',  # Skontosperre
            u'',  # Gesellschaftername
            u'',  # Beteiligtennummer
            u'',  # Identifikationsnummer
            u'',  # Zeichnernummer
            u'',  # Postensperre bis
            u'',  # Bezeichnung SoBil-Sachverhalt
            u'',  # Kennzeichen SoBil-Buchung
            u'',  # Festschreibung
            u'',  # Leistungsdatum
            u''   # Datum Zuord.Steuerperiode
        ]
        return [e.encode('cp1252', 'ignore') for e in ret_list]
