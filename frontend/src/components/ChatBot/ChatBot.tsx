import React, { useState, useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { MessageCircle, X, Send, Bot, Loader2, FileText, Download } from 'lucide-react';
import { api, ChatMessage } from '../../utils/api';
import { useApp } from '../../store/AppContext';
import { AppState, ToolResult } from '../../types';

const WELCOME: ChatMessage = {
  role: 'assistant',
  content: "Hi, I'm the TRINETRA Assistant. Ask me how to run a scan, set up a watch, read your results — or generate a full investigation report from your current scan.",
};

/** Build a compact text summary of the current scan for the AI to reason over */
function buildContext(state: AppState): string {
  if (!state?.results || state.results.length === 0) return '';
  const target = state.searchQuery || 'unknown target';
  const lines = state.results.slice(0, 25).map((r: ToolResult) => {
    let gui = '';
    try {
      gui = r.guiData ? JSON.stringify(r.guiData).slice(0, 3000) : '';   // was 350
    } catch {
      gui = '';
    }
    return `- [${r.category}] ${r.pluginName} — status: ${r.status}, freshness: ${r.freshness}${gui ? ` — data: ${gui}` : ''}`;
  });
  return `Target: ${target}\nTotal findings: ${state.results.length}\n\nScan results:\n${lines.join('\n')}`.slice(0, 24000); // was 8000
}

/** Minimal markdown-ish renderer: **bold**, "- " bullets, and paragraphs. No new deps. */
function renderContent(content: string) {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let listBuffer: string[] = [];

  const flushList = (key: string) => {
    if (listBuffer.length > 0) {
      elements.push(
        <ul className="chatbot-list" key={key}>
          {listBuffer.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      listBuffer = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      listBuffer.push(trimmed.slice(2));
      return;
    }
    flushList(`list-${idx}`);
    if (trimmed.startsWith('### ')) {
      elements.push(<div className="chatbot-h3" key={idx}>{renderInline(trimmed.slice(4))}</div>);
    } else if (trimmed.startsWith('## ')) {
      elements.push(<div className="chatbot-h2" key={idx}>{renderInline(trimmed.slice(3))}</div>);
    } else if (trimmed) {
      elements.push(<p key={idx}>{renderInline(trimmed)}</p>);
    }
  });
  flushList('list-end');
  return elements;
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={i}>{part}</React.Fragment>;
  });
}

export default function ChatBot() {
  const { state } = useApp();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [downloadingIdx, setDownloadingIdx] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const hasResults = !!state?.results && state.results.length > 0;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;
    const next: ChatMessage[] = [...messages, { role: 'user', content: text }];
    setMessages(next);
    setInput('');
    setLoading(true);
    try {
      const context = buildContext(state);
      const res = await api.chat(text, next.slice(1), context || undefined);
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Something went wrong.';
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ ${message}` }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSend() {
    sendMessage(input);
  }

  function handleGenerateReport() {
    const target = state?.searchQuery || 'the current target';
    sendMessage(`Generate a full SOC investigation report for ${target} based on the scan results.`);
  }

  async function handleDownloadDocx(idx: number, content: string) {
    if (downloadingIdx !== null) return;
    setDownloadingIdx(idx);
    try {
      const target = state?.searchQuery || 'report';
      await api.exportReportDocx(target, content);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMessages((m) => [...m, { role: 'assistant', content: `⚠️ Could not generate the Word document: ${message}` }]);
    } finally {
      setDownloadingIdx(null);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <>
      <button
        className="chatbot-fab"
        onClick={() => setOpen((o) => !o)}
        title="TRINETRA Assistant"
      >
        <AnimatePresence mode="wait" initial={false}>
          {open ? (
            <motion.span key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <X size={22} />
            </motion.span>
          ) : (
            <motion.span key="open" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <MessageCircle size={22} />
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="chatbot-panel"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
          >
            <div className="chatbot-header">
              <div className="chatbot-header-title">
                <div className="chatbot-header-icon"><Bot size={16} /></div>
                <div>
                  <div className="chatbot-header-name">TRINETRA Assistant</div>
                  <div className="chatbot-header-sub">
                    {hasResults ? `Analyzing: ${state.searchQuery}` : 'Always online'}
                  </div>
                </div>
              </div>
              <button className="chatbot-close-btn" onClick={() => setOpen(false)}>
                <X size={16} />
              </button>
            </div>

            <div className="chatbot-messages" ref={scrollRef}>
              {messages.map((m, i) => (
                <div key={i} className={`chatbot-msg chatbot-msg-${m.role}`}>
                  {m.role === 'assistant' && (
                    <div className="chatbot-msg-avatar"><Bot size={13} /></div>
                  )}
                  <div className="chatbot-msg-col">
                    <div className="chatbot-msg-bubble">{renderContent(m.content)}</div>
                    {m.role === 'assistant' && m.content.length > 400 && (
                      <button
                        className="chatbot-docx-btn"
                        onClick={() => handleDownloadDocx(i, m.content)}
                        disabled={downloadingIdx === i}
                        title="Download this report as a Word document"
                      >
                        <Download size={12} /> {downloadingIdx === i ? 'Generating...' : 'Download as Word (.docx)'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="chatbot-msg chatbot-msg-assistant">
                  <div className="chatbot-msg-avatar"><Bot size={13} /></div>
                  <div className="chatbot-msg-bubble chatbot-msg-typing">
                    <Loader2 size={14} className="chatbot-spin" /> Thinking...
                  </div>
                </div>
              )}
            </div>

            {hasResults && (
              <div className="chatbot-quick-actions">
                <button className="chatbot-quick-btn" onClick={handleGenerateReport} disabled={loading}>
                  <FileText size={13} /> Generate Report
                </button>
              </div>
            )}

            <div className="chatbot-input-row">
              <textarea
                className="chatbot-input"
                placeholder="Ask about TRINETRA..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button className="chatbot-send-btn" onClick={handleSend} disabled={loading || !input.trim()}>
                <Send size={16} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}