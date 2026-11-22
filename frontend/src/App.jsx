import React, { useEffect, useRef, useState } from 'react';
import {
  Archive, BookOpen, Check, ChevronDown, ChevronLeft, ChevronRight,
  FileText, FolderOpen, LoaderCircle, MessageSquare, Pencil, Plus, Send,
  Settings2, ShieldCheck, Sparkles, Trash2, Upload, ZoomIn, ZoomOut,
} from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { api, pdfUrl } from './api';

// Library sidebar: document selection controls the retrieval scope for a chat.
function Sidebar({ docs, chats, active, selected, onNew, onSelect, onUpload, onDeleteDoc, onDeleteChat, onRenameChat, onOpenDoc, onToggle }) {
  const fileInput = useRef(null);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brandmark"><Archive size={18} /></div>
        <div><b>PDF Reader</b><span>DOCUMENT RESEARCH</span></div>
      </div>

      <button className="new-chat" onClick={onNew}><Plus size={16} /> New research note</button>

      <section className="side-section library-section">
        <div className="section-heading"><span>Library</span><button className="icon-button" onClick={() => fileInput.current?.click()} title="Add a PDF"><Plus size={15} /></button></div>
        <input ref={fileInput} type="file" accept="application/pdf,.pdf" hidden onChange={event => {
          const file = event.target.files?.[0];
          if (file) onUpload(file);
          event.target.value = '';
        }} />
        <div className="document-list">
          {docs.length === 0 && <p className="side-empty">Your PDFs will appear here.</p>}
          {docs.map(doc => (
            <div className={`document-row ${selected.includes(doc.id) ? 'is-selected' : ''}`} key={doc.id}>
              <label className="document-check" title="Include this PDF in research">
                <input type="checkbox" checked={selected.includes(doc.id)} disabled={doc.status !== 'ready'} onChange={() => onToggle(doc.id)} />
                <span><Check size={12} /></span>
              </label>
              <button className="document-open" onClick={() => onOpenDoc(doc.id)} title={doc.filename}>
                <FileText size={15} />
                <span>{doc.filename}</span>
              </button>
              <span className={`document-status ${doc.status}`} title={doc.status}>
                {doc.status === 'processing' ? <LoaderCircle size={12} className="spin" /> : doc.status === 'ready' ? 'Ready' : 'Error'}
              </span>
              <button className="icon-button delete-button" onClick={() => onDeleteDoc(doc.id)} title="Remove PDF"><Trash2 size={13} /></button>
            </div>
          ))}
        </div>
        <button className="upload-button" onClick={() => fileInput.current?.click()}><Upload size={15} /><span>Add a PDF</span><small>PDF, up to 50 MB</small></button>
      </section>

      <section className="side-section recents-section">
        <div className="section-heading"><span>Recent research</span><MessageSquare size={14} /></div>
        <div className="recent-list">
          {chats.map(chat => (
            <div className={`recent-row ${active === chat.id ? 'is-active' : ''}`} key={chat.id}>
              <button onClick={() => onSelect(chat.id)} title={chat.title}><span>{chat.title}</span></button>
              <button className="icon-button" onClick={() => onRenameChat(chat)} title="Rename research note"><Pencil size={12} /></button>
              <button className="icon-button" onClick={() => onDeleteChat(chat.id)} title="Delete research note"><Trash2 size={13} /></button>
            </div>
          ))}
          {!chats.length && <p className="side-empty">No saved research yet.</p>}
        </div>
      </section>

      <div className="sidebar-footer">
        <div className="privacy-mark"><ShieldCheck size={16} /><div><b>Private workspace</b><span>Files stay on this device</span></div><i /></div>
        <button className="settings-button"><Settings2 size={15} /><span>Local model settings</span><ChevronDown size={14} /></button>
      </div>
    </aside>
  );
}

// PDF reader: the iframe is keyed by document/page/zoom so citations navigate reliably.
function Reader({ doc, page, setPage, zoom, setZoom }) {
  if (!doc) {
    return <section className="reader-panel reader-empty">
      <div className="empty-mark"><BookOpen size={24} /></div>
      <span className="overline">DOCUMENT READER</span>
      <h2>Choose a document</h2>
      <p>Select a PDF from the library to read it here. Source references will open the cited page.</p>
    </section>;
  }

  return (
    <section className="reader-panel">
      <header className="reader-header">
        <div className="reader-heading">
          <span className="panel-index">01</span>
          <div><span className="overline">DOCUMENT READER</span><b title={doc.filename}>{doc.filename}</b></div>
        </div>
        <div className="reader-controls">
          <button className="icon-button" onClick={() => setPage(Math.max(1, page - 1))} aria-label="Previous page"><ChevronLeft size={16} /></button>
          <label className="page-control"><input aria-label="Current page" type="number" min="1" max={doc.page_count || 9999} value={page} onChange={event => setPage(Math.max(1, Number(event.target.value) || 1))} /><span>/ {doc.page_count || '—'}</span></label>
          <button className="icon-button" onClick={() => setPage(Math.min(doc.page_count || page + 1, page + 1))} aria-label="Next page"><ChevronRight size={16} /></button>
          <span className="control-divider" />
          <button className="icon-button" onClick={() => setZoom(Math.max(50, zoom - 10))} aria-label="Zoom out"><ZoomOut size={15} /></button>
          <span className="zoom-value">{zoom}%</span>
          <button className="icon-button" onClick={() => setZoom(Math.min(160, zoom + 10))} aria-label="Zoom in"><ZoomIn size={15} /></button>
        </div>
      </header>
      <iframe key={`${doc.id}-${page}-${zoom}`} title={`PDF reader: ${doc.filename}`} src={`${pdfUrl(doc.id)}#page=${page}&zoom=${zoom}`} />
    </section>
  );
}

// Conversation transcript: answers show their supporting PDF passages as clickable citations.
function ResearchPanel({ conversation, docCount, loading, error, onSend, onCitation, onClear }) {
  const [value, setValue] = useState('');
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [conversation?.messages, loading]);

  const submit = event => {
    event?.preventDefault();
    const question = value.trim();
    if (question && !loading) {
      setValue('');
      onSend(question);
    }
  };

  return (
    <section className="research-panel">
      <header className="research-header">
        <div className="research-title">
          <span className="panel-index">02</span>
          <div><span className="overline">RESEARCH NOTES</span><b>{conversation?.title || 'New inquiry'}</b></div>
        </div>
        <div className="research-tools">
          <span className="scope-count"><i />{docCount} {docCount === 1 ? 'PDF' : 'PDFs'} in scope</span>
          {conversation && <button className="icon-button" onClick={onClear} title="Clear this research note"><Trash2 size={15} /></button>}
        </div>
      </header>

      <div className="transcript">
        {!conversation?.messages?.length ? (
          <div className="intro-card">
            <div className="intro-rule"><span>FIELD NOTE</span><span>LOCAL / PRIVATE</span></div>
            <div className="intro-symbol"><BookOpen size={21} /><Sparkles size={12} /></div>
            <h1>Research from<br />the source.</h1>
            <p>Ask a question about the selected PDFs. Answers are limited to retrieved document evidence and cite the page they come from.</p>
            <div className="prompt-examples">
              <button onClick={() => onSend('Summarize the selected PDF.')}>Summarize the selected PDF <ChevronRight size={14} /></button>
              <button onClick={() => onSend('What are the main points?')}>Identify the main points <ChevronRight size={14} /></button>
            </div>
          </div>
        ) : conversation.messages.map((message, index) => (
          <article className={`transcript-entry ${message.role}`} key={message.id || index}>
            <div className="entry-meta"><span>{message.role === 'assistant' ? 'PDF READER / EVIDENCE ASSISTANT' : 'YOUR QUESTION'}</span><time>{message.created_at ? new Date(`${message.created_at}Z`).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</time></div>
            <div className="entry-content markdown" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(message.content || '')) }} />
            {message.role === 'assistant' && message.sources?.length > 0 && (
              <div className="citation-section">
                <span className="citation-heading">SUPPORTING PASSAGES <b>{message.sources.length}</b></span>
                <div className="citation-list">
                  {message.sources.map((source, sourceIndex) => (
                    <button className="citation-card" key={source.chunk_id || sourceIndex} onClick={() => onCitation(source)} title={`${source.filename}, page ${source.page_number}`}>
                      <FileText size={14} /><span>{source.filename}</span><b>p. {source.page_number}</b><ChevronRight size={13} />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </article>
        ))}
        {loading && <div className="loading-note"><span className="loading-mark"><LoaderCircle size={15} className="spin" /></span><span>Searching selected PDFs and checking source passages…</span></div>}
        {error && <div className="inline-error"><b>Request could not be completed</b><span>{error}</span></div>}
        <div ref={endRef} />
      </div>

      <form className="question-form" onSubmit={submit}>
        <label htmlFor="research-question">QUESTION</label>
        <textarea id="research-question" value={value} onChange={event => setValue(event.target.value)} onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); }
        }} placeholder={docCount ? 'Ask about the selected documents…' : 'Select a PDF before asking a question…'} rows="2" />
        <div className="question-footer"><span>Answers require supporting PDF evidence.</span><button type="submit" disabled={!value.trim() || loading || !docCount} aria-label="Send question"><span>Submit inquiry</span><Send size={15} /></button></div>
      </form>
      <div className="evidence-policy"><ShieldCheck size={13} /> Evidence-bound responses <span>·</span> Unsupported questions receive an explicit abstention</div>
    </section>
  );
}

// App state connects the library, active document, selected retrieval scope, and conversation APIs.
export default function App() {
  const [docs, setDocs] = useState([]);
  const [chats, setChats] = useState([]);
  const [active, setActive] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [selected, setSelected] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);

  // Refresh document and conversation indexes, and discard selections for unavailable PDFs.
  const refresh = async () => {
    try {
      const [documentRows, conversationRows] = await Promise.all([api.documents(), api.conversations()]);
      setDocs(documentRows);
      setChats(conversationRows);
      setSelected(current => current.filter(id => documentRows.some(doc => doc.id === id && doc.status === 'ready')));
    } catch (requestError) {
      setError(`Backend unavailable: ${requestError.message}`);
    }
  };

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, []);

  // Restore the selected PDF scope and first reader page when opening a saved conversation.
  useEffect(() => {
    if (!active) { setConversation(null); return; }
    api.conversation(active).then(saved => {
      setConversation(saved);
      setSelected(saved.document_ids || []);
      setActiveDoc(saved.document_ids?.[0] || null);
      setPage(1);
    }).catch(requestError => setError(requestError.message));
  }, [active]);

  // If the open PDF is deselected or removed, move the reader to the next ready selection.
  useEffect(() => {
    const currentIsSelected = docs.some(doc => doc.id === activeDoc && selected.includes(doc.id) && doc.status === 'ready');
    if (!currentIsSelected) {
      const next = docs.find(doc => selected.includes(doc.id) && doc.status === 'ready');
      setActiveDoc(next?.id || null);
      setPage(1);
    }
  }, [docs, selected, activeDoc]);

  const createConversation = async () => {
    try {
      const created = await api.createConversation({ document_ids: selected });
      setChats(current => [created, ...current]);
      setActive(created.id);
      setError('');
      return created.id;
    } catch (requestError) {
      setError(requestError.message);
      return null;
    }
  };

  // Selection controls both the reader's active PDF and the backend's retrieval scope.
  const toggleDocument = id => {
    const next = selected.includes(id) ? selected.filter(item => item !== id) : [...selected, id];
    setSelected(next);
    if (next.includes(id)) { setActiveDoc(id); setPage(1); }
    else if (activeDoc === id) {
      const fallback = docs.find(doc => next.includes(doc.id) && doc.status === 'ready');
      setActiveDoc(fallback?.id || null);
      setPage(1);
    }
    if (active) api.patchConversation(active, { document_ids: next }).catch(requestError => setError(requestError.message));
  };

  const openDocument = id => {
    setActiveDoc(id);
    setPage(1);
    if (!selected.includes(id)) toggleDocument(id);
  };

  // Uploads are indexed asynchronously by the backend; the sidebar polls status until ready.
  const upload = async file => {
    if (!file.name.toLowerCase().endsWith('.pdf')) { setError('Choose a PDF file to add it to the library.'); return; }
    setError('');
    setProgress(1);
    try { await api.upload(file, setProgress); await refresh(); }
    catch (requestError) { setError(requestError.message); }
    finally { setTimeout(() => setProgress(0), 900); }
  };

  // Send a question, then refresh the transcript so stored citations appear with the answer.
  const send = async question => {
    let conversationId = active;
    if (!conversationId) conversationId = await createConversation();
    if (!conversationId) return;
    setLoading(true);
    setError('');
    try {
      await api.send(conversationId, question);
      const updated = await api.conversation(conversationId);
      setConversation(updated);
      setChats(current => current.map(chat => chat.id === conversationId ? { ...chat, title: updated.title } : chat));
      setActive(conversationId);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  };

  const clearConversation = async () => {
    if (!active || !window.confirm('Clear the messages and memory in this research note?')) return;
    try {
      const cleared = await api.clearConversation(active);
      setConversation(cleared);
      setChats(current => current.map(chat => chat.id === active ? { ...chat, title: cleared.title } : chat));
    } catch (requestError) { setError(requestError.message); }
  };

  const deleteDocument = async id => {
    try {
      await api.deleteDocument(id);
      setDocs(current => current.filter(doc => doc.id !== id));
      setSelected(current => current.filter(item => item !== id));
    } catch (requestError) { setError(requestError.message); }
  };

  const deleteConversation = async id => {
    try {
      await api.deleteConversation(id);
      setChats(current => current.filter(chat => chat.id !== id));
      if (active === id) { setActive(null); setConversation(null); }
    } catch (requestError) { setError(requestError.message); }
  };

  const renameConversation = async chat => {
    const title = window.prompt('Rename research note', chat.title);
    if (!title?.trim()) return;
    try {
      const updated = await api.patchConversation(chat.id, { title: title.trim() });
      setChats(current => current.map(item => item.id === chat.id ? { ...item, title: updated.title } : item));
      if (active === chat.id) setConversation(current => current ? { ...current, title: updated.title } : current);
    } catch (requestError) { setError(requestError.message); }
  };

  // A source citation navigates the reader to the exact PDF and page used by retrieval.
  const openCitation = source => {
    setActiveDoc(source.document_id);
    setPage(source.page_number);
    setZoom(100);
  };

  const activeDocument = docs.find(doc => doc.id === activeDoc && doc.status === 'ready');

  return (
    <main className={`app-shell ${dragging ? 'is-dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true); }} onDragLeave={event => { if (event.target === event.currentTarget) setDragging(false); }} onDrop={event => {
      event.preventDefault(); setDragging(false);
      const file = event.dataTransfer.files?.[0];
      if (file) upload(file);
    }}>
      <Sidebar docs={docs} chats={chats} active={active} selected={selected} onNew={createConversation} onSelect={setActive} onUpload={upload} onDeleteDoc={deleteDocument} onDeleteChat={deleteConversation} onRenameChat={renameConversation} onOpenDoc={openDocument} onToggle={toggleDocument} />
      <div className="workspace">
        <header className="workspace-bar">
          <div><span className="workspace-kicker">PDF READER / PRIVATE RESEARCH</span><span className="workspace-divider">/</span><b>Document workspace</b></div>
          <div className="local-state"><i />LOCAL MODE <span>·</span> LM STUDIO</div>
        </header>
        <div className="work-area">
          <Reader doc={activeDocument} page={page} setPage={setPage} zoom={zoom} setZoom={setZoom} />
          <ResearchPanel conversation={conversation} docCount={selected.length} loading={loading} error={error} onSend={send} onCitation={openCitation} onClear={clearConversation} />
        </div>
      </div>
      {dragging && <div className="drop-overlay"><div><Upload size={27} /><b>Drop a PDF to add it</b><span>Text is indexed locally on this device</span></div></div>}
      {progress > 0 && <div className="upload-progress"><div style={{ width: `${progress}%` }} /></div>}
    </main>
  );
}
