# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    telegram_notify_enabled = fields.Boolean(
        string='Bật thông báo Telegram',
        config_parameter='task_management.telegram_notify_enabled',
        help='Gửi thông báo qua Telegram Bot khi có công việc mới được tự động gán cho nhân viên')
    telegram_bot_token = fields.Char(
        string='Telegram Bot Token',
        config_parameter='task_management.telegram_bot_token',
        help='Lấy từ @BotFather trên Telegram')
    telegram_chat_id = fields.Char(
        string='Telegram Chat ID',
        config_parameter='task_management.telegram_chat_id',
        help='ID của group/kênh Telegram sẽ nhận thông báo (thêm bot vào group rồi lấy chat_id)')
