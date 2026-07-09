from odoo import models, fields, api
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class Feedback(models.Model):
    _name = 'khach_hang.feedback'
    _description = 'Phản Hồi'
    _inherit = ['mail.thread']

    customer_id = fields.Many2one('khach_hang.customer', string='Khách Hàng', required=True)
    question = fields.Text(string='Câu Hỏi', required=True)
    supporter = fields.Many2one('res.users', string='Nhân Viên Hỗ Trợ')
    answer = fields.Text(string='Câu Trả Lời')

    # ── [F4] Sentiment Analysis fields ─────────────────────────────────────────
    sentiment = fields.Selection([
        ('positive', '😊 Tích cực'),
        ('neutral',  '😐 Trung lập'),
        ('negative', '😠 Tiêu cực'),
    ], string='Cảm xúc', readonly=True, tracking=True)

    sentiment_score = fields.Float(
        string='Điểm cảm xúc',
        digits=(4, 2),
        readonly=True,
        help='-1.0 = rất tiêu cực  │  0.0 = trung lập  │  +1.0 = rất tích cực',
    )
    sentiment_reason = fields.Char(
        string='Giải thích AI',
        readonly=True,
        help='Lý do AI đưa ra nhận xét cảm xúc',
    )

    # ── [F4] Sentiment Analysis core ───────────────────────────────────────
    def _analyze_sentiment(self, text):
        """[F4] Gọi Gemini để phân tích cảm xúc của text phản hồi.

        Trả về dict {'label': str, 'score': float, 'reason': str}
        hoặc None nếu Gemini không khả dụng.
        """
        if not text or not text.strip():
            return None

        config = self.env['chatbot.config'].search([('active', '=', True)], limit=1)
        if not config or not config.gemini_api_key:
            _logger.info("[F4] Không có chatbot config, bỏ qua sentiment analysis.")
            return None

        prompt = f"""Phân tích cảm xúc của đoạn văn bản sau đây (ngôn ngữ tiếng Việt):

\"{text[:500]}\"

Trả về JSON chính xác theo đúng định dạng sau (không thêm bất kỳ text nào khác):
{{"label": "positive|neutral|negative", "score": 0.0, "reason": "giải thích ngắn"}}

Quy tắc:
- label: một trong 3 giá trị: positive, neutral, negative
- score: số thực từ -1.0 (đủ tiêu cực) đến 1.0 (đủ tích cực)
- reason: lý do ngắn gọn bằng tiếng Việt (tối đa 80 ký tự)"""

        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"gemini-2.0-flash:generateContent?key={config.gemini_api_key}")
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 150, "temperature": 0.1},
            }
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()

            ai_text = (
                resp.json()
                .get('candidates', [{}])[0]
                .get('content', {})
                .get('parts', [{}])[0]
                .get('text', '').strip()
            )
            # Loại bỏ markdown code fence nếu có
            ai_text = ai_text.strip('`').strip()
            if ai_text.startswith('json'):
                ai_text = ai_text[4:].strip()

            result = json.loads(ai_text)
            label = result.get('label', 'neutral')
            if label not in ('positive', 'neutral', 'negative'):
                label = 'neutral'
            score = float(result.get('score', 0.0))
            score = max(-1.0, min(1.0, score))  # clamp
            reason = str(result.get('reason', ''))[:200]

            _logger.info(f"[F4] Sentiment: {label} ({score:.2f}) — {reason}")
            return {'label': label, 'score': score, 'reason': reason}

        except Exception as e:
            _logger.warning(f"[F4] Sentiment analysis lỗi: {e}")
            return None

    def _apply_sentiment(self, text_content):
        """Gọi _analyze_sentiment và ghi kết quả vào record (silent)."""
        result = self._analyze_sentiment(text_content)
        if result:
            self.sudo().write({
                'sentiment': result['label'],
                'sentiment_score': result['score'],
                'sentiment_reason': result['reason'],
            })

    # ── Override create / write ───────────────────────────────────────────────
    @api.model
    def _create_feedback_template(self):
        IrModel = self.env['ir.model']
        model_id = IrModel.search([('model', '=', 'khach_hang.feedback')], limit=1).id
        if not self.env['mail.template'].search([('name', '=', 'Phản Hồi Từ Nhân Viên Hỗ Trợ')]):
            self.env['mail.template'].create({
                'name': 'Phản Hồi Từ Nhân Viên Hỗ Trợ',
                'model_id': model_id,
                'email_from': '${object.supporter.email_formatted}',
                'email_to': '${object.customer_id.email}',
                'subject': 'Phản Hồi Cho Câu Hỏi Của Bạn',
                'body_html': """
                    <p>Xin chào ${object.customer_id.name},</p>
                    <p>Chúng tôi đã nhận được câu hỏi của bạn: <strong>${object.question}</strong></p>
                    <p>Đây là câu trả lời từ nhân viên hỗ trợ ${object.supporter.name}:<br/>
                    ${object.answer}</p>
                    <p>Trân trọng,<br/>Đội ngũ hỗ trợ</p>
                """,
            })

    @api.model
    def create(self, vals):
        if not self.env['mail.template'].search([('name', '=', 'Phản Hồi Từ Nhân Viên Hỗ Trợ')]):
            self._create_feedback_template()
        feedback = super(Feedback, self).create(vals)
        # [F4] Phân tích cảm xúc ngay khi tạo mới
        text_to_analyze = vals.get('question', '')
        if text_to_analyze:
            feedback._apply_sentiment(text_to_analyze)
        return feedback

    def write(self, vals):
        result = super(Feedback, self).write(vals)
        # [F4] Phân tích lại khi question hoặc answer thay đổi
        if 'question' in vals or 'answer' in vals:
            for rec in self:
                combined = ' '.join(filter(None, [rec.question, rec.answer]))
                rec._apply_sentiment(combined)
        if 'answer' in vals and vals['answer'] and self.customer_id.email:
            self._send_feedback_email()
        return result

    def _send_feedback_email(self):
        template = self.env.ref('khach_hang.mail_template_feedback_response')
        template.send_mail(self.id, force_send=True)