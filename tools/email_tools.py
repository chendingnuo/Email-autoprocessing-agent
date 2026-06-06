"""
邮件处理工具
============
封装对学生组织公邮的读取和回复操作。
支持附件下载与保存。
"""

from __future__ import annotations

import email
import imaplib
import json
import logging
import os
import smtplib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header, decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional
from email import message_from_bytes

logger = logging.getLogger(__name__)


# 邮件任务类型定义和关键词
TASK_TYPE_KEYWORDS = {
    "volunteer_hours": ["荣誉时数", "志愿者时长", "时长导入", "小时", "志愿者"],
    "volunteer_project": ["立项", "项目申请", "活动申请", "场地申请", "申请"],
}


@dataclass
class EmailMessage:
    """一封邮件的结构化表示"""
    id: str
    subject: str
    sender: str
    recipient: str
    date: str
    body_text: str
    body_html: str = ""
    attachments: list[dict] = field(default_factory=list)
    raw_size: int = 0


class EmailTools:
    """
    邮件工具集。
    提供 IMAP 读取和 SMTP 回复功能。
    支持按任务类型过滤邮件和防重复处理。
    注意：实际使用时需要配置邮件服务器地址和凭证。
    """

    # 处理历史文件路径
    PROCESSED_EMAILS_FILE = "data/processed_emails.json"

    def __init__(
        self,
        imap_server: str = "",
        imap_port: int = 993,
        smtp_server: str = "",
        smtp_port: int = 587,
        email_account: str = "",
        email_password: str = "",
        attachment_dir: str = "",
    ):
        self.imap_server = imap_server or os.getenv("IMAP_SERVER", "")
        self.imap_port = int(os.getenv("IMAP_PORT", str(imap_port)))
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", str(smtp_port)))
        self.email_account = email_account or os.getenv("EMAIL_ACCOUNT", "")
        self.email_password = email_password or os.getenv("EMAIL_PASSWORD", "")
        self.attachment_dir = attachment_dir or os.getenv(
            "ATTACHMENT_DIR",
            os.path.join(os.getcwd(), "data", "attachments"),
        )
        os.makedirs(self.attachment_dir, exist_ok=True)

        # 初始化处理历史
        self.processed_emails = self._load_processed_emails()

        if not all([self.imap_server, self.smtp_server, self.email_account, self.email_password]):
            logger.warning(
                "邮件服务器配置不完整。请设置以下环境变量：\n"
                "  IMAP_SERVER, SMTP_SERVER, EMAIL_ACCOUNT, EMAIL_PASSWORD\n"
                "或在初始化 EmailTools 时传入对应参数。"
            )

    def _load_processed_emails(self) -> dict:
        """加载已处理邮件的历史记录"""
        file_path = Path(self.PROCESSED_EMAILS_FILE)
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("processed_emails", {})
            except Exception as e:
                logger.warning(f"读取处理历史失败: {e}")
                return {}
        return {}

    def _save_processed_emails(self) -> None:
        """保存已处理邮件的历史记录"""
        file_path = Path(self.PROCESSED_EMAILS_FILE)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({"processed_emails": self.processed_emails}, f,
                         ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存处理历史失败: {e}")

    def mark_email_processed(self, email_id: str, subject: str,
                           task_type: str, status: str = "success") -> None:
        """标记邮件为已处理"""
        self.processed_emails[email_id] = {
            "subject": subject,
            "task_type": task_type,
            "processed_at": datetime.now().isoformat(),
            "status": status
        }
        self._save_processed_emails()
        logger.info(f"邮件已标记为已处理: {email_id} ({task_type})")

    def is_email_processed(self, email_id: str) -> bool:
        """检查邮件是否已处理"""
        return email_id in self.processed_emails

    def get_processed_count(self, task_type: str = "") -> int:
        """获取已处理邮件数"""
        if not task_type:
            return len(self.processed_emails)
        return sum(1 for record in self.processed_emails.values()
                  if record.get("task_type") == task_type)

    def _detect_task_type(self, subject: str, body_preview: str = "") -> str:
        """根据邮件内容检测任务类型"""
        text = (subject + " " + body_preview).lower()
        
        for task_type, keywords in TASK_TYPE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return task_type
        
        return "unknown"

    def read_unread(self, limit: int = 10, batch_mode: bool = False, task_type: str = "") -> str:
        """
        读取收件箱中未处理的邮件，并保存附件到本地。
        读取后自动将邮件标记为已读，避免重复处理。
        
        支持按任务类型过滤，自动跳过已处理的邮件。

        Args:
            limit: 最大读取封数
            batch_mode: 是否启用批处理模式（返回分类统计）
            task_type: 任务类型过滤 ("volunteer_hours" / "volunteer_project" / "")
                      空字符串表示不过滤，返回所有类型

        Returns:
            str: 邮件列表的JSON字符串，含附件信息和任务类型
        """
        if not self.imap_server:
            return json.dumps({
                "status": "error",
                "message": "IMAP服务器未配置，无法读取邮件",
                "emails": []
            }, ensure_ascii=False)

        try:
            # 连接IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_account, self.email_password)
            mail.select("INBOX")

            # 搜索未读邮件
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                return json.dumps({
                    "status": "error",
                    "message": "搜索邮件失败",
                    "emails": []
                }, ensure_ascii=False)

            email_ids = messages[0].split()
            if not email_ids:
                # 没有未读邮件时，改为读取最近几封邮件（供测试用）
                status, all_msgs = mail.search(None, "ALL")
                if status == "OK":
                    all_ids = all_msgs[0].split()
                    email_ids = all_ids[-limit:] if all_ids else []
                    source = "recent"
                else:
                    mail.logout()
                    return json.dumps({
                        "status": "success",
                        "total": 0,
                        "emails": [],
                        "message": "收件箱中没有邮件"
                    }, ensure_ascii=False)
            else:
                source = "unread"

            emails = []
            categories = {}
            unread_ids_to_mark = []

            # 逆序处理，从最新开始
            for eid in reversed(email_ids):
                if len(emails) >= limit:
                    break

                # eid 是 bytes 类型（如 b'95'），统一转为字符串
                eid_str = eid.decode() if isinstance(eid, bytes) else str(eid)

                # 检查：是否已处理
                if self.is_email_processed(eid_str):
                    logger.debug(f"跳过已处理邮件: {eid_str}")
                    continue

                status, data = mail.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = data[0][1]
                msg = message_from_bytes(raw_email)

                # 解码主题
                subject = ""
                raw_subject = msg.get("Subject", "")
                if raw_subject:
                    decoded_parts = decode_header(raw_subject)
                    subject = "".join(
                        part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                        for part, charset in decoded_parts
                    )

                # 提取正文
                body_text = self._get_email_body(msg)
                body_preview = body_text[:500]

                # 检测任务类型
                detected_task_type = self._detect_task_type(subject, body_preview)

                # 检查：是否匹配指定的任务类型
                if task_type and detected_task_type != task_type:
                    logger.debug(
                        f"跳过不匹配的邮件类型: {eid_str} "
                        f"(期望: {task_type}, 实际: {detected_task_type})"
                    )
                    continue

                # 提取附件（传入字符串形式的ID，避免 b'95' 出现在文件名中）
                attachments = self._extract_attachments(msg, eid_str)

                email_msg = EmailMessage(
                    id=eid_str,
                    subject=subject or "(无主题)",
                    sender=msg.get("From", ""),
                    recipient=msg.get("To", ""),
                    date=str(parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else ""),
                    body_text=body_text,
                    raw_size=len(raw_email),
                )
                
                email_data = {
                    "id": email_msg.id,
                    "subject": email_msg.subject,
                    "from": email_msg.sender,
                    "date": email_msg.date,
                    "body_preview": email_msg.body_text[:500],
                    "body_length": len(email_msg.body_text),
                    "attachments": attachments,
                    "has_attachments": len(attachments) > 0,
                    "task_type": detected_task_type,  # 新增：任务类型
                }
                
                emails.append(email_data)
                categories[detected_task_type] = categories.get(detected_task_type, 0) + 1
                
                # 记录需要标记为已读的邮件
                if source == "unread":
                    unread_ids_to_mark.append(eid)

            # 将本次读取的未读邮件标记为已读，避免重复处理
            if source == "unread" and unread_ids_to_mark:
                for eid in unread_ids_to_mark:
                    try:
                        mail.store(eid, '+FLAGS', '\\Seen')
                    except Exception as e:
                        logger.warning(f"标记邮件已读失败 ({eid}): {e}")
                logger.info(f"已将 {len(unread_ids_to_mark)} 封邮件标记为已读")

            mail.logout()

            label = "最近" if source == "recent" else "未读"
            result = {
                "status": "success",
                "total": len(emails),
                "emails": emails,
                "source": source,
                "message": f"成功读取 {len(emails)} 封{label}邮件",
                "task_type": task_type,  # 返回过滤的任务类型
                "processed_count": self.get_processed_count(task_type),  # 已处理数量
            }
            
            # 批处理模式返回汇总
            if batch_mode and categories:
                summary = f"共{len(emails)}封："
                summary += "、".join(
                    f"{cat}({cnt})"
                    for cat, cnt in sorted(categories.items(),
                                         key=lambda x: -x[1])
                )
                result["summary"] = summary
                result["categories"] = categories
            
            return json.dumps(result, ensure_ascii=False)

        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP连接失败: {e}"
            logger.error(error_msg)
            return json.dumps({
                "status": "error",
                "message": error_msg,
                "emails": []
            }, ensure_ascii=False)

    @staticmethod
    def _detect_draft_folder(imap_server: str) -> str:
        """根据 IMAP 服务器判断草稿箱文件夹名称"""
        gmail_domains = ("gmail.com", "googlemail.com")
        if any(d in imap_server.lower() for d in gmail_domains):
            return "[Gmail]/Drafts"
        return "Drafts"

    def reply_draft(self, mail_id: str, subject: str, content: str) -> str:
        """
        将回复邮件保存到草稿箱，供人工审核后发送。
        自动根据邮箱服务商选择正确的草稿箱文件夹：
          - Gmail → [Gmail]/Drafts
          - 其他（QQ/126/163/ZJU等）→ Drafts

        Args:
            mail_id: 原邮件ID
            subject: 回复主题
            content: 回复正文

        Returns:
            str: 操作结果
        """
        if not self.imap_server:
            return json.dumps({
                "status": "error",
                "message": "IMAP服务器未配置，无法保存草稿"
            }, ensure_ascii=False)

        reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
        mime_msg = MIMEText(content, "plain", "utf-8")
        # 正确编码含中文的邮件头（RFC 2047），避免 ascii 编码错误
        mime_msg["Subject"] = Header(reply_subject, "utf-8")
        mime_msg["From"] = self.email_account
        mime_msg["In-Reply-To"] = mail_id

        draft_folder = self._detect_draft_folder(self.imap_server)
        fallback_folder = "Drafts" if draft_folder != "Drafts" else None

        try:
            conn = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            conn.login(self.email_account, self.email_password)

            # 1. 获取原邮件发件人地址
            conn.select("INBOX")
            original_sender = ""
            status, data = conn.fetch(mail_id.encode(), "(RFC822)")
            if status == "OK":
                msg = message_from_bytes(data[0][1])
                original_sender = msg.get("Reply-To", "") or msg.get("From", "")
            mime_msg["To"] = original_sender

            # 2. 依次尝试草稿箱文件夹
            folders_to_try = [draft_folder]
            if fallback_folder:
                folders_to_try.append(fallback_folder)

            for folder in folders_to_try:
                try:
                    conn.select(folder)
                    append_status = conn.append(
                        folder, "\\Draft", None, mime_msg.as_bytes()
                    )
                    if append_status[0] == "OK":
                        conn.logout()
                        return json.dumps({
                            "status": "success",
                            "mail_id": mail_id,
                            "subject": reply_subject,
                            "to": original_sender,
                            "draft_status": "saved_to_drafts",
                            "message": f"回复草稿已保存到 {folder}，请登录邮箱审核后发送",
                        }, ensure_ascii=False)
                except Exception:
                    continue

            conn.logout()
            return json.dumps({
                "status": "error",
                "message": "所有草稿箱文件夹均无法写入",
            }, ensure_ascii=False)

        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP连接失败: {e}"
            logger.error(error_msg)
            return json.dumps({
                "status": "error",
                "message": error_msg,
            }, ensure_ascii=False)
        except Exception as e:
            error_msg = f"生成回复草稿失败: {e}"
            logger.error(error_msg)
            return json.dumps({
                "status": "error",
                "message": error_msg,
            }, ensure_ascii=False)

    def send_confirmed(
        self, to_addr: str, subject: str, content: str,
        cc_addr: str = "", reply_to_mail_id: str = ""
    ) -> str:
        """
        实际发送已确认的回复邮件（需人工确认后调用）。

        Args:
            to_addr: 收件人地址
            subject: 邮件主题
            content: 邮件正文
            cc_addr: 抄送地址（可选）
            reply_to_mail_id: 原邮件ID（可选，仅用于记录）

        Returns:
            str: 发送结果
        """
        if not all([self.smtp_server, self.email_account, self.email_password]):
            return json.dumps({
                "status": "error",
                "message": "SMTP配置不完整，无法发送邮件"
            }, ensure_ascii=False)

        try:
            msg = MIMEText(content, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = self.email_account
            msg["To"] = to_addr
            if cc_addr:
                msg["Cc"] = cc_addr

            # SMTP连接：根据端口选择 SSL 或 STARTTLS
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(
                    self.smtp_server, self.smtp_port, timeout=30
                )
            else:
                server = smtplib.SMTP(
                    self.smtp_server, self.smtp_port, timeout=30
                )
                server.starttls()

            server.login(self.email_account, self.email_password)
            server.send_message(msg)
            server.quit()

            return json.dumps({
                "status": "success",
                "message": f"邮件已发送至 {to_addr}",
                "subject": subject,
            }, ensure_ascii=False)

        except smtplib.SMTPAuthenticationError:
            return json.dumps({
                "status": "error",
                "message": "SMTP登录失败，请检查邮箱地址和密码（如开启双重验证，需使用应用专用密码）"
            }, ensure_ascii=False)
        except smtplib.SMTPException as e:
            return json.dumps({
                "status": "error",
                "message": f"SMTP发送失败: {e}"
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"发送邮件异常: {e}"
            }, ensure_ascii=False)

    @staticmethod
    def _get_email_body(msg) -> str:
        """从邮件对象中提取纯文本正文"""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                    except Exception:
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                elif content_type == "text/html" and not body:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors="replace")
                    except Exception:
                        body = ""
        else:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body = msg.get_payload(decode=True).decode(charset, errors="replace")
            except Exception:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        return body.strip()

    def _extract_attachments(self, msg, email_id) -> list[dict]:
        """
        提取邮件附件并保存到本地。

        Args:
            msg: email.message.Message 对象
            email_id: 邮件ID字符串（用于命名，已确保不是 bytes 类型）

        Returns:
            list[dict]: 附件信息列表，包含 name, saved_path, size_kb, content_type
        """
        attachments = []
        if not msg.is_multipart():
            return attachments

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = str(email_id).replace("/", "_").replace("\\", "_")

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            # 解码附件文件名
            try:
                decoded_filename = decode_header(filename)
                filename = "".join(
                    part.decode(charset or "utf-8") if isinstance(part, bytes) else part
                    for part, charset in decoded_filename
                )
            except Exception:
                pass

            # 生成唯一文件名避免冲突
            ext = os.path.splitext(filename)[1] or ""
            safe_filename = f"{safe_id}_{uuid.uuid4().hex[:8]}{ext}"
            filepath = os.path.join(self.attachment_dir, safe_filename)

            try:
                payload = part.get_payload(decode=True)
                if payload:
                    with open(filepath, "wb") as f:
                        f.write(payload)
                    attachments.append({
                        "filename": filename,
                        "saved_path": filepath,
                        "size_kb": round(len(payload) / 1024, 1),
                        "content_type": part.get_content_type(),
                    })
                    logger.info(f"附件已保存: {filename} -> {filepath}")
            except Exception as e:
                logger.warning(f"保存附件 {filename} 失败: {e}")

        return attachments
