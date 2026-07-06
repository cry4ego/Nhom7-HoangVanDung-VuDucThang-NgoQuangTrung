# Hiểu Hệ Thống — Quản Lý Khách Hàng + Công Việc (Odoo 15)

> Tài liệu này giải thích **từ code thực tế** — không phải lý thuyết.  
> Đọc xong bạn có thể vẽ sơ đồ, giải thích luồng, và bảo vệ bài làm.
>
> **Repo gốc (fork từ):** https://github.com/rynxu2/16-06-N01

---

## Mục lục
1. [Bức tranh tổng thể](#1-bức-tranh-tổng-thể)
2. [4 Module và vai trò từng cái](#2-4-module-và-vai-trò-từng-cái)
0. [Code base gốc có gì — so sánh với bản hiện tại](#0-code-base-gốc-có-gì--so-sánh-với-bản-hiện-tại)
3. [Quan hệ giữa các model (ERD)](#3-quan-hệ-giữa-các-model-erd)
4. [Luồng nghiệp vụ chính](#4-luồng-nghiệp-vụ-chính)
5. [File cốt lõi cần hiểu](#5-file-cốt-lõi-cần-hiểu)
6. [Những gì đã làm được](#6-những-gì-đã-làm-được)
7. [Cải tiến so với bản gốc](#7-cải-tiến-so-với-bản-gốc)
8. [Câu hỏi bảo vệ thường gặp](#8-câu-hỏi-bảo-vệ-thường-gặp)

---

## 1. Bức tranh tổng thể

Hệ thống giải quyết bài toán: **một công ty cần quản lý nhân viên, khách hàng, đơn hàng và công việc — tất cả liên thông nhau.**

```
┌─────────────────────────────────────────────────────────────────┐
│                        HỆ THỐNG ERP                            │
│                                                                 │
│   [nhan_su]          [customer_management]   [task_management] │
│   Nhân viên    ──►   Khách hàng              Công việc         │
│   (dữ liệu gốc)      Đơn hàng          ◄──  (trung tâm tích   │
│                       Sản phẩm               hợp 3 module)     │
│                                                                 │
│                        [chatbot_support]                        │
│                        AI trả lời tự động                       │
│                        (đọc dữ liệu từ cả 3 module trên)       │
└─────────────────────────────────────────────────────────────────┘
```

**Triết lý thiết kế:** `nhan_su` là nguồn dữ liệu nhân viên duy nhất.  
Hai module còn lại **không tự tạo nhân viên riêng** — họ trỏ vào `nhan_su`.  
Đây là nguyên tắc "một nguồn sự thật" (Single Source of Truth) trong ERP.

---

## 2. 4 Module và vai trò từng cái

### Module 1: `nhan_su` — Dữ liệu gốc về con người

**Vai trò:** Lưu thông tin tất cả nhân viên của công ty.  
**Không phụ thuộc module nào** (depends: `base`).

**Các model bên trong:**

| Model | Tên hiển thị | Lưu gì |
|-------|-------------|--------|
| `nhan_vien` | Nhân viên | Thông tin cá nhân, trạng thái làm việc |
| `chuc_vu` | Chức vụ | Danh mục: Giám đốc, Nhân viên, ... |
| `don_vi` | Đơn vị/Phòng ban | Danh mục: Phòng KD, Phòng KT, ... |
| `lich_su_cong_tac` | Lịch sử công tác | NV từng giữ chức vụ nào, ở đơn vị nào |
| `chung_chi_bang_cap` | Danh mục bằng cấp | Đại học, Thạc sĩ, Chứng chỉ A, ... |
| `danh_sach_chung_chi_bang_cap` | Bằng cấp của NV | NV này có bằng gì |

**Điểm đặc biệt về chức vụ:**  
> ⚠️ Chức vụ **không gắn trực tiếp** vào nhân viên mà gắn qua **lịch sử công tác**.  
> Lý do: một nhân viên có thể thay đổi chức vụ nhiều lần — hệ thống lưu lại toàn bộ lịch sử.  
> Khi demo: xem chức vụ hiện tại ở tab "Lịch sử công tác", tìm bản ghi có `loai_chuc_vu = Chính`.

**Các trường tự động tính (computed fields):**

```python
# ho_va_ten = ho_ten_dem + ' ' + ten
# Ví dụ: "Nguyễn Thị" + "Hoa" = "Nguyễn Thị Hoa"
ho_va_ten = fields.Char(compute="_compute_ho_va_ten", store=True)

# tuoi = năm hiện tại - năm sinh
tuoi = fields.Integer(compute="_compute_tuoi", store=True)

# so_nguoi_bang_tuoi = đếm số NV khác có cùng tuổi
so_nguoi_bang_tuoi = fields.Integer(compute="_compute_so_nguoi_bang_tuoi", store=True)
```

**Ràng buộc (constraints):**
- Tuổi < 18 → báo lỗi
- `ma_dinh_danh` trùng → báo lỗi (SQL constraint)

---

### Module 2: `customer_management` — Nghiệp vụ khách hàng

**Vai trò:** Quản lý toàn bộ vòng đời khách hàng.  
**Phụ thuộc:** `base`, `mail` (không phụ thuộc `nhan_su` trực tiếp, nhưng có trường liên kết).

**Các model bên trong:**

| Model | Tên hiển thị | Lưu gì |
|-------|-------------|--------|
| `khach_hang.customer` | Khách hàng | Tên, email, SĐT, đăng nhập |
| `khach_hang.order` | Đơn hàng | Mã đơn, sản phẩm, tổng tiền, trạng thái |
| `khach_hang.product` | Sản phẩm | Tên, giá, tồn kho |
| `khach_hang.product.category` | Danh mục SP | Phân loại sản phẩm |
| `khach_hang.feedback` | Phản hồi | Câu hỏi/trả lời của KH |
| `khach_hang.care_activity` | Hoạt động chăm sóc | Lịch sử liên hệ chăm sóc KH |
| `khach_hang.potential_customer` | KH tiềm năng | Lead, chưa thành KH chính thức |

**Vòng đời đơn hàng (State Machine):**

```
draft ──► confirmed ──► shipping ──► done
  │                                   
  └──────────────────────────────► cancel
  
Nháp → Xác nhận → Đang giao → Hoàn thành
                               ↘
                            (hoặc) Hủy
```

**Liên kết với HRM:**
```python
# Trong khach_hang.customer:
nhan_vien_phu_trach_id = fields.Many2one('nhan_vien', ...)
# → Mỗi KH có 1 NV phụ trách, lấy từ module nhan_su
```

---

### Module 3: `task_management` — Trung tâm tích hợp

**Vai trò:** Quản lý công việc VÀ là nơi 3 module gặp nhau.  
**Phụ thuộc:** `base`, `mail`, `customer_management`, `nhan_su`.

**Model chính `task.management.task`:**

```python
name          = "Tên công việc"
partner_id    → khach_hang.customer   # KH nào cần xử lý?
order_id      → khach_hang.order      # Từ đơn hàng nào?
nhan_vien_id  → nhan_vien             # Ai thực hiện? (lấy từ HRM)
state         = todo/in_progress/done/cancel
progress      = 0..100 (%)
priority      = Thấp/Trung bình/Cao/Rất quan trọng
deadline      = Hạn chót
```

**Tại sao đây là "trung tâm tích hợp"?**  
Một task duy nhất biết: KH nào → đơn hàng nào → NV nào phụ trách.  
Đây là bằng chứng 3 module đã liên thông thực sự.

**File `order_inherit.py` — cầu nối quan trọng nhất:**

```python
class OrderTaskIntegration(models.Model):
    _inherit = 'khach_hang.order'  # Mở rộng Order, không sửa code gốc
```

Dùng `_inherit` thay vì sửa trực tiếp `order.py` → đây là nguyên tắc **Open/Closed** trong thiết kế phần mềm (mở để mở rộng, đóng để sửa đổi).

---

### Module 4: `chatbot_support` — AI hỗ trợ (Mức 3)

**Vai trò:** Chatbot AI trả lời câu hỏi dựa trên dữ liệu thật trong hệ thống.  
**Công nghệ:** Google Gemini API + RAG (Retrieval-Augmented Generation).

**Luồng xử lý khi người dùng hỏi:**

```
Câu hỏi
   │
   ▼
[1] Tìm tài liệu liên quan trong Knowledge Base (RAG)
   │
   ▼
[2] Lấy dữ liệu thực tế từ DB (đơn hàng, KH, NV, task)
   │
   ▼
[3] Ghép context → gửi lên Gemini API
   │
   ▼
[4] Gemini sinh câu trả lời bằng tiếng Việt
   │
   ▼
[5] Lưu hội thoại vào chatbot.conversation
   │
   ▼
Trả lời cho người dùng
```

**Giao diện:** Floating button 🤖 góc phải dưới, xuất hiện trên mọi trang Odoo backend.

---

## 3. Quan hệ giữa các model (ERD)

```
                    ┌──────────────┐
                    │   chuc_vu    │
                    │  (chức vụ)   │
                    └──────┬───────┘
                           │ Many2one
                    ┌──────▼───────────────────────────────────┐
         ┌──────────┤  lich_su_cong_tac  ├──── Many2one ──────►│ don_vi │
         │          │  (lịch sử công tác)│                     └────────┘
         │          └──────────┬─────────┘
         │                     │ Many2one (nhan_vien_id)
         │          ┌──────────▼─────────────────────────────────────────┐
         │          │              nhan_vien  ◄── DỮ LIỆU GỐC            │
         │          │  ma_dinh_danh, ho_va_ten, tuoi, trang_thai_lam_viec│
         │          └──┬──────────────────────────────────────────────────┘
         │             │                    ▲                    ▲
         │             │ One2many           │ Many2one           │ Many2one
         │    ┌────────▼──────┐             │                    │
         │    │danh_sach_     │    ┌────────┴──────────┐  ┌─────┴──────────────┐
         │    │chung_chi      │    │  khach_hang       │  │  task.management   │
         │    │_bang_cap      │    │  .customer        │  │  .task             │
         │    └───────────────┘    │                   │  │                    │
         │                         │ nhan_vien_phu_trach  │ nhan_vien_id ──────┘
         │                         │ order_ids         │  │ partner_id ────────►khach_hang.customer
         │                         │ feedback_ids      │  │ order_id ──────────►khach_hang.order
         │                         │ care_activity_ids │  │ state/progress     │
         │                         └──────┬────────────┘  └────────────────────┘
         │                                │ One2many              ▲
         │                         ┌──────▼────────────┐         │ AUTO tạo
         │                         │  khach_hang.order │─────────┘ khi tạo đơn
         │                         │                   │
         │                         │ customer_id       │
         │                         │ product_ids       │
         │                         │ state             │
         │                         └──────┬────────────┘
         │                                │ Many2many
         │                         ┌──────▼────────────┐
         └────────────────────────►│ khach_hang.product│
              chung_chi_bang_cap   │ (sản phẩm)        │
                                   └───────────────────┘
```

**Chú thích quan hệ:**

| Loại | Ký hiệu | Ý nghĩa |
|------|---------|---------|
| Many2one | `►` | Nhiều bản ghi trỏ về 1 |
| One2many | ngược lại Many2one | 1 trỏ đến nhiều |
| Many2many | `◄►` | Nhiều - nhiều (qua bảng trung gian) |

---

## 4. Luồng nghiệp vụ chính

### Luồng đầy đủ từ NV → KH → Đơn → Task

```
BƯỚC 1: Nhập nhân viên (nhan_su)
────────────────────────────────
Admin tạo nhân viên trong module nhan_su
→ Nhập họ tên đệm + tên → hệ thống TỰ GHÉP ho_va_ten
→ Nhập ngày sinh → hệ thống TỰ TÍNH tuoi
→ Đặt trạng_thai_lam_viec = "Đang làm việc"
→ Thêm lịch sử công tác → gán chức vụ + phòng ban

BƯỚC 2: Tạo khách hàng (customer_management)
─────────────────────────────────────────────
Tạo KH → chọn "Nhân viên phụ trách" từ danh sách nhan_vien
→ Dữ liệu NV lấy từ module nhan_su, không nhập lại

BƯỚC 3: Tạo đơn hàng (customer_management)
────────────────────────────────────────────
Trong hồ sơ KH → tạo đơn hàng mới
→ Chọn sản phẩm → tổng tiền TỰ TÍNH
→ Nhập ngày giao hàng dự kiến

BƯỚC 4: Hệ thống TỰ ĐỘNG tạo Task (task_management) ⭐
────────────────────────────────────────────────────────
Ngay khi đơn hàng được tạo, order_inherit.py kích hoạt:
1. Tìm NV đang làm việc (trang_thai = 'dang_lam')
2. Đếm task chưa xong của từng NV
3. Chọn NV có ít task nhất (LOAD BALANCING)
4. Tạo task với:
   - Tên: "Xử lý đơn hàng: [mã đơn]"
   - partner_id = khách hàng của đơn
   - order_id = đơn hàng vừa tạo
   - nhan_vien_id = NV được chọn tự động
   - deadline = ngày giao hàng của đơn

BƯỚC 5: Đồng bộ trạng thái (tự động)
──────────────────────────────────────
Khi bấm nút trên đơn hàng → task tự cập nhật:

  Đơn: Xác nhận  →  Task: todo,       progress = 20%
  Đơn: Giao hàng →  Task: in_progress, progress = 70%
  Đơn: Hoàn thành→  Task: done,        progress = 100%
  Đơn: Hủy       →  Task: cancel,      progress = 0%

BƯỚC 6: Hoàn thành → tạo Care Activity (tự động) ⭐
─────────────────────────────────────────────────────
Khi task = done:
→ Hệ thống TỰ ĐỘNG tạo "Hoạt động chăm sóc" trong hồ sơ KH
→ Ghi chú: "Công việc [tên] đã hoàn thành. NV thực hiện: [tên NV]"
→ Quản lý có thể xem lịch sử chăm sóc của từng KH
```

---

### Luồng Chatbot AI

```
Người dùng gõ câu hỏi
        │
        ▼
Chatbot phân tích từ khóa:
  "đơn hàng" → query khach_hang.order
  "khách hàng" → query khach_hang.customer
  "công việc" → query task.management.task
  "nhân viên" → query nhan_vien
  "sản phẩm" → query khach_hang.product
        │
        ▼
Song song: tìm tài liệu trong Knowledge Base
  (7 tài liệu FAQ, chính sách, quy trình)
        │
        ▼
Ghép dữ liệu thực + tài liệu → gửi Gemini API
        │
        ▼
Gemini sinh câu trả lời tiếng Việt, tự nhiên
        │
        ▼
Lưu vào chatbot.conversation (có thể xem lại)
```

---

## 5. File cốt lõi cần hiểu

### `addons/task_management/models/order_inherit.py`

Đây là file quan trọng nhất trong toàn bộ dự án.

```python
class OrderTaskIntegration(models.Model):
    _inherit = 'khach_hang.order'  # ← Mở rộng, không sửa
```

**`_inherit` khác `_name` như thế nào?**

| | `_name = 'new.model'` | `_inherit = 'existing.model'` |
|--|--|--|
| Tạo model mới | ✅ | ❌ |
| Mở rộng model có sẵn | ❌ | ✅ |
| Giữ nguyên dữ liệu cũ | N/A | ✅ |

**Hàm `_find_available_nhan_vien()` — thuật toán load balancing:**

```python
def _find_available_nhan_vien(self):
    # Bước 1: Lấy tất cả NV đang làm việc
    nhan_vien_list = self.env['nhan_vien'].search([
        ('trang_thai_lam_viec', '=', 'dang_lam')
    ])
    
    # Bước 2: Đếm task chưa xong của từng người
    for nv in nhan_vien_list:
        task_count = self.env['task.management.task'].search_count([
            ('nhan_vien_id', '=', nv.id),
            ('state', 'in', ['todo', 'in_progress']),
        ])
    
    # Bước 3: Chọn người có ít task nhất
    return người_ít_task_nhất
```

**Hàm `_update_related_tasks()` — đồng bộ trạng thái:**

```python
def _update_related_tasks(self, order_state):
    if order_state == 'done':
        self.task_ids.action_done()   # Gọi method → kích hoạt tạo care activity
    elif order_state == 'cancel':
        self.task_ids.action_cancel()
    else:
        task_vals = self.ORDER_TO_TASK_STATE.get(order_state, {})
        self.task_ids.write(task_vals)  # Chỉ cập nhật state/progress
```

> **Tại sao 'done' khác?**  
> Vì khi hoàn thành cần chạy thêm logic tạo care activity (trong `action_done` của task).  
> Nếu dùng `write()` trực tiếp → chỉ cập nhật dữ liệu, bỏ qua toàn bộ logic nghiệp vụ.

---

### `addons/chatbot_support/controllers/chatbot_controller.py`

Controller xử lý API `/chatbot/api/chat`:

```
Nhận request POST
→ Tìm/tạo conversation theo session_id
→ Lưu tin nhắn người dùng
→ Gọi _get_bot_response():
    → _retrieve_documents(): tìm KB bằng từ khóa
    → _get_live_data(): query DB thực
    → _build_context(): ghép thành chuỗi context
    → _generate_response(): gọi Gemini API
→ Lưu câu trả lời của bot
→ Trả JSON về client
```

---

## 6. Những gì đã làm được

### ✅ Mức 1 — Dữ liệu và giao diện cơ bản

| Tính năng | File thực hiện | Kết quả test |
|-----------|---------------|-------------|
| Nhân viên với đầy đủ thông tin | `nhan_su/models/nhan_vien.py` | 5 NV trong DB |
| `ho_va_ten` tự ghép từ họ tên đệm + tên | `_compute_ho_va_ten()` | ✅ |
| `tuoi` tự tính từ ngày sinh | `_compute_tuoi()` | ✅ |
| Chặn tuổi < 18 | `_check_tuoi()` | ✅ |
| Chặn mã định danh trùng | `_sql_constraints` | ✅ |
| Trạng thái làm việc (đang làm/tạm nghỉ/đã nghỉ) | field `trang_thai_lam_viec` | ✅ |
| Chức vụ qua lịch sử công tác | `lich_su_cong_tac` model | ✅ |
| Khách hàng có NV phụ trách từ HRM | `nhan_vien_phu_trach_id` | ✅ |
| Đơn hàng với vòng đời (state machine) | `order.py` + nút action | ✅ |
| Tổng tiền đơn tự tính theo sản phẩm | `_compute_total_amount()` | ✅ |
| 5 dữ liệu mẫu mỗi loại | demo data | ✅ |

### ✅ Mức 2 — Tự động hóa qua 3 module

| Tính năng | File thực hiện | Kết quả test |
|-----------|---------------|-------------|
| Tạo đơn → Task tự sinh | `order_inherit.py: create()` | ✅ |
| Task tự gán NV (load balancing) | `_find_available_nhan_vien()` | ✅ NV ít việc nhất |
| Task chứa đủ: KH + đơn + NV | `partner_id, order_id, nhan_vien_id` | ✅ |
| Confirm đơn → task progress 20% | `action_confirm()` | ✅ |
| Giao hàng → task in_progress 70% | `action_ship()` | ✅ |
| Hoàn thành → task done 100% | `action_done()` | ✅ |
| Hủy đơn → task cancel | `action_cancel()` | ✅ |
| Task done → tạo care activity KH | `task.py: action_done()` | ✅ |

### ✅ Mức 3 — AI Chatbot

| Tính năng | File thực hiện | Trạng thái |
|-----------|---------------|-----------|
| Chatbot Gemini + RAG | `chatbot_controller.py` | ✅ Chạy được |
| RAG vector embedding thật (Gemini Embedding API + cosine similarity) | `chatbot_config.generate_embedding()`, `_retrieve_documents_semantic()` | ✅ Mới thêm, tự fallback về keyword search nếu thiếu API key/mạng |
| Confidence score tính thực tế từ độ tương đồng / tỉ lệ khớp từ khóa | `_retrieve_documents_semantic()`, `_retrieve_documents_keyword()` | ✅ Không còn hardcode 0.8 |
| Knowledge Base 7 tài liệu | `chatbot.knowledge.base` | ✅ |
| Truy vấn đơn hàng/KH/task/NV thực | `_get_live_data()` | ✅ |
| Lưu lịch sử hội thoại | `chatbot.conversation` | ✅ 6 cuộc |
| Floating widget trên Odoo backend | `chatbot_widget.js + xml` | ✅ Mới thêm |
| Trang chat standalone `/chatbot` | `chatbot_controller.py` | ✅ |
| External API: Telegram Bot thông báo task mới | `task_management/models/order_inherit.py: _notify_telegram_new_task()` | ✅ Mới thêm, cấu hình tại Settings > Task Management |

---

## 7. Cải tiến so với bản gốc

### Cải tiến 1: Sửa bug `_sql_constraints` (typo)

**Vấn đề:** File gốc viết `_sql_constrains` (thiếu chữ `t`).  
**Hậu quả:** Odoo bỏ qua ràng buộc → có thể tạo 2 NV trùng mã định danh.  
**Sửa:** Đổi thành `_sql_constraints` (đúng chính tả).

```python
# SAI (bản gốc) — Odoo bỏ qua hoàn toàn
_sql_constrains = [...]

# ĐÚNG (đã sửa) — Odoo áp dụng ràng buộc DB
_sql_constraints = [
    ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh phải là duy nhất')
]
```

---

### Cải tiến 2: Sửa bug `compute` sai tên hàm

**Vấn đề:** Field `so_nguoi_bang_tuoi` khai báo `compute="so_nguoi_bang_tuoi"` nhưng tên hàm thật là `_compute_so_nguoi_bang_tuoi`.  
**Hậu quả:** Trường không bao giờ được tính.  
**Sửa:** Thêm dấu `_` vào tên hàm trong khai báo.

```python
# SAI (bản gốc) — tên hàm không khớp
so_nguoi_bang_tuoi = fields.Integer(compute="so_nguoi_bang_tuoi")

# ĐÚNG (đã sửa)
so_nguoi_bang_tuoi = fields.Integer(compute="_compute_so_nguoi_bang_tuoi")
```

---

### Cải tiến 3: Auto-gán nhân viên khi tạo task (Load Balancing)

**Vấn đề:** Bản gốc tạo task nhưng `nhan_vien_id` trống — không ai phụ trách.  
**Hậu quả:** Luồng HRM → KH → Task bị đứt giữa chừng → không đạt Mức 2.  
**Cải tiến:** Thêm thuật toán tự động chọn NV ít việc nhất trong số người đang làm việc.

```
Trước: Tạo đơn → Task sinh ra → nhan_vien_id = TRỐNG ❌

Sau:   Tạo đơn → Tìm NV đang làm → Đếm task chưa xong từng người
                → Chọn người ít nhất → Task có nhan_vien_id ✅
```

---

### Cải tiến 4: Sửa bug _update_related_tasks (care activity)

**Vấn đề:** Khi đơn hàng hoàn thành, code gọi `write({'state': 'done'})` trực tiếp.  
**Hậu quả:** Bỏ qua `action_done()` của task → care activity không được tạo.  
**Sửa:** Phân biệt `done` với các trạng thái khác.

```python
# SAI (bản gốc) — write() bỏ qua toàn bộ business logic
def _update_related_tasks(self, order_state):
    task_vals = self.ORDER_TO_TASK_STATE.get(order_state, {})
    self.task_ids.write(task_vals)  # ← chỉ update DB thuần túy

# ĐÚNG (đã sửa) — gọi method để kích hoạt business logic
def _update_related_tasks(self, order_state):
    if order_state == 'done':
        self.task_ids.action_done()    # ← chạy logic → tạo care activity
    elif order_state == 'cancel':
        self.task_ids.action_cancel()
    else:
        task_vals = self.ORDER_TO_TASK_STATE.get(order_state, {})
        self.task_ids.write(task_vals)
```

---

### Cải tiến 5: Floating Chatbot Widget trên Odoo Backend

**Vấn đề:** Chatbot chỉ có trang standalone (`/chatbot`) — phải mở tab mới.  
**Cải tiến:** Thêm widget OWL xuất hiện trên **mọi trang Odoo** dưới dạng nút nổi 🤖.

```
Trước: Người dùng phải vào /chatbot → trang riêng biệt

Sau:   Nút 🤖 luôn xuất hiện góc phải dưới
       → Click → Panel chat mở ngay, không rời trang
       → Có gợi ý nhanh: Đơn hàng / KH / Công việc / NV
```

**File thêm mới:**
- `static/src/js/chatbot_widget.js` — OWL Component
- `static/src/xml/chatbot_widget.xml` — QWeb template
- `static/src/css/chatbot_widget.css` — Giao diện

---

## 8. Câu hỏi bảo vệ thường gặp

**Q: Tại sao không đặt chức vụ trực tiếp trên nhân viên?**  
A: Vì một nhân viên có thể thay đổi chức vụ nhiều lần. Lưu qua `lich_su_cong_tac` giúp theo dõi lịch sử đầy đủ, không mất dữ liệu cũ. Đây là thiết kế HR thực tế.

**Q: `_inherit` hoạt động thế nào?**  
A: Odoo tự động ghép các trường và method mới vào model hiện có. Dữ liệu vẫn chung một bảng DB. Module `task_management` mở rộng `khach_hang.order` mà không cần sửa code của `customer_management`.

**Q: Load balancing hoạt động thế nào?**  
A: Khi tạo đơn, hệ thống đếm số task chưa xong (`state` = `todo` hoặc `in_progress`) của từng NV đang làm việc. NV có số đếm thấp nhất sẽ được gán. Nếu không có NV nào đang làm → `nhan_vien_id` để trống, quản lý gán tay sau.

**Q: Chatbot có lấy dữ liệu thật không hay bịa?**  
A: Có 2 nguồn: (1) Knowledge Base — tài liệu FAQ nhập tay, (2) Live Data — query trực tiếp từ DB. Gemini chỉ tổng hợp và diễn đạt, không bịa số liệu. Nếu không tìm thấy thông tin, bot nói thẳng "không có dữ liệu".

**Q: Tại sao care activity không tạo được ở bản gốc?**  
A: `write()` là lệnh SQL thuần — chỉ cập nhật cột trong DB. `action_done()` là Python method — chạy toàn bộ business logic bao gồm tạo care activity. Bản gốc dùng `write()` nên bỏ qua logic.

**Q: Mức 1/2/3 khác nhau thế nào trong code?**  
A: Mức 1 = model + view + dữ liệu mẫu. Mức 2 = `_inherit` + automation (`create`, `action_*`). Mức 3 = external API (Gemini) + RAG + giao diện AI. Mỗi mức đòi hỏi hiểu sâu hơn về Odoo framework.

---

---

## 0. Code base gốc có gì — So sánh với bản hiện tại

> Repo gốc: **https://github.com/rynxu2/16-06-N01**  
> Phần này trả lời câu hỏi: *"Em tự làm gì, kế thừa gì từ bản gốc?"*

---

### Tổng quan nhanh

| | Repo gốc (`rynxu2`) | Bản hiện tại (nhóm) |
|--|--|--|
| Module `nhan_su` | ✅ Có (có 2 bug) | ✅ Đã sửa bug + thêm tính năng |
| Module `customer_management` | ✅ Có (thiếu link HRM) | ✅ Đã thêm link NV phụ trách |
| Module `task_management` | ✅ Có (thiếu load balancing) | ✅ Đã thêm auto-assign NV |
| Module `chatbot_support` | ✅ Có (chỉ standalone page) | ✅ Đã thêm floating widget |
| Module `nhan_su` có `trang_thai_lam_viec` | ❌ Không có | ✅ Đã thêm |
| Auto-gán NV khi tạo đơn | ❌ Không có | ✅ Đã thêm (load balancing) |
| Care activity tự động khi task done | ❌ Bug — không hoạt động | ✅ Đã sửa |
| Chatbot widget trên backend Odoo | ❌ Không có | ✅ Đã thêm mới hoàn toàn |

---

### Chi tiết từng file — gốc vs hiện tại

---

#### `addons/nhan_su/models/nhan_vien.py`

**Repo gốc có:**
- Model `nhan_vien` với đầy đủ thông tin cá nhân
- Computed field `ho_va_ten`, `tuoi`, `so_nguoi_bang_tuoi`
- Quan hệ `lich_su_cong_tac_ids`, `danh_sach_chung_chi_bang_cap_ids`
- Constraint tuổi ≥ 18
- **Nhưng có 2 bug:**

```python
# BUG 1 — Repo gốc: sai chính tả, thiếu chữ 't'
# Hậu quả: Odoo bỏ qua hoàn toàn → có thể nhập trùng mã NV
_sql_constrains = [
    ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', '...')
]

# BUG 2 — Repo gốc: sai tên hàm, thiếu tiền tố '_compute_'
# Hậu quả: trường so_nguoi_bang_tuoi không bao giờ được tính
so_nguoi_bang_tuoi = fields.Integer(compute="so_nguoi_bang_tuoi", store=True)
```

**Bản hiện tại sửa + thêm:**
```python
# ĐÃ SỬA BUG 1
_sql_constraints = [
    ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', '...')
]

# ĐÃ SỬA BUG 2
so_nguoi_bang_tuoi = fields.Integer(compute="_compute_so_nguoi_bang_tuoi", store=True)

# MỚI THÊM — field trạng thái làm việc (cần cho load balancing Mức 2)
trang_thai_lam_viec = fields.Selection([
    ('dang_lam', 'Đang làm việc'),
    ('tam_nghi', 'Tạm nghỉ'),
    ('da_nghi', 'Đã nghỉ việc'),
], string="Trạng thái làm việc", default='dang_lam')
```

---

#### `addons/customer_management/models/customer.py`

**Repo gốc có:**
- Model `khach_hang.customer` với name, email, phone, address
- Xác thực đăng nhập (username + password hash SHA256)
- Quan hệ với order, feedback, care_activity
- Tính `order_count`

**Repo gốc KHÔNG có:**
```python
# THIẾU trong repo gốc — khách hàng chưa liên kết HRM
nhan_vien_phu_trach_id = fields.Many2one('nhan_vien', ...)
```

**Bản hiện tại thêm:**
```python
# ĐÃ THÊM — liên kết HRM: mỗi KH có 1 NV phụ trách
nhan_vien_phu_trach_id = fields.Many2one('nhan_vien', string='Nhân viên phụ trách')
```

---

#### `addons/task_management/models/order_inherit.py`

Đây là file có nhiều thay đổi nhất.

**Repo gốc có:**
- `_inherit = 'khach_hang.order'` — kế thừa đúng
- `task_ids` One2many
- `ORDER_TO_TASK_STATE` mapping trạng thái
- `create()` tự tạo task khi tạo đơn
- 4 action override (confirm/ship/done/cancel)

**Repo gốc THIẾU — `create()` không gán nhân viên:**
```python
# REPO GỐC: task sinh ra nhưng nhan_vien_id = TRỐNG
task_vals = {
    'name': f"Xử lý đơn hàng: {order.name}",
    'partner_id': order.customer_id.id if order.customer_id else False,
    'order_id': order.id,
    # ← THIẾU nhan_vien_id → luồng HRM bị đứt, không đạt Mức 2
    'deadline': order.delivery_date,
    'priority': '2',
    'state': 'todo',
    'progress': 0,
}
```

**Repo gốc BUG — `_update_related_tasks` dùng `write()` cho mọi state:**
```python
# REPO GỐC: write() bỏ qua business logic
def _update_related_tasks(self, order_state):
    task_vals = self.ORDER_TO_TASK_STATE.get(order_state, {})
    if task_vals and self.task_ids:
        self.task_ids.write(task_vals)  # ← khi state='done', care activity KHÔNG được tạo
```

**Bản hiện tại thêm + sửa:**
```python
# MỚI THÊM: thuật toán tìm NV ít việc nhất (load balancing)
def _find_available_nhan_vien(self):
    nhan_vien_list = self.env['nhan_vien'].search([
        ('trang_thai_lam_viec', '=', 'dang_lam')  # chỉ lấy NV đang làm
    ])
    best, min_tasks = None, float('inf')
    for nv in nhan_vien_list:
        task_count = self.env['task.management.task'].search_count([
            ('nhan_vien_id', '=', nv.id),
            ('state', 'in', ['todo', 'in_progress']),
        ])
        if task_count < min_tasks:
            min_tasks, best = task_count, nv
    return best

# ĐÃ SỬA: create() gán NV tự động
nhan_vien = self._find_available_nhan_vien()
task_vals = {
    ...
    'nhan_vien_id': nhan_vien.id if nhan_vien else False,  # ← THÊM MỚI
    ...
}

# ĐÃ SỬA: _update_related_tasks phân biệt 'done' để kích hoạt care activity
def _update_related_tasks(self, order_state):
    if not self.task_ids:
        return
    if order_state == 'done':
        self.task_ids.action_done()    # ← gọi method → tạo care activity
    elif order_state == 'cancel':
        self.task_ids.action_cancel()
    else:
        task_vals = self.ORDER_TO_TASK_STATE.get(order_state, {})
        if task_vals:
            self.task_ids.write(task_vals)
```

---

#### `addons/chatbot_support/` — Floating Widget

**Repo gốc có:**
- Backend module (models, views, menus)
- Controller API `/chatbot/api/chat`
- Trang standalone `/chatbot` (file HTML tĩnh)
- Gemini API + RAG pipeline
- Knowledge Base, Conversation history

**Repo gốc KHÔNG có:**
- Widget nổi trên Odoo backend
- Assets JS/CSS đăng ký vào `web.assets_backend`

**Bản hiện tại thêm mới hoàn toàn:**

```
addons/chatbot_support/static/src/
├── js/chatbot_widget.js    ← OWL Component (logic chat)
├── xml/chatbot_widget.xml  ← QWeb template (giao diện)
└── css/chatbot_widget.css  ← Style (nút nổi + panel)
```

```python
# MỚI trong __manifest__.py
'assets': {
    'web.assets_backend': [
        'chatbot_support/static/src/css/chatbot_widget.css',
        'chatbot_support/static/src/xml/chatbot_widget.xml',
        'chatbot_support/static/src/js/chatbot_widget.js',
    ],
},
```

Kết quả: nút 🤖 xuất hiện góc phải dưới trên mọi trang Odoo, không cần mở tab mới.

---

### Tóm tắt: Nhóm tự đóng góp gì so với repo gốc

```
repo gốc (rynxu2/16-06-N01)
        │
        │  Fork + kế thừa toàn bộ cấu trúc
        ▼
bản nhóm
        │
        ├── SỬA BUG (3 bug)
        │   ├── _sql_constrains → _sql_constraints
        │   ├── compute="so_nguoi_bang_tuoi" → "_compute_so_nguoi_bang_tuoi"
        │   └── _update_related_tasks: write() → action_done() khi done
        │
        ├── THÊM TÍNH NĂNG MỨC 1
        │   ├── field trang_thai_lam_viec cho nhân viên
        │   └── field nhan_vien_phu_trach_id cho khách hàng
        │
        ├── THÊM TÍNH NĂNG MỨC 2 (quan trọng nhất)
        │   ├── _find_available_nhan_vien() — load balancing
        │   └── create() gán nhan_vien_id tự động
        │
        └── THÊM TÍNH NĂNG MỨC 3
            └── Floating chatbot widget (OWL Component)
                → js + xml + css + asset registration
```

---

*Tài liệu này phản ánh code thực tế tại thời điểm 30/06/2026.*  
*Cập nhật mỗi khi có thay đổi quan trọng.*
