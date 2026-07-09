# Kiểm thử toàn bộ hệ thống — Quản lý Khách hàng + Công việc + Nhân sự (Odoo 15)

> Dùng file này để tự kiểm tra **toàn bộ** hệ thống trước khi báo cáo/bảo vệ BTL.
> Đánh dấu `[x]` vào từng ô sau khi test xong. Nếu bước nào sai kết quả kỳ vọng,
> ghi lại triệu chứng + copy log lỗi để tra ngược vào code.
>
> Tài liệu liên quan: [`HIEU_HE_THONG.md`](HIEU_HE_THONG.md) (giải thích code),
> [`business-flow/`](business-flow/) (sơ đồ luồng), [`poster/`](poster/) (poster).

---

## 0. Chuẩn bị môi trường

```bash
# 1. Bật PostgreSQL
sudo docker-compose up -d

# 2. Kích hoạt venv
source venv/bin/activate

# 3. Chạy Odoo, upgrade cả 4 module tự viết + --dev=all để thấy traceback đầy đủ
python3 odoo-bin.py -c odoo.conf -d ttdn \
  -u nhan_su,customer_management,task_management,chatbot_support --dev=all
```

- [ ] Log hiện dòng `Modules loaded.` không có traceback đỏ nào ở bước upgrade.
- [ ] Truy cập được `http://localhost:8069`, đăng nhập `admin` / `admin`.

Nếu bước upgrade lỗi ngay từ đầu (trước khi kịp test tính năng gì), copy toàn bộ traceback lại — thường là lỗi cú pháp XML/Python hoặc thiếu field trong view.

---

## 1. Mức 1 — Module `nhan_su` (dữ liệu gốc)

Menu: **QLNS > Quản lý nhân viên**

- [ ] Tạo nhân viên mới, nhập `Họ tên đệm` + `Tên` → field `Họ và tên` tự ghép đúng (không cần nhập tay).
- [ ] Nhập `Ngày sinh` → field `Tuổi` tự tính đúng (năm hiện tại − năm sinh).
- [ ] Xem field `Số người bằng tuổi` — phải hiển thị số nhân viên khác cùng tuổi (không phải luôn = 0/rỗng).
- [ ] Nhập `Ngày sinh` sao cho tuổi < 18 → Lưu → **phải báo lỗi** "Tuổi bé hơn 18" (hoặc tương tự).
- [ ] Tạo nhân viên với `Mã định danh` **trùng** với nhân viên đã có → Lưu → **phải báo lỗi** "Mã định danh phải là duy nhất".
- [ ] Đặt `Trạng thái làm việc` = "Đang làm việc" cho ít nhất 2-3 nhân viên (dùng cho test Mức 2 ở mục 3).
- [ ] Vào tab **Lịch sử công tác** của 1 nhân viên, thêm 1 dòng gán Chức vụ + Đơn vị → Lưu thành công.
- [ ] Menu **QLNS > Danh mục chung > Danh mục đơn vị / Danh mục chức vụ / Danh mục chứng chỉ, bằng cấp** — mở được, CRUD bình thường.
- [ ] Menu **QLNS > Danh sách chứng chỉ, bằng cấp** — thêm được 1 bằng cấp cho nhân viên.
- [ ] Bộ lọc trong danh sách nhân viên: thử filter "Đang làm việc" / "Tạm nghỉ" / "Đã nghỉ việc" — ra đúng kết quả tương ứng.

---

## 2. Mức 1 — Module `customer_management` (nghiệp vụ khách hàng)

Menu: **Quản Lý Khách Hàng**

- [ ] **Khách Hàng** → tạo mới, chọn `Nhân viên phụ trách` từ danh sách nhân sự (dữ liệu lấy từ `nhan_su`, không nhập tay) → Lưu thành công.
- [ ] **Sản Phẩm** → tạo 1-2 sản phẩm mới có giá, thuộc 1 danh mục sản phẩm.
- [ ] **Khách Hàng Tiềm Năng** → tạo mới 1 lead, CRUD bình thường.
- [ ] **Phản Hồi** → tạo 1 phản hồi gắn với 1 khách hàng.
- [ ] **Hoạt Động Chăm Sóc** → xem danh sách (sẽ có thêm bản ghi tự động sau khi test Mức 2 ở mục 3).
- [ ] **Biểu Đồ Đơn Hàng** → mở được, không lỗi render.

---

## 3. Mức 2 — Tự động hóa liên module (`task_management` là trung tâm)

Đây là phần quan trọng nhất để chứng minh 3 module liên thông thật.

### 3.1. Tạo đơn hàng → task tự sinh, tự gán nhân viên (load balancing)

- [ ] Vào **Quản Lý Khách Hàng > Đơn Hàng**, tạo đơn hàng mới (chọn khách hàng có sẵn, thêm sản phẩm, đặt ngày giao hàng dự kiến).
- [ ] Lưu xong, vào **Quản Lý Công Việc > Hoạt động > Tất cả công việc** → phải thấy 1 task mới tên `"Xử lý đơn hàng: <mã đơn>"`.
- [ ] Mở task đó, kiểm tra:
  - [ ] `Khách hàng` (partner_id) = đúng khách hàng của đơn.
  - [ ] `Đơn hàng` (order_id) = đúng đơn vừa tạo.
  - [ ] `Nhân viên` (nhan_vien_id) = **1 nhân viên đang "Đang làm việc"** (không phải người đã "Tạm nghỉ"/"Đã nghỉ việc").
- [ ] Tạo liên tiếp 3-4 đơn hàng nữa → các task mới sinh ra phải **rải đều** cho nhiều nhân viên khác nhau (người đang có ít task `todo`/`in_progress` nhất được ưu tiên gán) — không phải lúc nào cũng rơi vào 1 người.
- [ ] Thử đặt **tất cả** nhân viên về "Tạm nghỉ"/"Đã nghỉ việc", tạo 1 đơn hàng mới → task vẫn tạo được nhưng field `Nhân viên` để **trống** (không báo lỗi, không crash).

### 3.2. Đồng bộ trạng thái đơn hàng ↔ task

Trên đơn hàng vừa tạo ở 3.1, bấm lần lượt và kiểm tra task tương ứng sau mỗi bước:

| Bấm nút trên đơn hàng | Task kỳ vọng | Đã test |
|---|---|---|
| Xác nhận | `state = todo`, `progress = 20%` | [ ] |
| Giao hàng | `state = in_progress`, `progress = 70%` | [ ] |
| Hoàn thành | `state = done`, `progress = 100%` | [ ] |

- [ ] Test nhánh **Hủy đơn** (tạo đơn khác riêng để test) → task chuyển `state = cancel`.

### 3.3. Task hoàn thành → tự tạo Care Activity

- [ ] Sau khi bấm "Hoàn thành" ở đơn hàng 3.2, vào hồ sơ khách hàng của đơn đó → tab/menu **Hoạt Động Chăm Sóc**.
- [ ] Phải thấy **1 bản ghi mới tự động sinh**, nội dung ghi chú có nhắc tên công việc + tên nhân viên thực hiện.

### 3.4. External API — Telegram khi task được auto-gán

Chuẩn bị trước (1 lần, ngoài Odoo):
1. Tạo bot qua `@BotFather` trên Telegram → lấy **Bot Token**.
2. Thêm bot vào 1 group Telegram, gửi 1 tin nhắn bất kỳ vào group.
3. Mở `https://api.telegram.org/bot<TOKEN>/getUpdates` → lấy **Chat ID** (số âm dạng `-100...`).

Test trong Odoo:
- [ ] Vào **Settings > Task Management**, bật "Thông báo Telegram khi có công việc mới", nhập Bot Token + Chat ID, Lưu.
- [ ] Tạo 1 đơn hàng mới (như 3.1) → group Telegram phải nhận được tin nhắn có đủ: tên đơn, khách hàng, tên task, người phụ trách, hạn chót.
- [ ] Tắt lại tùy chọn thông báo → tạo đơn hàng mới → **không** có tin nhắn Telegram nào gửi, đơn hàng vẫn tạo bình thường.
- [ ] Test khi nhập sai Bot Token → tạo đơn hàng → đơn hàng/task vẫn tạo thành công (không bị lỗi 500), chỉ có dòng `Telegram API lỗi:`/`Telegram API exception:` trong log terminal.

---

## 4. Mức 3 — AI Chatbot (`chatbot_support`)

### 4.1. Cấu hình

- [ ] Vào **AI Chatbot > Cấu hình**, kiểm tra đã có 1 bản ghi cấu hình đang **Kích hoạt**, đã nhập **Gemini API Key** thật (https://aistudio.google.com/app/apikey), model embedding mặc định `models/gemini-embedding-001`.

### 4.2. Knowledge Base + vector embedding

- [ ] Vào **AI Chatbot > Knowledge Base**, đã có sẵn ~7 tài liệu mẫu (FAQ/chính sách/sản phẩm...).
- [ ] Mở 1 tài liệu, sửa nhẹ nội dung rồi Lưu → mở lại, field `embedding_vector` phải có dữ liệu (chuỗi JSON dài các số thực), không còn rỗng.
- [ ] Nếu vẫn rỗng: xem log terminal tìm dòng `Lỗi khi gọi Gemini Embedding API:` để biết nguyên nhân (thường do API key sai/hết quota/không có mạng).

### 4.3. Chat — RAG vector + fallback keyword

- [ ] Mở widget 🤖 (nút nổi góc phải dưới trên mọi trang Odoo backend) hoặc trang `http://localhost:8069/chatbot`.
- [ ] Hỏi 1 câu **đúng từ khóa** có trong Knowledge Base (VD tên sản phẩm/chính sách) → bot trả lời đúng nội dung liên quan.
- [ ] Hỏi 1 câu **diễn đạt khác đi** (không trùng từ khóa) nhưng cùng ý nghĩa với 1 tài liệu → bot vẫn trả lời đúng (chứng minh semantic/vector search hoạt động, không chỉ so khớp chữ).
- [ ] Hỏi câu có chứa từ khóa "đơn hàng"/"khách hàng"/"công việc"/"nhân viên"/"sản phẩm" → câu trả lời phải trích được **số liệu thật** từ DB (không bịa), khớp với dữ liệu vừa tạo ở mục 2-3.
- [ ] Vào **AI Chatbot > Lịch sử Chat**, mở conversation vừa test, xem field `confidence_score` của từng tin nhắn bot — giá trị phải **khác nhau tùy câu hỏi** (không cố định 1 số duy nhất).
- [ ] **Test fallback:** tạm sửa sai Gemini API Key trong Cấu hình → hỏi lại 1 câu đúng từ khóa trong Knowledge Base → bot vẫn trả lời được (rơi về keyword search), không bị lỗi/treo. Nhớ sửa lại API key đúng sau khi test xong.
- [ ] Test đánh giá hội thoại (nếu có nút rating trên widget) → gửi đánh giá → không lỗi.

---

## 5. Mức 3 nâng cao — Bộ tính năng AI F1–F10

> **Chuẩn bị chung:** bật Developer Mode để chạy cron thủ công:
> **Settings > General Settings**, cuộn xuống cuối → mục **Developer Tools** → **Activate the developer mode**.
> Sau đó menu chạy cron nằm ở: **Settings > Technical > Automation > Scheduled Actions**.
> Các tính năng gọi Gemini (F1/F4/F10) cần API key còn quota; hết quota thì rơi về fallback (vẫn không được crash).

### 5.1. F1 — AI Smart Priority (task_management)

- [ ] Tạo 1 đơn hàng mới (giá trị lớn hoặc ngày giao gần) → mở task vừa tự sinh.
- [ ] Field `Độ ưu tiên` của task **không phải lúc nào cũng là mặc định "Cao" (2)** — AI chọn 0–3 theo ngữ cảnh đơn.
- [ ] Xem log terminal: có dòng `[F1-AI] Priority đề xuất bởi AI: <n>` (hoặc `[F1-AI] Gemini không khả dụng..., dùng rule-based fallback` nếu hết quota — đơn hàng vẫn phải tạo thành công).

### 5.2. F3 — Auto Escalation task quá hạn (task_management)

- [ ] Mở 1 task đang `todo`/`in_progress`, sửa `Hạn chót` thành **hôm qua** (quá hạn 1 ngày).
- [ ] Mở 1 task khác, sửa `Hạn chót` lùi **6+ ngày** (để test tái phân công).
- [ ] Vào **Settings > Technical > Automation > Scheduled Actions** → mở `[F3] Kiểm tra Task quá hạn & Tự động Leo thang` → bấm **Run Manually**.
- [ ] Task quá hạn 1 ngày: checkbox `Đã gửi cảnh báo` = ✔; nếu đã bật Telegram → group nhận tin `⚠️ CẢNH BÁO: Task quá hạn...`.
- [ ] Task quá hạn 6 ngày: field `Nhân viên` **đổi sang người khác** (người ít việc nhất), chatter của task có ghi chú `🔄 [Tự động - F3 Escalation] ... Tái phân công từ A → B`.
- [ ] Chạy cron lần 2 → task đã cảnh báo rồi **không gửi lại** (escalation_sent chống spam).

### 5.3. F4 — Sentiment Analysis phản hồi (customer_management)

- [ ] **Quản Lý Khách Hàng > Phản Hồi** → tạo phản hồi mới với câu tiêu cực rõ (VD: *"Dịch vụ quá tệ, giao hàng trễ, tôi rất thất vọng"*) → Lưu.
- [ ] Mở lại bản ghi: `Cảm xúc` = 😠 Tiêu cực, `Điểm cảm xúc` âm (gần −1), `Giải thích AI` có nội dung.
- [ ] Tạo phản hồi tích cực (VD: *"Sản phẩm tuyệt vời, nhân viên nhiệt tình"*) → `Cảm xúc` = 😊 Tích cực, điểm dương.
- [ ] Hết quota Gemini → phản hồi vẫn lưu bình thường, 3 field sentiment để trống (xem log `[F4]`).

### 5.4. F5 — Churn Detection (customer_management)

- [ ] Mở 1 khách hàng → bấm nút **🔄 Tính Churn Risk** → 4 field cập nhật: `Rủi ro rời bỏ (%)`, `Mức rủi ro` (🟢/🟡/🔴), `Tính lần cuối`, `Lý do rủi ro`.
- [ ] Dựng 1 KH rủi ro cao để test: KH có vài phản hồi tiêu cực (từ 5.3) + 1-2 đơn bị hủy + lâu không có đơn hoàn thành → bấm tính lại → score ≥ 65% (🔴 Cao).
- [ ] KH 🔴 Cao: vào **Hoạt Động Chăm Sóc** → có bản ghi tự sinh chứa `[F5 Churn] ⚠️ Khách hàng có rủi ro rời bỏ cao...`.
- [ ] Bấm tính lại lần nữa trong ngày → **không tạo care activity trùng** (chống trùng 7 ngày).
- [ ] Chạy cron `[F5] Tính điểm Churn Risk cho toàn bộ Khách hàng` (Run Manually) → mọi KH đều có score; danh sách KH tô màu đỏ/vàng theo mức rủi ro.

### 5.5. F7 — Conversational Commerce (chatbot_support)

> Widget 🤖 và trang `/chatbot` hiện gọi endpoint v1; F7 chạy ở endpoint riêng `/chatbot/api/chat/v2` — test bằng curl:

```bash
# Intent: kiểm tra đơn hàng (thay ORD001 bằng mã đơn thật trong DB)
curl -s -X POST http://localhost:8069/chatbot/api/chat/v2 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"message":"Kiểm tra đơn hàng ORD001 giúp tôi","session_id":"test-f7-1"}}'

# Intent: tìm sản phẩm theo ngưỡng giá
curl -s -X POST http://localhost:8069/chatbot/api/chat/v2 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"message":"Tìm sản phẩm dưới 20 triệu","session_id":"test-f7-2"}}'

# Intent: yêu cầu hỗ trợ / đổi trả
curl -s -X POST http://localhost:8069/chatbot/api/chat/v2 -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"message":"Tôi muốn đổi trả sản phẩm","session_id":"test-f7-3"}}'
```

- [ ] Câu 1: trả về đúng trạng thái/tổng tiền của đơn được hỏi (dữ liệu thật từ DB).
- [ ] Câu 2: liệt kê sản phẩm có giá dưới ngưỡng hỏi.
- [ ] Câu 3: trả lời quy trình hỗ trợ/đổi trả.
- [ ] Log terminal có dòng `[F7]` nhận diện intent tương ứng.

### 5.6. F9 — Self-learning Knowledge Base (chatbot_support)

- [ ] Chat vài câu với bot (widget 🤖) để có tin nhắn bot trong DB.
- [ ] Vào **AI Chatbot > Lịch sử Chat** → mở conversation vừa chat → tab tin nhắn → click 1 dòng tin nhắn **bot** → đặt `Đánh giá tin nhắn` = 👎 Không tốt → Lưu.
- [ ] Chạy cron `[F9] Phân tích câu trả lời bị đánh giá thấp → KB draft` (Run Manually).
- [ ] Vào **AI Chatbot > Knowledge Base** → ⚠️ draft ở trạng thái **archived** nên danh sách mặc định KHÔNG hiển thị: bấm **Filters > Archived** → thấy bản ghi mới tên bắt đầu bằng `[F9 Draft]` kèm câu hỏi gốc (admin sửa nội dung trả lời đúng rồi bấm Unarchive để kích hoạt).
- [ ] Tin nhắn 👎 đó được đánh dấu `flagged_for_review` = ✔ → chạy cron lần 2 **không tạo draft trùng**.

### 5.7. F10 — AI Dashboard (chatbot_support)

- [ ] Chạy cron `[F10] Sinh AI Business Summary hàng ngày` (Run Manually).
- [ ] Vào **AI Chatbot > 🤖 AI Dashboard** → có bản ghi hôm nay: 6 ô KPI (đơn hôm nay, doanh thu, task quá hạn, task đang mở, KH churn cao, phản hồi tiêu cực) + đoạn tóm tắt điều hành tiếng Việt do Gemini viết.
- [ ] Chạy cron lần 2 trong cùng ngày → **không sinh trùng** (log `Summary đã tồn tại cho hôm nay, bỏ qua`). Muốn sinh lại: xóa bản ghi hôm nay rồi chạy cron.
- [ ] Số KPI khớp dữ liệu thật (đối chiếu số task quá hạn với danh sách task, số KH 🔴 với mục 5.4).

---

## 6. Kiểm tra tích hợp dữ liệu chung (Mức 1 bắt buộc)

- [ ] Xóa/sửa 1 nhân viên trong `nhan_su` → tất cả nơi tham chiếu (khách hàng phụ trách, task đang gán) phản ánh đúng thay đổi (không có bản ghi nhân viên "ảo" tạo riêng ở module khác).
- [ ] Xác nhận: không module nào (`customer_management`, `task_management`, `chatbot_support`) có model/tính năng tự tạo nhân viên riêng — tất cả đều dùng `Many2one('nhan_vien', ...)` trỏ về `nhan_su`.
- [ ] Không có dữ liệu hiển thị hardcode: mọi số liệu chatbot trả lời, mọi danh sách trong view đều đọc trực tiếp từ DB (kiểm tra bằng cách sửa dữ liệu gốc rồi hỏi lại chatbot/xem lại view — số liệu phải cập nhật theo).

---

## 7. Kiểm tra tài liệu nộp kèm (không phải code)

- [ ] File `docs/business-flow/Nhom07_BusinessFlow_QuanLyKhachHang_QuanLyCongViec.pdf` mở được, đọc rõ chữ, đủ: actor, các bước, điểm tích hợp HRM, trigger Mức 2, điểm AI/API Mức 3.
- [ ] File `docs/poster/Nhom07_Poster_HeThongERP.pdf` mở được, đọc rõ chữ.
- [ ] `README.md` gốc + `docs/business-flow/README.md` có mô tả ngắn gọn luồng đang vẽ và các module tham gia.
- [ ] `git log` của repo thể hiện lịch sử commit rải rác theo thời gian (không phải 1 commit duy nhất dồn hết vào cuối kỳ).

---

## 8. Bảng tổng hợp kết quả (điền tay trước khi nộp/bảo vệ)

| Hạng mục | Đạt | Ghi chú lỗi (nếu có) |
|---|---|---|
| Mức 1 — nhan_su (mục 1) | [ ] | |
| Mức 1 — customer_management (mục 2) | [ ] | |
| Mức 2 — auto task + load balancing (mục 3.1) | [ ] | |
| Mức 2 — đồng bộ trạng thái (mục 3.2) | [ ] | |
| Mức 2 — care activity tự động (mục 3.3) | [ ] | |
| Mức 3 — Telegram External API (mục 3.4) | [ ] | |
| Mức 3 — Chatbot RAG vector + fallback (mục 4) | [ ] | |
| F1 — AI Smart Priority (mục 5.1) | [ ] | |
| F3 — Auto Escalation (mục 5.2) | [ ] | |
| F4 — Sentiment Analysis (mục 5.3) | [ ] | |
| F5 — Churn Detection (mục 5.4) | [ ] | |
| F7 — Conversational Commerce (mục 5.5) | [ ] | |
| F9 — Self-learning KB (mục 5.6) | [ ] | |
| F10 — AI Dashboard (mục 5.7) | [ ] | |
| Tích hợp dữ liệu chung / không hardcode (mục 6) | [ ] | |
| Tài liệu nộp kèm (mục 7) | [ ] | |

---

## 9. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân thường gặp | Cách kiểm tra |
|---|---|---|
| Upgrade module lỗi ngay | Sai cú pháp Python/XML trong file vừa sửa | Đọc traceback cuối cùng trong log, tìm đúng tên file:dòng |
| Sửa code Python nhưng hành vi không đổi | `--dev=all` KHÔNG tự reload vì venv thiếu package `watchdog` | `pip install watchdog` hoặc restart Odoo thủ công sau mỗi lần sửa |
| Lỗi `InFailedSqlTransaction` / thiếu cột DB | Code có field mới nhưng chưa upgrade module (schema lệch) | Restart với `-u <module>` |
| Task không tự tạo khi tạo đơn | `order_inherit.py` chưa được load (chưa `-u task_management`) | Chạy lại lệnh upgrade ở mục 0 |
| `nhan_vien_id` của task luôn trống | Không còn nhân viên nào ở trạng thái "Đang làm việc" | Vào QLNS kiểm tra lại trạng thái nhân viên |
| Không nhận được tin nhắn Telegram | Sai Bot Token/Chat ID, hoặc bot chưa được thêm vào group | Xem log dòng `Telegram API lỗi:`; gọi thử `getUpdates` |
| Chatbot luôn trả lời fallback message | Sai/hết hạn Gemini API Key, hoặc hết quota | Xem log dòng `GEMINI FAILED` / `Lỗi khi gọi Gemini Embedding API:` |
| `embedding_vector` luôn rỗng | Model embedding lỗi thời (Google đã ngừng `text-embedding-004`) hoặc API key lỗi | Cấu hình phải là `models/gemini-embedding-001`; sửa nội dung tài liệu 1 lần để trigger sinh lại |
| `confidence_score` vẫn thấy giống nhau nhiều câu | Đang rơi vào nhánh fallback keyword (không phải bug) | Kiểm tra Gemini API Key còn hoạt động không |
| Cron F1/F4/F10 trả kết quả fallback đơn giản | Gemini hết quota (429) — thiết kế chấp nhận | Xem log `[F1-AI]`/`[F4]`/`[F10]`, thử lại sau vài phút |
| Sentiment/Churn không cập nhật trên form | View đang mở bản cache cũ | F5 (refresh trình duyệt) sau khi chạy cron/nút tính |
