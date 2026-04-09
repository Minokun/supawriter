'use client';

import { useState, useRef, useEffect, useCallback, memo } from 'react';
import { useRouter } from 'next/navigation';
import { useSharedAuth } from '@/contexts/AuthContext';
import { useModelConfig } from '@/contexts/ModelConfigContext';
import { useToast } from '@/components/ui/ToastContainer';
import MainLayout from '@/components/layout/MainLayout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import SearchResultsPanel from '@/components/ui/SearchResultsPanel';
import { CapabilityGate } from '@/components/system/CapabilityGate';
import { useCapabilityReadiness } from '@/lib/capability-readiness';
import dynamic from 'next/dynamic';
import { Send, Plus, Download, Trash2, ChevronRight, Loader2, Globe } from 'lucide-react';
import {
  sendChatMessage,
  getChatSessions,
  deleteChatSession,
  type ChatSession as APIChatSession,
  type ChatSendResponse,
  type SearchResult,
} from '@/lib/api';

// 动态导入 Markdown 渲染组件
const MarkdownContent = dynamic(() => import('@/components/ui/MarkdownContent'), {
  ssr: false,
  loading: () => <div className="h-10 w-20 bg-bg animate-pulse rounded" />
});

const NovelEditor = dynamic(() => import('@/components/ui/NovelEditor'), {
  ssr: false,
  loading: () => <div className="h-10 w-full bg-bg animate-pulse rounded" />
});

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  timestamp: Date;
  // 搜索结果（添加到消息中持久保存）
  search_data?: SearchResult[];
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

const MessageItem = memo(({ message, userImage }: { message: Message; userImage?: string | null }) => {
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);

  return (
    <div
      className={`flex gap-3 mb-6 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      {message.role === 'assistant' && (
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 shadow-sm">
          <span className="text-xl">🤖</span>
        </div>
      )}

      <div
        className={`max-w-[95%] md:max-w-[90%] shadow-sm ${message.role === 'user'
            ? 'bg-primary text-white rounded-2xl rounded-tr-sm'
            : 'bg-white border border-border text-text-primary rounded-2xl rounded-tl-sm'
        } p-4`}
      >
                {/* 搜索结果 - 显示在消息上方 */}
                {message.search_data && message.search_data.length > 0 && (
                  <div className="mb-4 pb-3 border-b border-border">
                    <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-primary mb-3">
                      <Globe size={12} />
                      <span>搜索结果 ({message.search_data.length})</span>
                    </div>
                    <div className="space-y-2">
                      {message.search_data.slice(0, 5).map((result, idx) => (
                        <a
                          key={idx}
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block p-2 bg-bg rounded-lg hover:bg-bg/80 transition-colors"
                        >
                          <div className="text-xs font-semibold text-text-primary line-clamp-1 mb-1">
                            {result.title}
                          </div>
                          <div className="text-[10px] text-text-secondary line-clamp-2">
                            {result.snippet || result.body}
                          </div>
                          <div className="text-[9px] text-text-tertiary mt-1 truncate">
                            {result.source || result.url}
                          </div>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* 思考过程 - 可折叠 */}
                {message.thinking && (
                  <div className="mb-4 pb-3 border-b border-border">
                    <button
                      onClick={() => setIsThinkingExpanded(!isThinkingExpanded)}
                      className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-primary hover:opacity-80 transition-opacity"
                    >
                      <div className={`p-1 rounded-md transition-colors ${isThinkingExpanded ? 'bg-primary/10 text-primary' : 'bg-bg text-primary'}`}>
                        <ChevronRight
                          size={12}
                          className={`transition-transform duration-300 ${isThinkingExpanded ? 'rotate-90' : ''}`}
                        />
                      </div>
                      <span>💭 Thinking Process</span>
                    </button>
                    {isThinkingExpanded && (
                      <div className="mt-3 text-sm text-text-primary leading-relaxed bg-bg p-3 rounded-xl italic border-l-2 border-primary/40">
                        {message.thinking}
                      </div>
                    )}
                  </div>
                )}

                {/* 消息内容 - 使用 NovelEditor 风格的渲染 */}
                <div className="text-[15px] leading-relaxed font-medium">
                  {message.role === 'assistant' ? (
                    <MarkdownContent content={message.content} />
                  ) : (
                    <p className="whitespace-pre-wrap font-bold">{message.content}</p>
                  )}
                </div>

                {/* 时间戳 */}
                <div className={`flex items-center gap-2 mt-3 pt-2 border-t border-current/10 ${
                    message.role === 'user' ? 'text-white/80' : 'text-text-secondary'
                  }`}>
        <span className="text-[10px] font-bold tracking-tight">
                    {new Date(message.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
      </div>

      {message.role === 'user' && (
        userImage ? (
          <img
            src={userImage}
            alt="用户头像"
            className="w-10 h-10 rounded-xl object-cover flex-shrink-0 shadow-sm"
          />
        ) : (
          <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center flex-shrink-0 shadow-sm">
            <span className="text-xl text-white">👤</span>
          </div>
        )
      )}
    </div>
  );
});
MessageItem.displayName = 'MessageItem';

const SessionItem = memo((
  { session, isActive, onSelect, onDelete }: {
    session: ChatSession;
    isActive: boolean;
    onSelect: (session: ChatSession) => void;
    onDelete: (sessionId: string) => void;
  }
) => {
  return (
    <div
      onClick={() => onSelect(session)}
      role="button"
      tabIndex={0}
      className={`group relative w-full text-left p-4 rounded-2xl transition-all duration-300 cursor-pointer mb-2 ${isActive
          ? 'bg-primary text-white shadow-lg shadow-primary/20 ring-1 ring-primary'
          : 'bg-white border border-border hover:border-primary/30 hover:shadow-md'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className={`font-body text-sm font-bold line-clamp-2 flex-1 leading-snug ${isActive ? 'text-white' : 'text-text-primary'}`}>
          {session.title}
        </p>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(session.id);
          }}
          aria-label={`删除会话 ${session.title}`}
          data-testid={`chat-session-delete-${session.id}`}
          className={`p-1.5 rounded-lg transition-all duration-200 ${isActive ? 'text-white/60 hover:bg-white/20 hover:text-white' : 'text-text-tertiary hover:bg-error/10 hover:text-error'}`}
        >
          <Trash2 size={14} />
        </button>
      </div>
      <div className={`flex items-center gap-2 mt-2 ${isActive ? 'text-white/70' : 'text-text-tertiary'}`}>
        <span className="text-[10px] font-medium uppercase tracking-tighter">
          {new Date(session.updatedAt).toLocaleDateString('zh-CN')}
        </span>
      </div>
    </div>
  );
});
SessionItem.displayName = 'SessionItem';

export default function AIAssistantPage() {
  const router = useRouter();
  const { session, status, isAuthenticated } = useSharedAuth();
  const { config: modelConfig } = useModelConfig();
  const { showError } = useToast();
  const readiness = useCapabilityReadiness('chat');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentThinking, setCurrentThinking] = useState('');
  const [currentResponse, setCurrentResponse] = useState('');
  const [isStreamingThinkingExpanded, setIsStreamingThinkingExpanded] = useState(false);
  const [enableSearch, setEnableSearch] = useState(true);
  // 将搜索结果与当前流式响应关联
  const [currentSearchResults, setCurrentSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentThinkingRef = useRef('');
  const currentResponseRef = useRef('');
  const currentSearchResultsRef = useRef<SearchResult[]>([]);
  const updateTimerRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentThinking, currentResponse, currentSearchResults, scrollToBottom]);

  const fetchSessions = useCallback(async () => {
    if (!isAuthenticated) {
      return;
    }

    try {
      const response = await getChatSessions({ page: 1, page_size: 20 });
      if (!response?.items) {
        setSessions([]);
        return;
      }
      const apiSessions: ChatSession[] = response.items.map((s: APIChatSession) => ({
        id: s.id,
        title: s.title,
        messages: s.messages
          .map((m) => ({
            id: `${s.id}-${m.timestamp}`,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            timestamp: new Date(m.timestamp || s.created_at),
          }))
          .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime()),
        createdAt: new Date(s.created_at),
        updatedAt: new Date(s.updated_at),
      }));
      setSessions(apiSessions);
    } catch (error) {
      console.error('加载会话列表失败:', error);
    }
  }, [status]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setInput('');
    setCurrentThinking('');
    setCurrentResponse('');
    setCurrentSearchResults([]);
    currentThinkingRef.current = '';
    currentResponseRef.current = '';
  };

  const handleSelectSession = (session: ChatSession) => {
    setActiveSessionId(session.id);
    setMessages(session.messages);
    setCurrentThinking('');
    setCurrentResponse('');
    setCurrentSearchResults([]);
    currentThinkingRef.current = '';
    currentResponseRef.current = '';
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading || !isAuthenticated) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const messageToSend = input.trim();
    setInput('');
    setIsLoading(true);
    setCurrentThinking('');
    setCurrentResponse('');

    const assistantMessageId = (Date.now() + 1).toString();

    try {
      await sendChatMessage(
        {
          session_id: activeSessionId || undefined,
          message: messageToSend,
          model: modelConfig.chat_model,
          enable_search: enableSearch,
        },
        (chunk: ChatSendResponse) => {
          if (chunk.type === 'user_message') {
            if (chunk.session_id && !activeSessionId) {
              setActiveSessionId(chunk.session_id);
            }
          } else if (chunk.type === 'search_start') {
            setIsSearching(true);
            setSearchQuery(messageToSend);
            setCurrentSearchResults([]);
          } else if (chunk.type === 'search_progress') {
            const progressData = chunk.results || chunk.search_data;
            if (progressData) {
              setCurrentSearchResults(progressData);
            }
          } else if (chunk.type === 'search_complete') {
            setIsSearching(false);
            const completeData = chunk.results || chunk.search_data;
            if (completeData && completeData.length > 0) {
              // 将搜索结果保存到消息中，确保 AI 回复完成后仍能查看
              setCurrentSearchResults(completeData);
              currentSearchResultsRef.current = completeData;
            }
          } else if (chunk.type === 'search_error') {
            setIsSearching(false);
            console.error('[Search] Search error:', chunk.message);
            // 清空搜索结果
            setCurrentSearchResults([]);
            currentSearchResultsRef.current = [];
          } else if (chunk.type === 'assistant_thinking') {
            // 收到思考内容，说明搜索已完成
            if (isSearching) {
              setIsSearching(false);
            }
            currentThinkingRef.current += (chunk.text || '');
            setCurrentThinking(currentThinkingRef.current);
          } else if (chunk.type === 'assistant_chunk') {
            currentResponseRef.current += (chunk.text || '');
            setCurrentResponse(currentResponseRef.current);
          } else if (chunk.type === 'assistant_end') {
            if (updateTimerRef.current) {
              clearTimeout(updateTimerRef.current);
              updateTimerRef.current = null;
            }
            const finalMessage: Message = {
              id: assistantMessageId,
              role: 'assistant',
              content: chunk.full_text || currentResponseRef.current,
              thinking: chunk.thinking || currentThinkingRef.current || undefined,
              timestamp: new Date(),
              // 保存搜索结果到消息中，确保持久化
              search_data: currentSearchResultsRef.current.length > 0 ? currentSearchResultsRef.current : undefined,
            };
            setMessages((prev) => {
              const filtered = prev.filter(m => m.id !== assistantMessageId);
              return [...filtered, finalMessage];
            });
            setCurrentThinking('');
            setCurrentResponse('');
            currentThinkingRef.current = '';
            currentResponseRef.current = '';
            currentSearchResultsRef.current = [];
            setIsLoading(false);
            // 清空临时搜索结果状态
            setCurrentSearchResults([]);
            setTimeout(() => fetchSessions(), 500);
          } else if (chunk.type === 'error') {
            console.error('[Streaming] Server error:', chunk.message);
            setIsLoading(false);
            setIsSearching(false);
            setCurrentThinking('');
            setCurrentResponse('');
            setCurrentSearchResults([]);
            currentThinkingRef.current = '';
            currentResponseRef.current = '';
            currentSearchResultsRef.current = [];
          }
        },
        () => {
          setIsLoading(false);
          setIsSearching(false);
          setCurrentThinking('');
          setCurrentResponse('');
          setCurrentSearchResults([]);
          currentThinkingRef.current = '';
          currentResponseRef.current = '';
          currentSearchResultsRef.current = [];
        },
        (error) => {
          console.error('发送消息失败:', error);
          // 提取错误信息
          const errorMessage = error instanceof Error ? error.message : String(error);
          showError(errorMessage || '发送消息失败，请稍后重试');
          setIsLoading(false);
          setIsSearching(false);
          setCurrentThinking('');
          setCurrentResponse('');
          setCurrentSearchResults([]);
          currentThinkingRef.current = '';
          currentResponseRef.current = '';
          currentSearchResultsRef.current = [];
        }
      );
    } catch (error) {
      console.error('发送消息失败:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      showError(errorMessage || '发送消息失败，请稍后重试');
      setIsLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm('确定要删除这个对话吗？')) return;

    try {
      await deleteChatSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (activeSessionId === sessionId) {
        handleNewChat();
      }
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  };

  const handleExportMarkdown = () => {
    if (messages.length === 0) return;

    let markdown = `# AI对话记录\n\n*导出时间: ${new Date().toLocaleString()}*\n\n`;
    
    messages.forEach(msg => {
      if (msg.role === 'user') {
        markdown += `## 👤 用户\n\n${msg.content}\n\n`;
      } else {
        if (msg.thinking) {
          markdown += `## 🤖 AI 助手\n\n### 💭 思考过程\n\n${msg.thinking}\n\n### 📝 回复内容\n\n${msg.content}\n\n`;
        } else {
          markdown += `## 🤖 AI 助手\n\n${msg.content}\n\n`;
        }
      }
    });

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `对话记录_${new Date().getTime()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <MainLayout>
      <div className="flex gap-6 h-[calc(100vh-140px)] animate-in fade-in duration-500">
        {/* 左侧边栏 - 会话管理 */}
        <div className="w-80 flex-shrink-0 flex flex-col h-full">
          <Card padding="md" className="flex-1 flex flex-col min-h-0 border-none shadow-standard bg-white/80 backdrop-blur-sm">
            {/* Header */}
            <div className="flex-shrink-0 mb-6 px-2">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center shadow-inner">
                  <span className="text-2xl">🤖</span>
                </div>
                <div>
                  <h1 className="font-heading text-xl font-bold text-text-primary tracking-tight">
                    AI Assistant
                  </h1>
                  <p className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest">
                    Intelligent Chat
                  </p>
                </div>
              </div>
              
              <Button
                variant="primary"
                icon={<Plus size={18} />}
                onClick={handleNewChat}
                className="w-full rounded-2xl py-6 shadow-lg shadow-primary/10"
              >
                新建对话
              </Button>
            </div>

            {/* Session List */}
            <div className="flex-1 overflow-y-auto px-2 space-y-1 custom-scrollbar">
              <div className="flex items-center justify-between mb-3 px-2">
                <span className="text-[11px] font-bold text-text-tertiary uppercase tracking-widest">Recent Chats</span>
                {messages.length > 0 && (
                  <button 
                    onClick={handleExportMarkdown}
                    className="text-[11px] font-bold text-primary hover:underline flex items-center gap-1"
                  >
                    <Download size={12} /> EXPORT
                  </button>
                )}
              </div>

              {sessions.map(session => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={activeSessionId === session.id}
                  onSelect={handleSelectSession}
                  onDelete={handleDeleteSession}
                />
              ))}

              {sessions.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-text-tertiary text-xs italic font-medium">No history yet</p>
                </div>
              )}
            </div>
            
            {/* Model Info */}
            <div className="mt-auto pt-4 border-t border-border/50 px-2">
               <div className="bg-bg rounded-xl p-3 flex items-center justify-between">
                  <span className="text-[10px] font-bold text-text-secondary uppercase tracking-tighter">Current Model</span>
                  <span className="text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-border text-primary font-bold">
                    {modelConfig.chat_model.split(':').pop()}
                  </span>
               </div>
            </div>
          </Card>
        </div>

        {/* 右侧 - 聊天对话区 */}
        <div className="flex-1 flex flex-col h-full min-w-0">
          <Card className="flex-1 flex flex-col h-full min-h-0 border-none shadow-strong bg-white overflow-hidden rounded-[32px] p-0">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-2 custom-scrollbar bg-bg/20">
              {messages.length === 0 && !isLoading ? (
                <div className="flex flex-col items-center justify-center h-full text-center max-w-sm mx-auto">
                  <div className="w-24 h-24 bg-primary/5 rounded-[40px] flex items-center justify-center mb-8 animate-bounce duration-[3000ms]">
                    <span className="text-5xl">✨</span>
                  </div>
                  <h3 className="font-heading text-2xl font-bold text-text-primary mb-4">
                    Ready to start?
                  </h3>
                  <p className="text-text-secondary leading-relaxed font-medium">
                    我在这里为您解答、创作、排忧解难。
                    <br />只需输入，即刻开启。
                  </p>
                </div>
              ) : (
                <div className="max-w-6xl mx-auto w-full">
                  {messages.map(message => (
                    <MessageItem
                      key={message.id}
                      message={message}
                      userImage={session?.user?.image}
                    />
                  ))}

                  {/* Search Results Panel - 独立显示，不依赖流式响应状态 */}
                  {isLoading && (isSearching || currentSearchResults.length > 0) && (
                    <div className="mb-6 max-w-6xl mx-auto">
                      <SearchResultsPanel
                        results={currentSearchResults}
                        query={searchQuery}
                        loading={isSearching}
                      />
                    </div>
                  )}

                  {/* Streaming Assistant Response */}
                  {isLoading && (currentThinking || currentResponse) && (
                    <div className="flex gap-3 mb-6">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <span className="text-xl animate-pulse">🤖</span>
                      </div>
                      <div className="max-w-[90%] md:max-w-[85%] bg-white border border-border rounded-2xl rounded-tl-sm p-4 shadow-sm">
                        {currentThinking && (
                          <div className="mb-4 pb-3 border-b border-border">
                            <button
                              onClick={() => setIsStreamingThinkingExpanded(!isStreamingThinkingExpanded)}
                              className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-primary"
                            >
                              <div className={`p-1 rounded-md bg-primary/5 text-primary`}>
                                <ChevronRight
                                  size={12}
                                  className={`transition-transform duration-300 ${isStreamingThinkingExpanded ? 'rotate-90' : ''}`}
                                />
                              </div>
                              <span>💭 Analyzing...</span>
                            </button>
                            {isStreamingThinkingExpanded && (
                              <div className="mt-3 text-sm text-text-primary leading-relaxed bg-bg p-3 rounded-xl italic border-l-2 border-primary/40">
                                {currentThinking}
                              </div>
                            )}
                          </div>
                        )}

                        <div className="text-[15px] leading-relaxed font-medium text-text-primary">
                          <p className="whitespace-pre-wrap break-words">{currentResponse}</p>
                          <span className="inline-block w-1.5 h-4 bg-primary ml-1 animate-pulse rounded-full align-middle" />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Initial Loading Spinner - 仅在非搜索状态且无流式内容时显示 */}
                  {isLoading && !isSearching && currentSearchResults.length === 0 && !currentThinking && !currentResponse && (
                    <div className="flex gap-3 mb-6">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                        <Loader2 className="animate-spin text-primary" size={20} />
                      </div>
                      <div className="bg-bg/50 rounded-2xl p-4 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce" />
                        <div className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce [animation-delay:0.2s]" />
                        <div className="w-1.5 h-1.5 bg-primary/40 rounded-full animate-bounce [animation-delay:0.4s]" />
                      </div>
                    </div>
                  )}
                </div>
              )}
              <div ref={messagesEndRef} className="h-4" />
            </div>

            {/* Input Area */}
            <div className="p-4 md:p-5 bg-white border-t border-border/50">
              <div className="max-w-6xl mx-auto">
                <div className="relative group bg-bg rounded-[20px] border-2 border-transparent focus-within:border-primary/20 focus-within:bg-white focus-within:shadow-lg transition-all duration-300">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage();
                      }
                    }}
                    placeholder="Ask anything..."
                    className="w-full min-h-[50px] max-h-[200px] pl-5 pr-16 py-3 bg-transparent rounded-[20px] font-body text-[15px] text-text-primary placeholder:text-text-tertiary placeholder:font-medium resize-none focus:outline-none custom-scrollbar"
                    rows={1}
                    disabled={isLoading || !readiness.ready}
                  />
                  <div className="absolute right-2 bottom-2">
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Send size={16} />}
                      onClick={handleSendMessage}
                      disabled={!input.trim() || isLoading || !readiness.ready}
                      className="h-[40px] w-[40px] rounded-xl shadow-md shadow-primary/10"
                    >
                      发送
                    </Button>
                  </div>
                </div>
                {!readiness.ready && !readiness.loading && (
                  <div className="mt-3">
                    <CapabilityGate
                      title={readiness.title}
                      description={readiness.description}
                      ctaHref={readiness.ctaHref}
                      ctaLabel={readiness.ctaLabel}
                    />
                  </div>
                )}
                <div className="flex items-center justify-between mt-2 opacity-30">
                  <p className="text-[9px] font-bold tracking-widest text-text-tertiary uppercase">
                    Press <span className="bg-text-tertiary text-white px-1 rounded mx-0.5">Enter</span> to send
                  </p>
                  <button
                    onClick={() => setEnableSearch(!enableSearch)}
                    className={`group relative overflow-hidden rounded-lg px-3 py-1.5 flex items-center gap-2 font-medium text-[11px] tracking-wide transition-all duration-300 ${
                      enableSearch
                        ? 'bg-primary text-white shadow-lg shadow-primary/40 hover:shadow-xl hover:-translate-y-0.5'
                        : 'bg-white/80 border border-border/50 text-text-primary hover:bg-white hover:border-primary/30 hover:shadow-md'
                    }`}
                  >
                    {enableSearch ? (
                      <Globe size={14} className="relative z-10" />
                    ) : (
                      <Globe size={14} className="text-text-primary relative z-10" />
                    )}
                    <span className="relative z-10">
                      {enableSearch ? '搜索开启' : '搜索关闭'}
                    </span>
                    {/* 微妙的背景光效 */}
                    <div className={`absolute inset-0 rounded-lg transition-opacity duration-300 ${
                      enableSearch
                        ? 'bg-gradient-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100'
                        : 'opacity-0'
                    }`} />
                  </button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
