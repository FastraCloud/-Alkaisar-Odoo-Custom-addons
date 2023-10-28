
{
    "name": "Purchase Request Petty Cash",
    "category": "Purchase Management",
    "depends": [
        "purchase_request",
        'kay_petty_cash',
        'posh_multilocation',
    ],
    "data": [
        'security/ir.model.access.csv',
        # 'security/rules.xml',
        'wizard/cancel_reason_view.xml',
        
        'views/petty_cash.xml',
        'views/account_invoice.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
