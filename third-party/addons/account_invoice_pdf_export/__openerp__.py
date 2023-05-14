{
    'name': "Export Invoices",
    'description': """Export multiple invoices PDF in Zip 
    """,
    'category': '',
    'version': '1.0',
    'depends': ['base','sale','account'],
    'data': [
     'wizard/invoice_pdf_export_view.xml',
    ],

    # Author
    'author': 'Synodica Solutions Pvt. Ltd.',
    'website': 'https://synodica.com',
    'maintainer': 'Synodica Solutions Pvt. Ltd.',

    'installable': True,
    'application': True,
    'auto_install': False,
}
