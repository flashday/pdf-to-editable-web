# **智能文档处理实施方案：React \+ Markdown 修正工作台与 GPT-OSS 协同架构**

## **1\. 架构总览**

本方案旨在构建一个高精度的\*\*“人机协同（Human-in-the-Loop）”\*\*文档处理流水线。系统利用 PaddleOCR 3.x 将非结构化 PDF 转换为语义化的 Markdown，通过基于 React 的双栏修正工作台进行人工清洗，最终将高质量数据注入 GPT-OSS 私有化模型进行推理。

### **核心技术决策**

* **中间交互格式**：**Markdown**（兼顾 LLM 语义理解与人类可读性）。  
* **前端框架**：**React**（利用其强大的生态处理 PDF 渲染与复杂状态同步）。  
* **编辑器形态**：**双栏对照（Split-View）**，左侧 PDF 原文与右侧 Markdown 编辑器通过坐标映射实现同步。  
* **推理模型**：**GPT-OSS**（私有化部署，遵循 Harmony 对话格式）。

## ---

**2\. 核心组件与数据流转设计**

### **2.1 数据流转图**

1. **OCR 引擎层**：PaddleOCR (PP-Structure V3) 处理 PDF，同时输出：  
   * content.md: 语义化的 Markdown 文本（用于编辑与 RAG）。  
   * layout.json: 包含 xyxy 坐标、置信度、Block ID 的元数据（用于前端高亮定位）。  
2. **前端交互层 (React)**：加载上述两份数据，提供双向绑定的编辑界面。  
3. **RAG 存储层**：用户保存修正后的 Markdown \-\> LangChain 切片 \-\> 向量数据库（Milvus/Chroma）。  
4. **推理层**：GPT-OSS 模型 \+ Harmony Prompt 模板 \-\> 业务输出。

## ---

**3\. 前端实施方案：React "精准作业台" (Precision Workbench)**

本部分是项目的工程难点，重点在于如何在 React 中实现“左图右文”的像素级对齐与交互。

### **3.1 关键组件选型**

| 模块 | 推荐库/组件 | 选型理由 |
| :---- | :---- | :---- |
| **PDF 渲染器** | **react-pdf-highlighter** 或 **react-pdf** | react-pdf 提供了基础的 Canvas 渲染能力；react-pdf-highlighter 在此基础上封装了成熟的坐标高亮（Highlight）与 Tip 提示功能，非常适合展示 OCR 的 Bounding Box。 |
| **Markdown 编辑器** | **Vditor** (React 封装) 或 **Monaco Editor** | Vditor 对大文档渲染性能极佳，且原生支持所见即所得；若需要更强的代码级控制（如自定义语法高亮显示置信度），Monaco 是更底层的选择。鉴于您需要“编辑修改”，推荐 **Vditor** 以降低业务人员上手门槛。 |
| **布局管理** | **react-resizable-panels** | 提供类似 VS Code 的高性能拖拽分割栏，确保在大屏操作时的流畅度。 |
| **状态管理** | **Zustand** | 比 Redux 更轻量，适合管理当前选中的 BlockID、滚动位置同步等瞬时状态。 |

### **3.2 核心功能实现路径**

#### **A. JSON 坐标与 Markdown 的映射机制 (Block Mapping)**

PaddleOCR 生成的 Markdown 段落与 JSON 中的 Block 是一一对应的。为了实现“点击 PDF 跳转编辑器”或“滚动同步”，我们需要建立索引：

1. **后端预处理**：在生成 Markdown 时，将 JSON 中的 region\_id 作为不可见的 HTML 锚点插入 Markdown。  
   * *原始 Markdown*：\# 章节标题  
   * *注入后*：\<div id="block\_123" data-coords="100,200,500,600"\>\</div\> \# 章节标题  
2. **前端状态同步**：  
   * 创建一个全局 Store：useStore({ activeBlockId: null })。

#### **B. 左侧 PDF 叠加层 (Overlay Layer)**

不要直接修改 PDF 文件。使用 react-pdf 渲染 Canvas 后，在上方覆盖一个绝对定位的 div 层。

* **绘制选框**：遍历 layout.json，为每个 Block 渲染一个半透明的 div。  
* **置信度告警**：根据 JSON 中的 score 字段，如果置信度 \< 0.9，将该 Block 的边框设为红色，提示人工重点校验。  
* **交互**：点击某个框 \-\> 更新 activeBlockId \-\> 触发右侧编辑器滚动。

#### **C. 双向同步滚动 (Sync-Scrolling) 的实现策略**

简单的百分比滚动（如“左边滚 50%，右边也滚 50%”）在文档编辑场景是无效的，因为图片在 PDF 中占很大篇幅，但在 Markdown 中只占一行。

* **推荐方案：基于锚点的最近邻同步** 1。  
  * **PDF \-\> Editor**：监听 PDF 容器的滚动事件，计算当前视口中心最接近的 Block ID，调用编辑器的 scrollToElement('\#block\_id')。  
  * **Editor \-\> PDF**：监听编辑器光标位置或滚动事件，获取当前行对应的 Block ID，从 JSON 中查找该 ID 的 y 轴坐标，控制 PDF 容器滚动到该 y 值。

#### **D. 复杂表格处理 (HTML 补丁)**

Vditor 支持从 Excel/网页直接粘贴表格并自动转换为 Markdown 或 HTML。

* **策略**：对于 PP-Structure 识别出的复杂表格（包含合并单元格），OCR 结果通常直接就是 HTML \<table\> 代码。React 编辑器应配置为\*\*“混合渲染模式”\*\*，即普通文本用 Markdown 渲染，但遇到 \<table\> 标签时直接渲染为 HTML 表格，允许用户直接在单元格内修改数据。

## ---

**4\. 后端与 RAG 向量化策略**

### **4.1 向量化：从 Markdown 到 Vector**

由于用户会对 Markdown 进行编辑，PaddleOCR 原生的 build\_vector 方法（基于原始 OCR 结果）可能不再适用。建议采用标准的 RAG 数据处理流：

1. **文档加载**：读取用户保存后的修正版 Markdown 文件。  
2. **智能切片 (Chunking)**：  
   * 使用 **MarkdownHeaderSplitter**（LangChain 组件）。这是 Markdown 格式的最大优势，可以基于 \#、\#\# 标题层级进行语义完整的切分，避免将一个完整的段落切碎。  
3. **Embedding**：调用 PP-ChatOCRv4 的 Embedding 模型或通用的 BGE/M3E 模型生成向量。  
4. **入库**：存入向量数据库，并附带元数据（Metadata），如 {"page\_num": 5, "source\_file": "contract.pdf"}，以便推理时能反查来源。

### **4.2 推理引擎：GPT-OSS 与 Harmony 格式集成**

在本地私有化部署 GPT-OSS 时，必须严格遵守其训练时的 Prompt 格式，否则模型性能会大幅下降（尤其是在指令遵循方面）2。

#### **A. Harmony 提示词模板构建**

GPT-OSS 不使用标准的 ChatML，而是使用 Harmony 格式。在将 RAG 检索到的上下文（Context）喂给模型时，请使用以下结构构造 Prompt：

\<|start|\>message

\<|role|\>system

You are a specialized document assistant.

Here is the reference context retrieved from the database (formatted in Markdown):

{{ retrieved\_markdown\_chunks }}

Analyze the context to answer the user's question.

\<|end|\>

\<|start|\>message

\<|role|\>user

{{ user\_question }}

\<|end|\>

\<|start|\>model

\<|role|\>model

#### **B. 推理优化**

* **Thinking Effort (思考强度)**：GPT-OSS 支持 low, medium, high 三种推理模式。对于简单的字段提取，设为 low 以降低延迟；对于复杂的跨段落逻辑分析（如“合同条款是否有冲突”），建议设为 high 4。

## ---

**5\. 项目实施路线图**

1. **阶段一：原型验证 (POC)**  
   * 后端：跑通 PaddleOCR 脚本，输出 Markdown 和 JSON。  
   * 前端：搭建 React 框架，引入 react-pdf 和 Vditor，实现静态加载展示，暂不包含同步滚动。  
2. **阶段二：核心交互开发**  
   * 实现坐标映射算法。  
   * 开发 Canvas 叠加层，实现 Bounding Box 的渲染与点击交互。  
   * 调试双向同步滚动，解决由于图片高度导致的视差问题。  
3. **阶段三：数据闭环**  
   * 实现“保存”按钮：将编辑器内容写回 Markdown 文件。  
   * 集成 RAG 流水线：保存即触发向量化更新。  
   * 接入 GPT-OSS 接口进行问答测试。

## **6\. 总结**

选择 **React** 配合 **Markdown** 是一个兼顾开发效率与数据质量的最佳实践。React 生态中丰富的 PDF 处理库（如 react-pdf-highlighter）为您解决“图文对照”这一核心痛点提供了现成的基石。而 Markdown 的语义特性，则确保了经过人工修正的数据能以最高效率被 GPT-OSS 模型理解，从而最大化 RAG 系统的检索与回答准确率。

#### **Works cited**

1. Implementing Synchronous Scrolling in a Dual-Pane Markdown Editor \- DEV Community, accessed January 27, 2026, [https://dev.to/woai3c/implementing-synchronous-scrolling-in-a-dual-pane-markdown-editor-5d75](https://dev.to/woai3c/implementing-synchronous-scrolling-in-a-dual-pane-markdown-editor-5d75)  
2. gpt-oss-120b & gpt-oss-20b Model Card \- OpenAI, accessed January 27, 2026, [https://cdn.openai.com/pdf/419b6906-9da6-406c-a19d-1bb078ac7637/oai\_gpt-oss\_model\_card.pdf](https://cdn.openai.com/pdf/419b6906-9da6-406c-a19d-1bb078ac7637/oai_gpt-oss_model_card.pdf)  
3. openai/gpt-oss-120b \- Hugging Face, accessed January 27, 2026, [https://huggingface.co/openai/gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b)  
4. GPT-OSS: Specs, Setup, and Self-Hosting Guide \- Semaphore CI, accessed January 27, 2026, [https://semaphore.io/blog/gpt-oss](https://semaphore.io/blog/gpt-oss)