// src/services/llm.ts
import type { LlmConfig } from '../types'

// 定义你的 FastAPI 后端地址
const API_BASE_URL = 'http://localhost:8000'; 

class LlmService {
  
  // 仅作占位，防止外部调用报错
  private initClient(config: LlmConfig): void {}

  /**
   * 普通发送 (保留接口)
   */
  async sendMessage(config: LlmConfig, userMessage: string): Promise<string | null> {
    try {
      console.log(`[RAG] 正在请求后端 ${API_BASE_URL}, 模型: ${config.model}`);
      
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_name: config.model,
          user_query: userMessage
        })
      });

      if (!response.ok) throw new Error('Backend Error');
      const data = await response.json();
      return data.reply; // 返回 Python 生成的文本

    } catch (error) {
      console.error('RAG Error:', error);
      return '抱歉，财务分析系统暂时无法连接。';
    }
  }

  /**
   * 核心适配：伪装成流式输出
   * app.ts 依赖这个方法来切分长句和驱动数字人说话
   */
  async sendMessageWithStream(config: LlmConfig, userMessage: string): Promise<AsyncIterable<string>> {
    // 1. 等待 Python 全量生成结果
    const fullText = await this.sendMessage(config, userMessage);
    
    // 2. 创建一个异步生成器，把结果一次性吐出来
    // 这样 app.ts 会把它当成一个巨大的"chunk"，然后内部的 splitSentence 依然能正常工作
    return (async function* () {
      if (fullText) {
        yield fullText; 
      }
    })();
  }
}

export const llmService = new LlmService()