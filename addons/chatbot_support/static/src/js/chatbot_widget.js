/** @odoo-module **/
import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ChatbotWidget extends Component {
    static template = "chatbot_support.ChatbotWidget";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            isOpen: false,
            messages: [
                {
                    id: 1,
                    type: "bot",
                    text: "Xin chào! Tôi là trợ lý AI. Hỏi tôi về đơn hàng, khách hàng, sản phẩm, công việc hoặc nhân viên.",
                },
            ],
            inputText: "",
            isLoading: false,
            sessionId: "odoo_" + Date.now(),
        });
        this.messagesEndRef = useRef("messagesEnd");
    }

    toggleChat() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            this._scrollToBottom();
        }
    }

    closeChat() {
        this.state.isOpen = false;
    }

    _scrollToBottom() {
        setTimeout(() => {
            const el = this.messagesEndRef.el;
            if (el) el.scrollIntoView({ behavior: "smooth" });
        }, 50);
    }

    onInput(ev) {
        this.state.inputText = ev.target.value;
    }

    onInputKeypress(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    sendSuggestion(text) {
        this.state.inputText = text;
        this.sendMessage();
    }

    async sendMessage() {
        const text = this.state.inputText.trim();
        if (!text || this.state.isLoading) return;

        this.state.inputText = "";
        this.state.messages.push({ id: Date.now(), type: "user", text });
        this.state.isLoading = true;
        this._scrollToBottom();

        try {
            const result = await this.rpc("/chatbot/api/chat", {
                message: text,
                session_id: this.state.sessionId,
            });

            if (result && result.success) {
                this.state.messages.push({ id: Date.now(), type: "bot", text: result.response });
            } else {
                this.state.messages.push({
                    id: Date.now(),
                    type: "bot",
                    text: "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.",
                });
            }
        } catch (err) {
            this.state.messages.push({
                id: Date.now(),
                type: "bot",
                text: "Không thể kết nối. Vui lòng thử lại sau.",
            });
        } finally {
            this.state.isLoading = false;
            this._scrollToBottom();
        }
    }
}

registry.category("main_components").add("ChatbotWidget", {
    Component: ChatbotWidget,
    props: {},
});
