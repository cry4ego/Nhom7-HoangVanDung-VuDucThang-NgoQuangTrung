# -*- coding: utf-8 -*-
"""
F5: Churn Detection — Phát hiện khách hàng có nguy cơ rời bỏ.

Score tính từ 3 tín hiệu:
  - Số ngày kể từ đơn hàng cuối (recency)
  - Tỷ lệ phản hồi tiêu cực gần đây (sentiment từ F4)
  - Tỷ lệ đơn hàng bị hủy (cancel rate)

Cron hàng tuần tính lại score và tự tạo care_activity cho KH rủi ro cao.
"""
from odoo import models, fields, api
import logging
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

# Ngưỡng phân loại (%)
THRESHOLD_HIGH = 65    # >= 65% → rủi ro cao → tự tạo care activity
THRESHOLD_MED  = 35    # >= 35% → rủi ro trung bình


class ChurnDetection(models.Model):
    """Extend khach_hang.customer với các field và logic phát hiện churn."""
    _inherit = 'khach_hang.customer'

    # ── [F5] Churn Risk Fields ────────────────────────────────────────────────
    churn_risk_score = fields.Float(
        string='Rủi ro rời bỏ (%)',
        digits=(5, 1),
        readonly=True,
        help='0–100%. Tính từ recency, sentiment tiêu cực và tỷ lệ đơn hủy.',
    )
    churn_risk_label = fields.Selection([
        ('low',    '🟢 Thấp'),
        ('medium', '🟡 Trung bình'),
        ('high',   '🔴 Cao'),
    ], string='Mức rủi ro', readonly=True, tracking=True)

    churn_last_computed = fields.Date(
        string='Tính lần cuối',
        readonly=True,
    )
    churn_reason = fields.Char(
        string='Lý do rủi ro',
        readonly=True,
        help='Mô tả tóm tắt các yếu tố đóng góp vào điểm rủi ro.',
    )

    # ── Score computation ─────────────────────────────────────────────────────
    def _compute_churn_score(self):
        """Tính churn score (0–100) cho 1 khách hàng.

        Trả về (score: float, reasons: list[str]).
        """
        self.ensure_one()
        score = 0.0
        reasons = []

        # 1. Recency — ngày từ đơn cuối (tối đa 40 điểm)
        done_orders = self.order_ids.filtered(lambda o: o.state == 'done')
        if done_orders:
            last_date = max(
                (o.date_order or o.create_date.date() for o in done_orders),
                default=None
            )
            if last_date:
                days_since = (date.today() - last_date).days
                recency_score = min(days_since / 90 * 40, 40)   # 90 ngày = full 40đ
                score += recency_score
                if days_since > 30:
                    reasons.append(f"Chưa mua hàng {days_since} ngày")
        else:
            # Chưa có đơn hoàn thành nào → cộng 20 điểm cơ bản
            score += 20
            reasons.append("Chưa có đơn hoàn thành")

        # 2. Negative sentiment — phản hồi tiêu cực gần đây (tối đa 35 điểm)
        recent_feedbacks = self.env['khach_hang.feedback'].search([
            ('customer_id', '=', self.id),
            ('sentiment', '!=', False),
        ], order='create_date desc', limit=5)

        if recent_feedbacks:
            neg_count = len(recent_feedbacks.filtered(lambda f: f.sentiment == 'negative'))
            neg_ratio = neg_count / len(recent_feedbacks)
            sentiment_score = neg_ratio * 35
            score += sentiment_score
            if neg_count > 0:
                reasons.append(f"{neg_count}/{len(recent_feedbacks)} phản hồi tiêu cực")

        # 3. Cancel rate — tỷ lệ đơn hủy (tối đa 25 điểm)
        all_orders = self.order_ids
        if all_orders:
            cancelled = all_orders.filtered(lambda o: o.state == 'cancel')
            cancel_rate = len(cancelled) / len(all_orders)
            cancel_score = cancel_rate * 25
            score += cancel_score
            if cancel_rate > 0.2:
                reasons.append(f"Tỷ lệ hủy đơn {cancel_rate:.0%}")

        score = min(round(score, 1), 100.0)
        return score, reasons

    def _update_churn_risk(self):
        """Cập nhật score + label + reason cho bản ghi này."""
        self.ensure_one()
        score, reasons = self._compute_churn_score()

        if score >= THRESHOLD_HIGH:
            label = 'high'
        elif score >= THRESHOLD_MED:
            label = 'medium'
        else:
            label = 'low'

        self.write({
            'churn_risk_score': score,
            'churn_risk_label': label,
            'churn_last_computed': date.today(),
            'churn_reason': '; '.join(reasons) if reasons else 'Ổn định',
        })

        # Tự tạo care activity nếu rủi ro cao
        if label == 'high':
            self._create_churn_care_activity(score, reasons)

        return score, label

    def _create_churn_care_activity(self, score, reasons):
        """Tự tạo hoạt động chăm sóc khi KH rủi ro cao."""
        # Không tạo trùng trong vòng 7 ngày
        existing = self.env['khach_hang.care_activity'].search([
            ('customer_id', '=', self.id),
            ('notes', 'ilike', '[F5 Churn]'),
            ('care_date', '>=', str(date.today() - timedelta(days=7))),
        ], limit=1)
        if existing:
            return

        self.env['khach_hang.care_activity'].create({
            'customer_id': self.id,
            'care_date': date.today(),
            'contact_method': 'phone',
            'notes': (
                f"[F5 Churn] ⚠️ Khách hàng có rủi ro rời bỏ cao ({score:.1f}%). "
                f"Lý do: {'; '.join(reasons)}. "
                f"Đề xuất: liên hệ chăm sóc ngay, tặng ưu đãi giữ chân."
            ),
        })
        _logger.info(f"[F5] Tạo care activity cảnh báo churn cho KH {self.name} (score={score:.1f}%)")

    # ── Cron entry point ──────────────────────────────────────────────────────
    @api.model
    def _cron_compute_churn_risk(self):
        """[F5] Scheduled Action — chạy hàng tuần, tính lại churn score cho mọi KH."""
        customers = self.search([])
        _logger.info(f"[F5-CRON] Bắt đầu tính churn risk cho {len(customers)} khách hàng.")
        high_count = 0
        for customer in customers:
            try:
                _, label = customer._update_churn_risk()
                if label == 'high':
                    high_count += 1
            except Exception as e:
                _logger.error(f"[F5] Lỗi khi tính churn cho KH {customer.id}: {e}")

        _logger.info(
            f"[F5-CRON] Hoàn thành. Tổng rủi ro cao: {high_count}/{len(customers)} KH."
        )

    # ── Manual trigger button ─────────────────────────────────────────────────
    def action_compute_churn_risk(self):
        """Nút bấm thủ công — tính ngay churn score cho KH đang mở."""
        for rec in self:
            rec._update_churn_risk()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Churn Risk đã được cập nhật',
                'message': f'Điểm rủi ro: {self.churn_risk_score:.1f}% ({self.churn_risk_label})',
                'type': 'success' if self.churn_risk_label == 'low' else 'warning',
                'sticky': False,
            },
        }
