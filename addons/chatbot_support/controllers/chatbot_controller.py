# -*- coding: utf-8 -*-
import json
import logging
import math
import requests
from datetime import datetime
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a, vec_b):
    """Độ tương đồng cosin giữa 2 vector embedding (thuần Python, không cần numpy)."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ChatbotController(http.Controller):

    @http.route('/chatbot', type='http', auth='public', website=False, csrf=False)
    def chatbot_page(self, **kwargs):
        """Trang giao diện chat cho khách hàng"""
        import os
        chat_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'src', 'chat.html')
        with open(chat_path, 'r', encoding='utf-8') as f:
            return f.read()

    @http.route('/chatbot/api/chat', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def chat(self, message, session_id=None, partner_id=None, **kwargs):
        """
        Main chat endpoint
        
        Args:
            message (str): User's message
            session_id (str): Session ID for conversation tracking
            partner_id (int): Optional customer ID
        
        Returns:
            dict: {
                'response': str,
                'conversation_id': int,
                'message_id': int,
                'success': bool
            }
        """
        try:
            # Get or create conversation
            conversation = self._get_or_create_conversation(session_id, partner_id, kwargs)
            
            # Save user message
            user_message = request.env['chatbot.message'].sudo().create({
                'conversation_id': conversation.id,
                'message_type': 'user',
                'content': message,
            })
            
            # Get chatbot response using RAG
            bot_response, metadata = self._get_bot_response(message, conversation)
            
            # Save bot message
            bot_message = request.env['chatbot.message'].sudo().create({
                'conversation_id': conversation.id,
                'message_type': 'bot',
                'content': bot_response,
                'retrieved_docs': json.dumps(metadata.get('retrieved_docs', [])),
                'confidence_score': metadata.get('confidence_score', 0.0),
                'model_used': metadata.get('model_used', 'gemini-1.5-flash'),
                'response_time': metadata.get('response_time', 0.0),
            })
            
            return {
                'success': True,
                'response': bot_response,
                'conversation_id': conversation.id,
                'message_id': bot_message.id,
                'metadata': metadata
            }
            
        except Exception as e:
            _logger.error(f"Chatbot error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'response': 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.'
            }
    
    @http.route('/chatbot/api/welcome', type='json', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_welcome_message(self, **kwargs):
        """Get welcome message from config"""
        try:
            config = request.env['chatbot.config'].sudo().get_active_config()
            return {
                'success': True,
                'message': config.welcome_message
            }
        except Exception as e:
            return {
                'success': False,
                'message': 'Xin chào! Tôi có thể giúp gì cho bạn?'
            }
    
    @http.route('/chatbot/api/rate', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def rate_conversation(self, conversation_id, rating, feedback=None, **kwargs):
        """Rate a conversation"""
        try:
            conversation = request.env['chatbot.conversation'].sudo().browse(conversation_id)
            if conversation.exists():
                conversation.write({
                    'rating': str(rating),
                    'feedback': feedback
                })
                return {'success': True}
            return {'success': False, 'error': 'Conversation not found'}
        except Exception as e:
            _logger.error(f"Rating error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_or_create_conversation(self, session_id, partner_id, request_data):
        """Get existing conversation or create new one"""
        Conversation = request.env['chatbot.conversation'].sudo()
        
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"
        
        # Try to find existing active conversation
        conversation = Conversation.search([
            ('session_id', '=', session_id),
            ('state', '=', 'active')
        ], limit=1)
        
        if not conversation:
            # Create new conversation
            vals = {
                'session_id': session_id,
                'user_ip': request_data.get('user_ip'),
                'user_agent': request_data.get('user_agent'),
            }
            if partner_id:
                vals['partner_id'] = partner_id
            
            conversation = Conversation.create(vals)
        
        return conversation
    
    def _get_bot_response(self, user_message, conversation):
        """
        Get bot response using RAG pipeline
        
        This method will:
        1. Call RAG service to retrieve relevant documents
        2. Call Gemini API to generate response
        3. Return response and metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Get config
            config = request.env['chatbot.config'].sudo().get_active_config()
            
            # Step 1: Retrieve relevant documents from knowledge base
            retrieved_docs, confidence_score = self._retrieve_documents(user_message, config)

            # Step 2: Build context from retrieved documents + live data
            kb_context = self._build_context(retrieved_docs)
            live_context = self._get_live_data(user_message, conversation)
            context = kb_context + "\n\n" + live_context

            # Step 3: Generate response using Gemini
            response = self._generate_response(user_message, context, config, conversation)

            # Calculate response time
            response_time = time.time() - start_time

            # Update usage count for retrieved docs
            for doc in retrieved_docs:
                doc.increment_usage()

            metadata = {
                'retrieved_docs': [doc.id for doc in retrieved_docs],
                'confidence_score': confidence_score,
                'model_used': config.gemini_model,
                'response_time': response_time,
            }
            
            return response, metadata
            
        except Exception as e:
            _logger.error(f"RAG error: {str(e)}", exc_info=True)
            # Return fallback message
            config = request.env['chatbot.config'].sudo().get_active_config()
            return config.fallback_message, {'error': str(e)}
    
    def _get_live_data(self, user_message, conversation):
        """Truy vấn dữ liệu thực từ hệ thống dựa trên câu hỏi của khách hàng"""
        live_parts = []
        msg_lower = user_message.lower()

        # Nếu khách hỏi về đơn hàng
        if any(kw in msg_lower for kw in ['đơn hàng', 'đơn', 'order', 'mua', 'đặt']):
            orders = request.env['khach_hang.order'].sudo().search([], limit=10, order='create_date desc')
            if orders:
                lines = ["=== DỮ LIỆU ĐƠN HÀNG THỰC TẾ ==="]
                for o in orders:
                    lines.append(
                        f"- {o.name}: KH={o.customer_id.name or 'N/A'}, "
                        f"Tổng={o.total_amount:,.0f} VNĐ, Trạng thái={o.state or 'draft'}"
                    )
                live_parts.append("\n".join(lines))

        # Nếu khách hỏi về khách hàng
        if any(kw in msg_lower for kw in ['khách hàng', 'khách', 'customer']):
            customers = request.env['khach_hang.customer'].sudo().search([], limit=10)
            if customers:
                lines = ["=== DỮ LIỆU KHÁCH HÀNG THỰC TẾ ==="]
                for c in customers:
                    lines.append(
                        f"- {c.name}: Email={c.email or 'N/A'}, SĐT={c.phone or 'N/A'}, "
                        f"Số đơn={c.order_count}"
                    )
                live_parts.append("\n".join(lines))

        # Nếu khách hỏi về công việc / task
        if any(kw in msg_lower for kw in ['công việc', 'task', 'tiến độ', 'trạng thái']):
            tasks = request.env['task.management.task'].sudo().search([], limit=10, order='create_date desc')
            if tasks:
                lines = ["=== DỮ LIỆU CÔNG VIỆC THỰC TẾ ==="]
                for t in tasks:
                    lines.append(
                        f"- {t.name}: NV={t.nhan_vien_id.ho_va_ten or 'Chưa gán'}, "
                        f"Trạng thái={t.state}, Tiến độ={t.progress}%"
                    )
                live_parts.append("\n".join(lines))

        # Nếu khách hỏi về nhân viên
        if any(kw in msg_lower for kw in ['nhân viên', 'nhan vien', 'staff', 'người phụ trách']):
            employees = request.env['nhan_vien'].sudo().search([], limit=10)
            if employees:
                lines = ["=== DỮ LIỆU NHÂN VIÊN THỰC TẾ ==="]
                for nv in employees:
                    lines.append(
                        f"- {nv.ho_va_ten}: MĐD={nv.ma_dinh_danh}, "
                        f"Trạng thái={nv.trang_thai_lam_viec or 'N/A'}"
                    )
                live_parts.append("\n".join(lines))

        # Nếu khách hỏi về sản phẩm
        if any(kw in msg_lower for kw in ['sản phẩm', 'product', 'hàng hóa', 'giá']):
            products = request.env['khach_hang.product'].sudo().search([], limit=10)
            if products:
                lines = ["=== DỮ LIỆU SẢN PHẨM THỰC TẾ ==="]
                for p in products:
                    price = getattr(p, 'price', 0) or getattr(p, 'list_price', 0) or 0
                    lines.append(f"- {p.name}: Giá={price:,.0f} VNĐ")
                live_parts.append("\n".join(lines))

        if not live_parts:
            return ""
        return "\n\n".join(live_parts)

    def _retrieve_documents(self, query, config):
        """
        Retrieve relevant documents from knowledge base.

        Ưu tiên semantic search bằng vector embedding (Gemini). Nếu không thể
        (thiếu API key, chưa có doc nào có embedding, hoặc lỗi mạng) thì rơi về
        keyword search như cũ. Trả về (docs, confidence_score) để metadata phản
        ánh đúng chất lượng của kết quả tìm được thay vì giá trị hardcode.
        """
        semantic_docs, semantic_score = self._retrieve_documents_semantic(query, config)
        if semantic_docs:
            _logger.info(f"RAG Search (semantic): {len(semantic_docs)} docs, top_score={semantic_score:.3f}")
            return semantic_docs, semantic_score

        docs, confidence = self._retrieve_documents_keyword(query, config)
        return docs, confidence

    def _retrieve_documents_semantic(self, query, config):
        """Semantic search dựa trên cosine similarity giữa embedding của câu hỏi
        và embedding đã lưu sẵn của từng tài liệu trong knowledge base."""
        KnowledgeBase = request.env['chatbot.knowledge.base'].sudo()

        docs_with_embedding = KnowledgeBase.search([
            ('active', '=', True),
            ('embedding_vector', '!=', False),
        ])
        if not docs_with_embedding:
            return KnowledgeBase, 0.0

        query_vector = config.generate_embedding(query)
        if not query_vector:
            return KnowledgeBase, 0.0

        scored = []
        for doc in docs_with_embedding:
            try:
                doc_vector = json.loads(doc.embedding_vector)
            except (ValueError, TypeError):
                continue
            score = _cosine_similarity(query_vector, doc_vector)
            if score >= config.similarity_threshold:
                scored.append((score, doc))

        if not scored:
            return KnowledgeBase, 0.0

        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:config.top_k_results]
        top_score = top[0][0]
        doc_ids = [doc.id for _, doc in top]
        docs = KnowledgeBase.browse(doc_ids)
        return docs, top_score

    def _retrieve_documents_keyword(self, query, config):
        """Keyword search (fallback) - searches each word separately then combines results."""
        KnowledgeBase = request.env['chatbot.knowledge.base'].sudo()

        _logger.info(f"RAG Search (keyword fallback): query='{query}'")

        # Strategy 1: Try full query first
        docs = KnowledgeBase.search([
            ('active', '=', True),
            '|', '|',
            ('name', 'ilike', query),
            ('content_plain', 'ilike', query),
            ('keywords', 'ilike', query)
        ], limit=config.top_k_results, order='priority desc, usage_count desc')

        if docs:
            _logger.info(f"RAG Search: Full query found {len(docs)} docs")
            return docs, 0.6

        # Strategy 2: If no results, try individual words
        query_words = [w for w in query.lower().split() if len(w) >= 2]
        _logger.info(f"RAG Search: Trying words: {query_words}")

        doc_ids = set()
        for word in query_words:
            word_docs = KnowledgeBase.search([
                ('active', '=', True),
                '|', '|',
                ('name', 'ilike', word),
                ('content_plain', 'ilike', word),
                ('keywords', 'ilike', word)
            ])
            doc_ids.update(word_docs.ids)
            _logger.info(f"RAG Search: Word '{word}' found {len(word_docs)} docs")

        if not doc_ids:
            return KnowledgeBase, 0.0

        docs = KnowledgeBase.browse(list(doc_ids))
        docs = docs.sorted(key=lambda d: (d.priority, d.usage_count), reverse=True)
        docs = docs[:config.top_k_results]

        # Confidence tỉ lệ với số từ khóa khớp được trên tổng số từ trong câu hỏi
        matched_ratio = min(len(doc_ids), len(query_words)) / max(len(query_words), 1)
        confidence = round(0.3 + 0.3 * matched_ratio, 2)
        return docs, confidence
    
    def _build_context(self, documents):
        """Build context string from retrieved documents"""
        if not documents:
            return "Không có thông tin liên quan trong knowledge base."
        
        context_parts = []
        total_chars = 0
        max_context_chars = 8000  # Limit context to ~2000 tokens
        
        for i, doc in enumerate(documents, 1):
            # Get content, truncate if too long
            content = doc.content_plain or ""
            
            # Add document with clear formatting
            doc_text = f"""
=== TÀI LIỆU {i}: {doc.name} ===
{content}
===================================
"""
            
            # Check if adding this doc would exceed limit
            if total_chars + len(doc_text) > max_context_chars:
                # Truncate this document
                remaining = max_context_chars - total_chars
                if remaining > 200:  # Only add if we have meaningful space
                    truncated = content[:remaining] + "...[đã cắt bớt]"
                    doc_text = f"""
=== TÀI LIỆU {i}: {doc.name} ===
{truncated}
===================================
"""
                    context_parts.append(doc_text)
                break
            
            context_parts.append(doc_text)
            total_chars += len(doc_text)
        
        _logger.info(f"Built context with {len(context_parts)} documents, {total_chars} chars")
        return "\n".join(context_parts)
    
    def _generate_response(self, user_message, context, config, conversation):
        """
        Generate response using Gemini API
        """
        try:
            history = self._get_conversation_history(conversation, limit=5)
            prompt = self._build_prompt(user_message, context, history, config)
            _logger.warning(f"=== CALLING GEMINI API === model={config.gemini_model}")
            response = self._call_gemini_api(prompt, config)
            _logger.warning(f"=== GEMINI OK === {response[:80]}")
            return response

        except Exception as e:
            import traceback
            _logger.error(f"=== GEMINI FAILED === {str(e)}")
            _logger.error(traceback.format_exc())
            return config.fallback_message
    
    def _get_conversation_history(self, conversation, limit=5):
        """Get recent conversation history"""
        messages = request.env['chatbot.message'].sudo().search([
            ('conversation_id', '=', conversation.id)
        ], order='create_date desc', limit=limit * 2)
        
        history = []
        for msg in reversed(messages):
            role = 'user' if msg.message_type == 'user' else 'model'
            history.append({
                'role': role,
                'parts': [msg.content]
            })
        
        return history
    
    def _build_prompt(self, user_message, context, history, config):
        """Build the full prompt for Gemini"""
        system_prompt = config.system_prompt
        
        prompt = f"""{system_prompt}

THÔNG TIN TỪ KNOWLEDGE BASE VÀ DỮ LIỆU HỆ THỐNG:
{context}

---

HƯỚNG DẪN TRẢ LỜI:
1. ĐỌC KỸ nội dung trong các tài liệu và dữ liệu hệ thống trên
2. TÌM KIẾM thông tin liên quan đến câu hỏi của khách hàng
3. TỔNG HỢP và trả lời dựa trên nội dung tìm được
4. TRÍCH DẪN thông tin cụ thể (số liệu, tên, trạng thái) từ dữ liệu thực tế
5. Nếu KHÔNG TÌM THẤY thông tin phù hợp, hãy thừa nhận và đề xuất liên hệ nhân viên

LƯU Ý:
- Trả lời bằng tiếng Việt, ngắn gọn nhưng đầy đủ
- Ưu tiên dữ liệu thực tế từ hệ thống (đơn hàng, khách hàng, nhân viên, công việc)
- Nếu có nhiều thông tin liên quan, hãy tổng hợp lại
- Không bịa đặt thông tin không có trong dữ liệu

Câu hỏi của khách hàng: {user_message}
"""
        return prompt
    
    def _call_gemini_api(self, prompt, config):
        """
        Call Gemini API to generate response
        """
        api_key = config.gemini_api_key
        model = config.gemini_model

        _logger.info(f"Calling Gemini API: model={model}, key={api_key[:10]}...")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
            }
        }

        headers = {'Content-Type': 'application/json'}

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        _logger.info(f"Gemini API response status: {response.status_code}")

        if response.status_code != 200:
            _logger.error(f"Gemini API error body: {response.text}")

        response.raise_for_status()

        result = response.json()

        if 'candidates' in result and len(result['candidates']) > 0:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                text = candidate['content']['parts'][0]['text']
                _logger.info(f"Gemini response OK: {text[:100]}...")
                return text

        raise Exception(f"Invalid response from Gemini API: {json.dumps(result)[:200]}")
