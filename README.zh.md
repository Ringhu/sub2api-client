# sub2api-client

面向 **任意 sub2api 风格 OpenAI 兼容反代**（one-api、new-api、sub2api 等）的极简 Python 客户端参考实现。

配好 `OPENAI_BASE_URL` + `OPENAI_API_KEY` 之后，本库提供一行调用的常用封装：

| 端点                          | 函数                          |
|-------------------------------|-------------------------------|
| `POST /v1/chat/completions`   | `chat(prompt)`                |
| `POST /v1/responses`          | `respond(prompt)`             |
| `POST /v1/images/generations` | `generate_image(prompt)`      |
| `POST /v1/images/edits`       | `edit_image(prompt, image=...)` |
| `GET  /v1/models`（可用性探测） | `python probe_models.py`      |

原生的 `openai` SDK 代码零改动可用，本库只是薄薄一层常用封装，外加一份
在典型 sub2api 反代上实测过的模型白名单（2026-04-23）。

English version: [README.md](README.md)

## 快速开始

```bash
git clone https://github.com/Ringhu/sub2api-client
cd sub2api-client
pip install -e .

cp .env.example .env
# 编辑 .env 填入你反代的 URL 和 API key
```

冒烟测试：

```bash
python examples/chat_completions.py
```

跑出来一句话介绍 Transformers 就说明通了。

## 库用法

```python
from llm_client import chat, respond, generate_image, edit_image

# Chat Completions
print(chat("用一个词打招呼。"))

# Responses API（比如给 o 系列模型指定 reasoning effort）
print(respond("17 × 23 = ?", model="o3-mini", reasoning={"effort": "low"}))

# 文生图 —— 返回一组 PNG bytes
generate_image("白色桌面上的一个红苹果", save_to="apple.png")

# 图像编辑（multipart 上传）
edit_image("把苹果变绿", image="apple.png", save_to="green.png")
```

需要 streaming / tool calling / 其他 SDK 原生功能时，直接拿底层 client：

```python
from llm_client import get_client
client = get_client()
stream = client.chat.completions.create(
    model="gpt-5.5", messages=[{"role": "user", "content": "hi"}], stream=True,
)
```

## 可用模型

最后验证于 **2026-04-23**。你反代的实际白名单可能不同，跑
`python probe_models.py` 自行复测。

### 文本模型（chat / responses）

| 家族          | 模型 ID                                                                                              | 说明                              |
|---------------|-------------------------------------------------------------------------------------------------------|-----------------------------------|
| **GPT-5.5**   | `gpt-5.5`                                                                                             | **默认**，最新，质量最好           |
| GPT-5.4       | `gpt-5.4`, `gpt-5.4-2026-03-05`, `gpt-5.4-mini`, `gpt-5.4-nano`                                       | 完整版支持 1M 上下文               |
| GPT-5.3       | `gpt-5.3-codex`                                                                                       | 代码向                             |
| GPT-5.2       | `gpt-5.2`, `gpt-5.2-pro`（及各 pinned 版本、chat-latest、codex 变体）                                 | `pro` 用于高质量推理               |
| GPT-5.1       | `gpt-5.1`, `gpt-5.1-chat-latest`, `gpt-5.1-codex`, `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`          |                                   |
| GPT-5.0       | `gpt-5`, `gpt-5-chat`, `gpt-5-codex`, `gpt-5-mini`, `gpt-5-nano`, `gpt-5-pro`                         |                                   |
| **o 系列**    | `o1`, `o1-mini`, `o1-preview`, `o1-pro`, `o3`, `o3-mini`, `o3-pro`, `o4-mini`                         | 推理模型，配合 Responses API 的 `reasoning` 参数使用 |
| GPT-4.5 / 4.1 | `gpt-4.5-preview`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`                                          |                                   |
| GPT-4o        | `gpt-4o`（及 pinned）、`gpt-4o-mini`、`gpt-4o-audio-preview`、`gpt-4o-realtime-preview`、`chatgpt-4o-latest` | 音频 / realtime 需 SDK 支持       |
| GPT-4 / 3.5   | `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`（及 pinned）                                                   | 兼容老代码                         |

### 图像模型（仅 generations / edits，**不能**走 chat）

| ID              | 说明              |
|-----------------|-------------------|
| `gpt-image-2`   | **默认**，最新     |
| `gpt-image-1.5` |                   |
| `gpt-image-1`   |                   |

图像模型调用 `/v1/chat/completions` 会返回 HTTP 400（"not supported"）。
必须走 `/v1/images/generations` 或 `/v1/images/edits`，对应 `generate_image()` 和 `edit_image()`。

## 环境变量

| 变量              | 用途                                                     |
|-------------------|----------------------------------------------------------|
| `OPENAI_BASE_URL` | 反代的 OpenAI 兼容根地址，形如 `https://your-proxy/v1`    |
| `OPENAI_API_KEY`  | 反代颁发的 API key                                        |
| `OPENAI_API_BASE` | 部分库（LiteLLM、LlamaIndex）读这个而不是上面那个，保持一致 |

项目根的 `.env` 会被 `python-dotenv` 自动加载，`.env` 默认被 gitignore，
**别提交真 key**。

## 第三方库接入

`openai` SDK 默认读取 `OPENAI_BASE_URL` / `OPENAI_API_KEY`，绝大多数基于 SDK 的库开箱即用：

```python
# LangChain
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-5.5")

# LiteLLM —— 必须给 model 前缀 "openai/"，LiteLLM 才走 SDK
import litellm
resp = litellm.completion(model="openai/gpt-5.5", messages=[...])

# LlamaIndex
from llama_index.llms.openai import OpenAI as LlamaOpenAI
llm = LlamaOpenAI(model="gpt-5.5")
```

## 常见坑

1. **本地 `ALL_PROXY=socks://...` 会让 httpx 崩溃。** 如果 shell 里设了
   SOCKS 代理，`httpx`（OpenAI SDK 底层）会尝试走它，报错。本库已经用
   `httpx.Client(trust_env=False)` 规避掉了这个问题。如果你绕开本库直接
   用 SDK 又撞上 `Could not resolve proxy`，要么 `unset ALL_PROXY`，
   要么照抄同样的 `trust_env=False` 写法。

2. **Responses API 的 `store` 默认值。** SDK 的 `client.responses.create()`
   默认 `store=True`，很多反代不支持服务端存储、会报错。`respond()`
   默认传 `store=False`。

3. **`/v1/models` 列表不是权威。** 反代可能列出它实际上服务不了的模型。
   跑 `probe_models.py` 实测一下再选。

4. **图像模型走 chat 会 400**，属于预期行为，用 `generate_image()` /
   `edit_image()`。

## 探测你的反代

```bash
# 测所有文本模型的 chat + responses（默认）
python probe_models.py --endpoint both

# 只测图像模型
python probe_models.py --endpoint images

# 全测
python probe_models.py --endpoint all
```

## 协议

MIT。详见 [LICENSE](LICENSE)。

本项目与 OpenAI 或任何特定反代实现无直接关联，可用模型和命名完全取决于你接的那个反代。
