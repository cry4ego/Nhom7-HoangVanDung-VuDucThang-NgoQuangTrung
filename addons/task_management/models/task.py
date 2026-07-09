# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
from odoo.tools import date_utils

class TaskManagement(models.Model):
    _name = 'task.management.task'
    _description = 'Quáº£n lÃ½ CÃ´ng Viá»‡c'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, deadline asc'

    name = fields.Char(string='TÃªn cÃ´ng viá»‡c', required=True, tracking=True)
    description = fields.Html(string='MÃ´ táº£ chi tiáº¿t') 

    partner_id = fields.Many2one('khach_hang.customer', string='KhÃ¡ch hÃ ng', tracking=True)
    order_id = fields.Many2one('khach_hang.order', string='ÄÆ¡n hÃ ng liÃªn quan', tracking=True, ondelete='cascade')
 
    nhan_vien_id = fields.Many2one('nhan_vien', string='NgÆ°á»i thá»±c hiá»‡n', tracking=True)
    
    start_date = fields.Date(string='NgÃ y báº¯t Ä‘áº§u', default=fields.Date.context_today)
    deadline = fields.Date(string='Háº¡n chÃ³t', tracking=True)
    
    progress = fields.Integer(string='Tiáº¿n Ä‘á»™ (%)', default=0)
    
    priority = fields.Selection([
        ('0', 'Tháº¥p'),
        ('1', 'Trung bÃ¬nh'),
        ('2', 'Cao'),
        ('3', 'Ráº¥t quan trá»ng')
    ], string='Äá»™ Æ°u tiÃªn', default='1')

    state = fields.Selection([
        ('todo', 'Cáº§n lÃ m'),
        ('in_progress', 'Äang thá»±c hiá»‡n'),
        ('done', 'HoÃ n thÃ nh'),
        ('cancel', 'Há»§y bá»')
    ], string='Tráº¡ng thÃ¡i', default='todo', tracking=True, group_expand='_expand_states')

    @api.constrains('start_date', 'deadline')
    def _check_dates(self):
        for record in self:
            if record.deadline and record.start_date and record.deadline < record.start_date:
                raise ValidationError("Lá»—i Logic: Háº¡n chÃ³t pháº£i sau ngÃ y báº¯t Ä‘áº§u!")

    @api.onchange('state')
    def _onchange_state(self):
        state_progress = {
            'todo': 0,          
            'in_progress': 50,   
            'done': 100,         
            'cancel': 0          
        }
        if self.state in state_progress:
            self.progress = state_progress[self.state]

    def _expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_todo(self):
        self.state = 'todo'
        self.progress = 0

    def action_in_progress(self):
        self.state = 'in_progress'
        self.progress = 50

    def action_done(self):
        self.state = 'done'
        self.progress = 100
        if self.partner_id:
            self.env['khach_hang.care_activity'].create({
                'customer_id': self.partner_id.id,
                'care_date': fields.Date.context_today(self),
                'contact_method': 'phone',
                'notes': f"CÃ´ng viá»‡c \"{self.name}\" Ä‘Ã£ hoÃ n thÃ nh. NhÃ¢n viÃªn thá»±c hiá»‡n: {self.nhan_vien_id.ho_va_ten if self.nhan_vien_id else 'N/A'}",
            })

    def action_cancel(self):
        self.state = 'cancel'
        self.progress = 0

