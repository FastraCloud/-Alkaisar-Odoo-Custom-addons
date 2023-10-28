# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To be approved'),
    ('approved', 'Approved'),
    ('validate','Validated'),
    ('done', 'Done'),
    ('rejected', 'Rejected'),
    ('closed','Closed'),
]

class Kay_petty_cash(models.Model):
    _inherit = "kay.petty.cash"
    
    state = fields.Selection(selection=_STATES,default='draft')
    custodian = fields.Many2one('res.users',string="Custodian")
    location = fields.Many2one('stock.location','Location')
    purchase_request_petty_cash_lines = fields.One2many('purchase.request.kay.petty.cash', 'key_petty_cash_id', string="Lines")
    cancel_reason = fields.Char(
        string="Reason for Rejection",
        readonly=True)
    
    @api.multi
    def button_draft(self):
        return self.write({'state': 'draft'})

    @api.multi
    def button_to_approve(self):
        return self.write({'state': 'to_approve'})

    @api.multi
    def button_approved(self):
        return self.write({'state': 'approved'})

    @api.multi
    def button_rejected(self):
        return self.write({'state': 'rejected'})

    
class PurchaseRequestKayPettyCash(models.Model):
    _name = "purchase.request.kay.petty.cash"
    
    key_petty_cash_id = fields.Many2one('kay.petty.cash', string="Petty Cash")
    name = fields.Char('Request Description')
    date = fields.Date('Request Date')
    amount = fields.Float('Request Amount')

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    discount_type = fields.Selection([('percentage', 'Percentage'), ('amount', 'Amount')], string='Discount Type', default='amount')
    discount_rate = fields.Float(string='Discount Rate', digits=dp.get_precision('Product Price'), default=0.0)
    discount_fixed = fields.Monetary(string='Discount', digits=dp.get_precision('Product Price'), default=0.0, track_visibility='always')

    # @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
                 'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
                 'invoice_id.date_invoice', 'invoice_id.date', 'discount_type', 'discount_fixed', 'discount_rate')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        discount = 0.0
        if self.discount_type == 'amount':
            discount = self.discount_fixed
        if self.discount_type == 'percentage':
            discount = (self.price_unit * self.quantity * self.discount_rate) / 100
        price = self.price_unit - discount
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id,
                                                          partner=self.invoice_id.partner_id)

        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        self.price_total = taxes['total_included'] if taxes else self.price_subtotal
        if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            currency = self.invoice_id.currency_id
            date = self.invoice_id._get_currency_rate_date()
            price_subtotal_signed = currency._convert(price_subtotal_signed, self.invoice_id.company_id.currency_id,
                                                      self.company_id or self.env.user.company_id,
                                                      date or fields.Date.today())
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign