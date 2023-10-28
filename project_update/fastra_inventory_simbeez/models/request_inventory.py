# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError

class RequestInventory(models.Model):
    _name = 'request.inventory'
    _rec_name = "store_manager_id"

    @api.model
    def _get_default_approver(self):
        result = self.env['stock.location'].sudo().search([('store_keeper', '=', self.env.uid)])
        print(result,"result......")
        if len(result)>0:
            return self.env['res.users'].browse(result.branch_manager.id)
        if len(result)<=0:
            result_store_keeper = self.env['stock.location'].search([('store_keeper', '=', self.env.uid)])
            print(result_store_keeper,"store keeper result......")
            if result_store_keeper:
                return self.env['res.users'].browse(result_store_keeper.branch_manager.id)

    @api.model
    def _get_default_location(self):
        result = self.env['stock.location'].sudo().search([('store_keeper', '=', self.env.uid)])
        print(result,"result....location..")
        if len(result)==1:
            return result.id
        if len(result)>1:
            return result[0].id

    store_manager_id = fields.Many2one("res.users", string='Store Keeper', default=lambda self: self.env.user)
    source_location_id = fields.Many2one('stock.location', string="Source Location",default=_get_default_location)
    request_date = fields.Date('Purchase Date', default=datetime.date(datetime.now()))
    receiver_user_id = fields.Many2one('res.users', String='Project Mangaer',default=_get_default_approver)
    destination_location_id = fields.Many2one('stock.location', string="Purchase Location",default=_get_default_location)
    #date_returned = fields.Date('Return Date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),
        ('approve', 'Approve')
    ], string='Status', index=True, default='draft', copy=False)
    request_line_ids = fields.One2many('request.inventory.line', 'request_inventory_id', string='Request Lines')
    expected_to_return = fields.Boolean('Expected To Return')

    @api.multi
    def submit_request(self):
        for record in self:
            for request_line_id in record.request_line_ids:
                if request_line_id.quantity > request_line_id.product_id.qty_available:
                    request_line_id.state = 'not_available'
                else:
                    request_line_id.state = 'available'
            record.write({'state': 'request'})

    @api.multi
    def reset_to_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_request_approve(self):
        self.request_approve()
        return 
        return {
            'name': _('Approval Confirmation'),
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.confirm.req',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_inv_req_id':self.id
                }
        }

    @api.multi
    def request_approve(self,expected_to_return=False):
        stock_obj = self.env['stock.move'].sudo()
        new_state = "approve"
        for request_line_id in self.request_line_ids:
            stock_move_val = {'location_id': self.source_location_id.id,
                              'location_dest_id': self.destination_location_id.id,
                              'product_id': request_line_id.product_id.id,
                              'product_uom': request_line_id.product_id.uom_id.id,
                              'product_uom_qty': request_line_id.quantity,
                              'quantity_done':request_line_id.quantity,
                              'name':  self.store_manager_id.name + ': ' + request_line_id.product_id.name
                              }
            st_mv_id = stock_obj.create(stock_move_val)
            st_mv_id._action_confirm()
            st_mv_id._action_assign()
            st_mv_id._action_done()
            # update stock in stock quant
            current_stock_obj = self.env['stock.quant'].sudo().search([('location_id','=',self.destination_location_id.id),('product_id','=',request_line_id.product_id.id)])
            current_stock = current_stock_obj.quantity + request_line_id.quantity
            current_stock_obj.write({'quantity':current_stock})
        if expected_to_return:
            new_state = "to_be_returned"
            expected_to_return = True
        self.write({'state': new_state,'expected_to_return':expected_to_return})

    @api.multi
    def inventory_request_return(self):
        stock_obj = self.env['stock.move'].sudo()
        for request_line_id in self.request_line_ids:
            if not request_line_id.qty_to_return:
                raise UserError('Quantity To Return must be set in case of Return!!')

            stock_move_val = {'location_id': self.destination_location_id.id,
                              'location_dest_id': self.source_location_id.id,
                              'product_id': request_line_id.product_id.id,
                              'product_uom': request_line_id.product_id.uom_id.id,
                              'qty_to_return': request_line_id.qty_to_return,
                              'quantity_done':request_line_id.qty_to_return,
                              'name':  self.store_manager_id.name + ': ' + request_line_id.product_id.name
                              }
            st_mv_id = stock_obj.create(stock_move_val)
            st_mv_id = stock_obj.create(stock_move_val)
            st_mv_id._action_confirm()
            st_mv_id._action_assign()
            st_mv_id._action_done()
        self.write({'state': 'returned'})        
#

class RequestInventoryLine(models.Model):
    _name = 'request.inventory.line'

    request_inventory_id = fields.Many2one('request.inventory', string="Request Inventory")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float("Quantity Purchased", default=1, digits=dp.get_precision('Product Unit of Measure'))
    state = fields.Selection([('available', 'Available'), ('not_available', 'Not Available')], string='Status', index=True, copy=False)
    expected_to_return = fields.Boolean(related='request_inventory_id.expected_to_return',string='Expected to Return')
    description = fields.Text(string='Description')
    requestes_inventory = fields.Many2one('inventory.request', string="Request From Inventory")
    #qty_to_return = fields.Float('Quantity to Return')
class RequestOfInventory(models.Model):
    _name = 'inventory.request'

    @api.multi
    def submit_request(self):
        for rec in self:
            rec.state_of_request = 'request'
            
    @api.model
    def _get_default_approver(self):
        result = self.env['stock.location'].sudo().search([('store_keeper', '=', self.env.uid)])
        if len(result)>0:
            return self.env['res.users'].browse(result.branch_manager.id)
        if len(result)<=0:
            result_store_keeper = self.env['stock.location'].search([('store_keeper', '=', self.env.uid)])
            print(result_store_keeper,"store keeper result......")
            if result_store_keeper:
                return self.env['res.users'].browse(result_store_keeper.branch_manager.id)

    @api.model
    def _get_default_location(self):
        result = self.env['stock.location'].sudo().search([('store_keeper', '=', self.env.uid)])
        if len(result)==1:
            return result.id
        if len(result)>1:
            return result[0].id



    @api.multi
    def action_request_approve(self):
        for rec in self:
            rec.state_of_request = 'approve'
            # update stock in stock quant
            for request_line_id in self.request_lines:
                current_stock_obj = self.env['stock.quant'].sudo().search([('location_id','=',self.source_location.id),('product_id','=',request_line_id.product_id.id)])
                current_stock = current_stock_obj.quantity - request_line_id.quantity
                current_stock_obj.write({'quantity':current_stock})  
          
    @api.multi
    def reset_to_draft(self):
        self.write({'state_of_request': 'draft'})

    @api.multi
    def _get_default_destination_location(self):
        virutal_location_id = self.env['stock.location'].sudo().search([('name', '=', 'Raycon Virtual Location')])
        return virutal_location_id and virutal_location_id.id or False

    store_keeper_name = fields.Many2one("res.users", string='Store Keeper Name', default=lambda self: self.env.user)
    source_location = fields.Many2one('stock.location', string="Source Location",default=_get_default_location)
    Receiver_name = fields.Char(string="Receiver Name")
    released_date = fields.Date('Date Released', default=datetime.date(datetime.now()))
    Project_manager = fields.Many2one('res.users', String='Project Mangaer', default=_get_default_approver)
    destination_location = fields.Many2one('stock.location', string="Destination Location",default=_get_default_destination_location)
    state_of_request = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),
        ('approve', 'Approve')
    ], string='Status', index=True, default='draft', copy=False)
    request_lines = fields.One2many('request.inventory.line', 'requestes_inventory', string='Request Lines')

