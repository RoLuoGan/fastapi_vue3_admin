import request from "@/utils/request";
import { Auth } from "@/utils/auth";

const API_PATH = "/operations/aiagent";

const AIAgentAPI = {
  // ==================== 会话管理 ====================
  
  /**
   * 创建AI Agent会话
   */
  createSession(data: SessionCreateRequest) {
    return request<ApiResponse<SessionCreateResponse>>({
      url: `${API_PATH}/session/create`,
      method: "post",
      data,
    });
  },

  /**
   * 获取用户会话列表
   */
  getUserSessions(params: SessionListQuery) {
    return request<ApiResponse<SessionListResponse>>({
      url: `${API_PATH}/session/list`,
      method: "get",
      params,
    });
  },

  /**
   * 获取会话历史
   */
  getSessionHistory(sessionId: number) {
    return request<ApiResponse<SessionHistoryResponse>>({
      url: `${API_PATH}/session/${sessionId}/history`,
      method: "get",
    });
  },

  /**
   * 结束会话
   */
  endSession(sessionId: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/session/${sessionId}/end`,
      method: "post",
    });
  },

  // ==================== 聊天接口 ====================

  /**
   * 发送消息（非流式）
   */
  sendMessage(data: ChatRequest, config?: { signal?: AbortSignal }) {
    return request<ApiResponse<ChatResponse>>({
      url: `${API_PATH}/chat`,
      method: "post",
      data,
      ...config,
    });
  },

  /**
   * 发送消息（流式）- 使用 fetch + ReadableStream
   * @param data 聊天请求数据
   * @param onChunk 接收每个chunk的回调
   * @param onComplete 完成回调
   * @param onError 错误回调
   * @param signal 用于取消请求
   */
  async sendMessageStream(
    data: ChatRequest,
    callbacks: {
      onChunk?: (chunk: StreamChunk) => void;
      onComplete?: () => void;
      onError?: (error: string) => void;
    },
    signal?: AbortSignal
  ) {
    const token = Auth.getAccessToken();
    const baseURL = import.meta.env.VITE_APP_BASE_API || "/api/v1";
    
    // 调试日志
    console.log("[AIAgentAPI] 流式请求 token:", token ? `Bearer ${token.substring(0, 20)}...` : "无token");
    console.log("[AIAgentAPI] 流式请求 URL:", `${baseURL}${API_PATH}/chat/stream`);
    
    try {
      const response = await fetch(`${baseURL}${API_PATH}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify(data),
        signal,
        credentials: "same-origin",  // 确保携带凭证
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("无法获取响应流");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonStr = line.slice(6).trim();
              if (jsonStr) {
                const chunk = JSON.parse(jsonStr) as StreamChunk;
                if (chunk.type === "error") {
                  callbacks.onError?.(chunk.error || "未知错误");
                } else if (chunk.type === "complete") {
                  callbacks.onComplete?.();
                } else {
                  callbacks.onChunk?.(chunk);
                }
              }
            } catch (e) {
              console.warn("解析SSE数据失败:", line, e);
            }
          }
        }
      }
      
      callbacks.onComplete?.();
    } catch (error: any) {
      if (error.name !== "AbortError") {
        callbacks.onError?.(error.message || "流式请求失败");
      }
    }
  },

  // ==================== 操作确认 ====================

  /**
   * 获取待确认操作列表
   */
  getPendingOperations(params: PendingOperationsQuery) {
    return request<ApiResponse<PendingOperation[]>>({
      url: `${API_PATH}/operations/pending`,
      method: "get",
      params,
    });
  },

  /**
   * 确认操作
   */
  confirmOperation(operationId: number, data: OperationConfirmRequest) {
    return request<ApiResponse<OperationConfirmResponse>>({
      url: `${API_PATH}/operation/${operationId}/confirm`,
      method: "post",
      data,
    });
  },

  // ==================== 人工接管 ====================

  /**
   * 人工接管会话
   */
  takeoverSession(sessionId: number, data: TakeoverRequest) {
    return request<ApiResponse>({
      url: `${API_PATH}/session/${sessionId}/takeover`,
      method: "post",
      data,
    });
  },

  // ==================== 规则管理 ====================

  /**
   * 获取规则列表
   */
  getRules() {
    return request<ApiResponse<AgentRule[]>>({
      url: `${API_PATH}/rules`,
      method: "get",
    });
  },

  /**
   * 创建规则
   */
  createRule(data: RuleCreateRequest) {
    return request<ApiResponse<{ id: number }>>({
      url: `${API_PATH}/rules/create`,
      method: "post",
      data,
    });
  },

  /**
   * 更新规则
   */
  updateRule(ruleId: number, data: RuleUpdateRequest) {
    return request<ApiResponse>({
      url: `${API_PATH}/rules/${ruleId}`,
      method: "put",
      data,
    });
  },

  /**
   * 删除规则
   */
  deleteRule(ruleId: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/rules/${ruleId}`,
      method: "delete",
    });
  },
};

export default AIAgentAPI;

// ==================== 类型定义 ====================

/** 会话创建请求 */
export interface SessionCreateRequest {
  session_name?: string;
  llm_model?: string;
}

/** 会话创建响应 */
export interface SessionCreateResponse {
  session_id: number;
  session_name: string;
  status: string;
  llm_model?: string;
  created_at: string;
}

/** 会话列表查询参数 */
export interface SessionListQuery {
  page?: number;
  page_size?: number;
  status?: string;
}

/** 会话列表响应 */
export interface SessionListResponse {
  sessions: SessionInfo[];
  page: number;
  page_size: number;
}

/** 会话信息 */
export interface SessionInfo {
  id: number;
  session_name: string;
  status: string;
  llm_model?: string;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

/** 会话历史响应 */
export interface SessionHistoryResponse {
  session: {
    id: number;
    session_name: string;
    status: string;
    created_at: string;
    updated_at: string;
  };
  messages: ChatMessage[];
  total_messages: number;
}

/** 聊天消息 */
export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  tool_calls?: McpToolCall[];
}

/** 聊天请求 */
export interface ChatRequest {
  session_id: number;
  message: string;
  context?: Record<string, any>;
}

/** 聊天响应 */
export interface ChatResponse {
  session_id: number;
  message_id: number;
  content: string;
  role: string;
}

/** 待确认操作查询参数 */
export interface PendingOperationsQuery {
  session_id?: number;
  page?: number;
  page_size?: number;
}

/** 待确认操作 */
export interface PendingOperation {
  operation_id: number;
  session_id: number;
  operation_type: string;
  tool_name: string;
  target_resource?: string;
  params: Record<string, any>;
  confirm_reason: string;
  created_at: string;
}

/** 操作确认请求 */
export interface OperationConfirmRequest {
  confirmed: boolean;
  comment?: string;
}

/** 操作确认响应 */
export interface OperationConfirmResponse {
  status: string;
  operation_id: number;
  result?: any;
  message?: string;
}

/** 人工接管请求 */
export interface TakeoverRequest {
  reason?: string;
}

/** 规则信息 */
export interface AgentRule {
  id: number;
  rule_name: string;
  rule_type: string;
  rule_config: Record<string, any>;
  priority: number;
  enabled: boolean;
  description?: string;
  created_at: string;
  updated_at: string;
}

/** 规则创建请求 */
export interface RuleCreateRequest {
  rule_name: string;
  rule_type: string;
  rule_config: Record<string, any>;
  priority?: number;
  enabled?: boolean;
  description?: string;
}

/** 规则更新请求 */
export interface RuleUpdateRequest {
  rule_name?: string;
  rule_type?: string;
  rule_config?: Record<string, any>;
  priority?: number;
  enabled?: boolean;
  description?: string;
}

/** MCP工具调用信息 */
export interface McpToolCall {
  tool: string;
  tool_call_id?: string;
  input: any;
  output: string;
  success: boolean;
}

/** 流式响应块 */
export interface StreamChunk {
  type: "text" | "tool_start" | "tool_end" | "mcp_tool_call" | "complete" | "error" | "user_saved";
  content?: string;
  tool?: string;
  tool_call_id?: string;
  input?: any;
  output?: string;
  error?: string;
  success?: boolean;
  message_id?: number;  // 消息保存后返回的ID
}
